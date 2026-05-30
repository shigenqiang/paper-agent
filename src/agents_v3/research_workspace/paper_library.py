"""论文库管理服务"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import (
    Author,
    CitationInfo,
    OpenAccessInfo,
    Paper,
    PaperClassification,
    PaperDates,
    PaperIdentifiers,
    PaperSource,
    PaperStatus,
)
from src.agents_v3.research_workspace.search.base import BaseSearchAdapter, SearchQuery, SearchResult, SearchSession
from src.agents_v3.research_workspace.search.dedup import build_existing_keys, make_dedup_key
from src.agents_v3.research_workspace.search.ranking import RankingService
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage


def search_result_to_meta(r: SearchResult) -> dict[str, Any]:
    """将 SearchResult 转换为 Paper 构造用的元数据 dict"""
    return {
        "title": r.title,
        "authors": [{"name": a} for a in r.authors],
        "dates": {"year": r.year},
        "source": {"venue": r.venue},
        "identifiers": {
            "doi": r.doi,
            "arxiv_id": r.arxiv_id,
            "pubmed_id": r.pubmed_id,
            "openalex_id": r.openalex_id,
            "semantic_scholar_id": r.semantic_scholar_id,
        },
        "abstract": r.abstract,
        "language": r.language,
        "publication_type": r.publication_type,
        "url": r.url,
        "open_access": {"pdf_url": r.pdf_url},
        "classification": {
            "concepts": r.concepts,
            "keywords": r.keywords,
        },
        "citation": {"citation_count": r.citations},
    }


class PaperLibraryService:
    """项目论文库管理"""

    def __init__(
        self,
        storage: JSONStorage | None = None,
        search_adapters: list[BaseSearchAdapter] | None = None,
        global_storage: JSONStorage | None = None,
    ):
        self.storage = storage or get_storage()
        self.search_adapters = search_adapters or []
        self.global_storage = global_storage or get_storage()

    # ── 论文池操作 ──────────────────────────────────────

    def add_to_pool(self, result: SearchResult) -> str:
        """将搜索结果存入全局论文池（无搜索分数），返回 paper_id"""
        # 用 DOI/arXiv ID/OpenAlex ID 生成稳定的 paper_id
        paper_id = self._make_pool_paper_id(result)
        existing = self.global_storage.load_from_folder("papers_pool", paper_id)
        if existing:
            logger.debug(f"Paper already in pool: {paper_id}")
            return paper_id

        pool_data = {
            "paper_id": paper_id,
            "title": result.title,
            "abstract": result.abstract,
            "authors": [{"name": a} for a in result.authors],
            "year": result.year,
            "venue": result.venue,
            "doi": result.doi,
            "arxiv_id": result.arxiv_id,
            "pubmed_id": result.pubmed_id,
            "openalex_id": result.openalex_id,
            "semantic_scholar_id": result.semantic_scholar_id,
            "url": result.url,
            "pdf_url": result.pdf_url,
            "citations": result.citations,
            "concepts": result.concepts,
            "keywords": result.keywords,
            "language": result.language,
            "publication_type": result.publication_type,
            "source": result.source,
            "source_payload": result.source_payload,
            "is_pdf_downloaded": False,
            "is_parsed": False,
            "added_at": __import__("datetime").datetime.now().isoformat(),
        }
        self.global_storage.save_to_folder("papers_pool", paper_id, pool_data)
        logger.info(f"Added to pool: {paper_id} - {result.title[:50]}")
        return paper_id

    def get_from_pool(self, paper_id: str) -> dict[str, Any] | None:
        """从全局论文池读取论文元数据"""
        return self.global_storage.load_from_folder("papers_pool", paper_id)

    def list_pool(self) -> list[dict[str, Any]]:
        """列出论文池中的所有论文"""
        return self.global_storage.list_folder("papers_pool")

    def _make_pool_paper_id(self, result: SearchResult) -> str:
        """生成稳定的 paper_id（基于标识符）"""
        if result.doi:
            return f"doi_{result.doi.replace('/', '_').replace('.', '_')}"
        if result.arxiv_id:
            return f"arxiv_{result.arxiv_id}"
        if result.openalex_id:
            return f"oa_{result.openalex_id}"
        if result.semantic_scholar_id:
            return f"s2_{result.semantic_scholar_id}"
        # fallback: 用标题生成
        import hashlib
        title_hash = hashlib.md5(result.title.lower().strip().encode()).hexdigest()[:12]
        return f"title_{title_hash}"

    def add_uploaded_paper(
        self,
        project_id: str,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Paper:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        dest_dir = self.storage.data_dir / "files" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}.pdf"

        import shutil
        shutil.copy2(file_path, dest_path)

        meta = metadata or {}
        authors_raw = meta.get("authors", [])
        authors = [
            Author(name=a) if isinstance(a, str) else Author(**a)
            for a in authors_raw
        ]

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=meta.get("title", path.stem),
            abstract=meta.get("abstract", ""),
            authors=authors,
            dates=PaperDates(year=meta.get("year")),
            source=PaperSource(venue=meta.get("venue", "")),
            identifiers=PaperIdentifiers(
                doi=meta.get("doi", ""),
                arxiv_id=meta.get("arxiv_id", ""),
            ),
            source_platform="upload",
            status=PaperStatus.UPLOADED,
            pdf_path=str(dest_path),
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())
        logger.info(f"Added paper {paper_id} to project {project_id}")
        return paper

    def add_paper_metadata(
        self,
        project_id: str,
        metadata: dict[str, Any],
        source: str = "import",
        scores: dict[str, float] | None = None,
        topic: str = "",
    ) -> Paper | None:
        # 去重检查
        existing = self.storage.query("papers", {"project_id": project_id})
        existing_keys = build_existing_keys(existing)
        if make_dedup_key(metadata) in existing_keys:
            # 即使论文已存在，仍保存主题相关分数
            if scores and topic:
                dedup_key = make_dedup_key(metadata)
                for p in existing:
                    if make_dedup_key(p) == dedup_key:
                        self.save_topic_score(project_id, p["paper_id"], topic, scores)
                        break
            logger.info(f"Duplicate skipped: {metadata.get('title', '')[:50]}")
            return None

        paper_id = f"paper_{uuid.uuid4().hex[:8]}"

        # 兼容处理：authors 可能是 list[str] 或 list[Author] 或 list[dict]
        authors_raw = metadata.get("authors", [])
        authors = []
        for a in authors_raw:
            if isinstance(a, str):
                authors.append(Author(name=a))
            elif isinstance(a, dict):
                authors.append(Author(**a))
            elif isinstance(a, Author):
                authors.append(a)
            else:
                authors.append(Author(name=str(a)))

        # 兼容处理：identifiers 可能是 dict 或 PaperIdentifiers
        ids_raw = metadata.get("identifiers")
        if isinstance(ids_raw, PaperIdentifiers):
            identifiers = ids_raw
        elif isinstance(ids_raw, dict):
            identifiers = PaperIdentifiers(**ids_raw)
        else:
            identifiers = PaperIdentifiers(
                doi=metadata.get("doi", ""),
                arxiv_id=metadata.get("arxiv_id", ""),
                pubmed_id=metadata.get("pubmed_id", ""),
                openalex_id=metadata.get("openalex_id", ""),
                semantic_scholar_id=metadata.get("semantic_scholar_id", ""),
            )

        # 兼容处理：dates
        dates_raw = metadata.get("dates")
        if isinstance(dates_raw, PaperDates):
            dates = dates_raw
        elif isinstance(dates_raw, dict):
            dates = PaperDates(**dates_raw)
        else:
            dates = PaperDates(year=metadata.get("year"))

        # 兼容处理：source
        source_raw = metadata.get("source_info") or metadata.get("source")
        if isinstance(source_raw, PaperSource):
            paper_source = source_raw
        elif isinstance(source_raw, dict):
            paper_source = PaperSource(**source_raw)
        else:
            paper_source = PaperSource(venue=metadata.get("venue", ""))

        # 兼容处理：open_access
        oa_raw = metadata.get("open_access")
        if isinstance(oa_raw, OpenAccessInfo):
            oa = oa_raw
        elif isinstance(oa_raw, dict):
            oa = OpenAccessInfo(**oa_raw)
        else:
            oa = OpenAccessInfo(pdf_url=metadata.get("pdf_url", ""))

        # 兼容处理：classification
        cls_raw = metadata.get("classification")
        if isinstance(cls_raw, PaperClassification):
            classification = cls_raw
        elif isinstance(cls_raw, dict):
            classification = PaperClassification(**cls_raw)
        else:
            classification = PaperClassification(
                concepts=metadata.get("concepts", []),
                keywords=metadata.get("keywords", []),
            )

        # 兼容处理：citation
        cit_raw = metadata.get("citation")
        if isinstance(cit_raw, CitationInfo):
            citation = cit_raw
        elif isinstance(cit_raw, dict):
            citation = CitationInfo(**cit_raw)
        else:
            citation = CitationInfo(citation_count=metadata.get("citations"))

        # 提取重要性得分
        importance_score = 0.0
        if scores:
            importance_score = scores.get("importance_score", 0.0)

        paper = Paper(
            paper_id=paper_id,
            project_id=project_id,
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract", ""),
            language=metadata.get("language", ""),
            publication_type=metadata.get("publication_type", ""),
            authors=authors,
            identifiers=identifiers,
            dates=dates,
            source=paper_source,
            open_access=oa,
            classification=classification,
            citation=citation,
            url=metadata.get("url", ""),
            source_platform=source if isinstance(source, str) else "",
            status=PaperStatus.IMPORTED,
            importance_score=importance_score,
        )
        self.storage.upsert_item("papers", paper_id, paper.model_dump())

        # 持久化主题相关分数到 topic_scores 集合
        if scores and topic:
            self.save_topic_score(project_id, paper_id, topic, scores)

        logger.info(f"Imported paper {paper_id}: {paper.title}")
        return paper

    def add_search_results(
        self,
        project_id: str,
        results: list[dict[str, Any]],
    ) -> list[Paper]:
        papers = []
        for r in results:
            paper = self.add_paper_metadata(project_id, r, source="search")
            if paper:
                papers.append(paper)
        return papers

    def search_papers(
        self,
        query: SearchQuery,
    ) -> list[SearchResult]:
        """调用已注册的搜索适配器，返回结果（去重，存入论文池）"""
        from src.agents_v3.research_workspace.search.merger import SearchResultMerger
        merger = SearchResultMerger()

        all_results: list[SearchResult] = []
        for adapter in self.search_adapters:
            try:
                results = adapter.search(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search adapter {adapter.source_name} failed: {e}")

        # 去重合并
        merged = merger.merge(all_results)

        # 存入论文池
        for r in merged:
            paper_id = self.add_to_pool(r)
            r.source_payload["pool_paper_id"] = paper_id

        return merged

    # ── 搜索缓存 ──────────────────────────────────────

    @staticmethod
    def _make_cache_key(query: SearchQuery) -> str:
        """根据查询参数生成缓存 key"""
        parts = [
            query.query.strip().lower(),
            ",".join(sorted(query.sources)),
            str(query.year_from or ""),
            str(query.year_to or ""),
            str(query.limit),
        ]
        raw = "|".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> list[SearchResult] | None:
        """查找缓存的搜索结果"""
        item = self.storage.get_item("search_cache", cache_key)
        if item:
            # 兼容两种格式：直接存储或包装在 data 字段中
            cache_data = item.get("data", item)
            results = [SearchResult(**r) for r in cache_data.get("results", [])]
            logger.info(f"Search cache hit: {cache_key} ({len(results)} results)")
            return results
        return None

    def _store_cache(self, cache_key: str, query: SearchQuery, results: list[SearchResult]) -> None:
        """存储搜索结果到缓存"""
        cache_data = {
            "query": query.model_dump(),
            "results": [r.model_dump(exclude_defaults=True) for r in results],
            "cached_at": datetime.now().isoformat(),
            "result_count": len(results),
        }
        self.storage.upsert_item("search_cache", cache_key, {
            "cache_key": cache_key,
            "data": cache_data,
            "expires_at": (datetime.now().timestamp() + 86400),  # 24 小时
        })
        logger.info(f"Cached search results: {cache_key} ({len(results)} results)")

    def search_and_import(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> list[Paper]:
        """搜索并导入到项目（自动去重）"""
        results = self.search_papers(query)

        # 排序以计算分数
        ranking = RankingService(query=query.query)
        results = ranking.rank(results, query=query.query)

        papers = []
        topic = query.query
        for r in results:
            meta = search_result_to_meta(r)
            scores = {
                "importance_score": r.final_score,
                "relevance_score": r.relevance_score,
                "quality_score": r.quality_score,
            }
            paper = self.add_paper_metadata(
                project_id, meta, source=r.source, scores=scores, topic=topic,
            )
            if paper:
                papers.append(paper)
        return papers

    def list_papers(
        self,
        project_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[Paper]:
        query = {"project_id": project_id}
        if filters:
            query.update(filters)
        items = self.storage.query("papers", query)
        return [Paper(**i) for i in items]

    def get_paper(self, paper_id: str) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if item:
            return Paper(**item)
        return None

    def update_paper(self, paper_id: str, **updates: Any) -> Paper | None:
        item = self.storage.get_item("papers", paper_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now().isoformat()
        self.storage.upsert_item("papers", paper_id, item)
        return Paper(**item)

    def mark_included(self, paper_id: str) -> Paper | None:
        return self.update_paper(paper_id, included=True, exclude_reason="")

    def mark_excluded(self, paper_id: str, reason: str) -> Paper | None:
        return self.update_paper(paper_id, included=False, exclude_reason=reason)

    def import_doi_list(
        self,
        project_id: str,
        doi_list: list[str],
    ) -> list[Paper]:
        """通过 DOI 导入论文，使用 Semantic Scholar 查询元数据"""
        import json
        import urllib.request

        papers = []
        for doi in doi_list:
            meta = self._lookup_doi_via_s2(doi)
            meta["identifiers"] = PaperIdentifiers(doi=doi)
            paper = self.add_paper_metadata(project_id, meta, source="doi")
            if paper:
                papers.append(paper)
        return papers

    @staticmethod
    def _lookup_doi_via_s2(doi: str) -> dict[str, Any]:
        """通过 Semantic Scholar API 查询 DOI 元数据"""
        import json
        import time
        import urllib.request

        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,abstract,authors,year,venue,openAccessPdf,externalIds,citationCount"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperAgent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            authors = [a.get("name", "") for a in (data.get("authors") or []) if a.get("name")]
            oa = data.get("openAccessPdf") or {}
            pdf_url = oa.get("url", "") or ""
            ext = data.get("externalIds") or {}
            arxiv_id = ext.get("ArXiv", "") or ""

            # 优先使用 arXiv PDF
            if arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            return {
                "title": data.get("title", f"DOI: {doi}"),
                "abstract": data.get("abstract") or "",
                "authors": [{"name": a} for a in authors],
                "year": data.get("year"),
                "venue": data.get("venue") or "",
                "open_access": {"pdf_url": pdf_url} if pdf_url else {},
            }
        except Exception as e:
            logger.warning(f"S2 DOI lookup failed for {doi}: {e}")
            return {"title": f"DOI: {doi}"}

    def import_bibtex(
        self,
        project_id: str,
        bibtex_text: str,
    ) -> list[Paper]:
        papers = []
        entries = self._parse_bibtex(bibtex_text)
        for entry in entries:
            paper = self.add_paper_metadata(project_id, entry, source="bibtex")
            if paper:
                papers.append(paper)
        return papers

    def _parse_bibtex(self, text: str) -> list[dict[str, Any]]:
        entries = []
        parts = text.split("@")
        for part in parts[1:]:
            match = re.match(r'\w+\{([^,]+),', part)
            if not match:
                continue
            key = match.group(1).strip()
            entry: dict[str, Any] = {"key": key}
            for field_match in re.finditer(r'(\w+)\s*=\s*\{([^}]*)\}', part):
                field_name = field_match.group(1).lower()
                field_value = field_match.group(2).strip()
                if field_name == "author":
                    entry["authors"] = [a.strip() for a in field_value.split(" and ")]
                elif field_name == "year":
                    try:
                        entry["year"] = int(field_value)
                    except ValueError:
                        pass
                elif field_name == "title":
                    entry["title"] = field_value
                elif field_name == "journal":
                    entry["venue"] = field_value
                elif field_name == "doi":
                    entry["doi"] = field_value
            entries.append(entry)
        return entries

    # ── 搜索暂存与提交 ──────────────────────────────

    def search_candidates(
        self,
        project_id: str,
        query: SearchQuery,
    ) -> SearchSession:
        """搜索并暂存结果（不入库），返回 SearchSession。支持缓存。"""
        cache_key = self._make_cache_key(query)

        # 尝试缓存
        if query.use_cache and not query.force_refresh:
            cached = self._check_cache(cache_key)
            if cached is not None:
                session = SearchSession(
                    project_id=project_id,
                    query=query.model_dump(),
                    results=cached,
                    status="pending",
                )
                storage = self.storage
                session_data = session.model_dump()
                session_data["results"] = [r.model_dump(exclude_defaults=True) for r in session.results]
                storage.upsert_item("search_sessions", session.session_id, session_data)
                logger.info(f"Created search session {session.session_id} from cache: {len(cached)} results")
                return session

        # 缓存未命中，调用 API
        results = self.search_papers(query)
        ranking = RankingService(query=query.query)
        results = ranking.rank(results, query=query.query)

        # 存入缓存
        self._store_cache(cache_key, query, results)
        session = SearchSession(
            project_id=project_id,
            query=query.model_dump(),
            results=results,
            status="pending",
        )
        storage = self.storage
        session_data = session.model_dump()
        session_data["results"] = [r.model_dump(exclude_defaults=True) for r in session.results]
        storage.upsert_item("search_sessions", session.session_id, session_data)
        logger.info(f"Created search session {session.session_id}: {len(results)} results")
        return session

    def get_search_session(self, session_id: str) -> SearchSession | None:
        item = self.storage.get_item("search_sessions", session_id)
        if item:
            return SearchSession(**item)
        return None

    def list_search_sessions(self, project_id: str) -> list[SearchSession]:
        items = self.storage.query("search_sessions", {"project_id": project_id})
        return [SearchSession(**i) for i in items]

    def commit_search_results(
        self,
        project_id: str,
        session_id: str,
        result_ids: list[str],
        topic: str = "",
    ) -> list[Paper]:
        """将选中的搜索结果提交入库（从论文池读取元数据）

        Args:
            project_id: 项目 ID
            session_id: 搜索会话 ID
            result_ids: 用户选中的搜索结果 ID 列表
            topic: 当前搜索主题，用于记录论文的重要性得分
        """
        session = self.get_search_session(session_id)
        if not session:
            logger.error(f"Search session not found: {session_id}")
            return []

        # 从 session query 中提取主题（如果未显式传入）
        if not topic:
            topic = session.query.get("query", "")

        results_by_id = {r.result_id: r for r in session.results}
        papers = []
        for rid in result_ids:
            r = results_by_id.get(rid)
            if not r:
                continue

            # 提取分数
            scores = {
                "importance_score": r.final_score,
                "relevance_score": r.relevance_score,
                "quality_score": r.quality_score,
            }

            # 从论文池读取元数据
            pool_paper_id = r.source_payload.get("pool_paper_id")
            if pool_paper_id:
                pool_data = self.get_from_pool(pool_paper_id)
                if pool_data:
                    meta = self._pool_data_to_meta(pool_data)
                    paper = self.add_paper_metadata(
                        project_id, meta, source=r.source, scores=scores, topic=topic,
                    )
                    if paper:
                        papers.append(paper)
                    continue

            # fallback: 直接用搜索结果
            meta = search_result_to_meta(r)
            paper = self.add_paper_metadata(
                project_id, meta, source=r.source, scores=scores, topic=topic,
            )
            if paper:
                papers.append(paper)

        # Update session
        session.selected_result_ids = result_ids
        session.status = "committed"
        self.storage.upsert_item("search_sessions", session_id, session.model_dump())

        logger.info(f"Committed {len(papers)} papers from session {session_id}")
        return papers

    def _pool_data_to_meta(self, pool_data: dict[str, Any]) -> dict[str, Any]:
        """将论文池数据转换为入库元数据格式"""
        return {
            "title": pool_data.get("title", ""),
            "authors": pool_data.get("authors", []),
            "abstract": pool_data.get("abstract", ""),
            "year": pool_data.get("year"),
            "venue": pool_data.get("venue", ""),
            "doi": pool_data.get("doi", ""),
            "arxiv_id": pool_data.get("arxiv_id", ""),
            "pubmed_id": pool_data.get("pubmed_id", ""),
            "openalex_id": pool_data.get("openalex_id", ""),
            "semantic_scholar_id": pool_data.get("semantic_scholar_id", ""),
            "url": pool_data.get("url", ""),
            "pdf_url": pool_data.get("pdf_url", ""),
            "citations": pool_data.get("citations"),
            "concepts": pool_data.get("concepts", []),
            "keywords": pool_data.get("keywords", []),
            "language": pool_data.get("language", ""),
            "publication_type": pool_data.get("publication_type", ""),
        }

    # ── 主题相关重要性得分 ──────────────────────────────────

    def save_topic_score(
        self,
        project_id: str,
        paper_id: str,
        topic: str,
        scores: dict[str, float],
    ) -> None:
        """保存论文在特定主题下的重要性得分

        分数是主题相关的临时数据，只存储在项目 JSON 中，不写入关系数据库。
        """
        from datetime import datetime as _dt

        score_record = {
            "paper_id": paper_id,
            "project_id": project_id,
            "topic": topic,
            "importance_score": scores.get("importance_score", 0.0),
            "relevance_score": scores.get("relevance_score", 0.0),
            "quality_score": scores.get("quality_score", 0.0),
            "scored_at": _dt.now().isoformat(),
        }

        # 读取现有记录，按 paper_id + topic 去重更新
        records = self.storage.load_collection("topic_scores")
        updated = False
        for i, rec in enumerate(records):
            if rec.get("paper_id") == paper_id and rec.get("topic") == topic:
                records[i] = score_record
                updated = True
                break
        if not updated:
            records.append(score_record)

        self.storage.save_collection("topic_scores", records)
        logger.debug(f"Saved topic score: {paper_id} @ {topic[:30]} = {scores.get('importance_score', 0):.3f}")

    def get_topic_scores(
        self,
        project_id: str,
        topic: str,
    ) -> list[dict[str, Any]]:
        """获取某主题下所有论文的重要性得分

        返回按 importance_score 降序排列的得分记录列表。
        """
        records = self.storage.load_collection("topic_scores")
        matched = [
            r for r in records
            if r.get("project_id") == project_id and r.get("topic") == topic
        ]
        matched.sort(key=lambda r: r.get("importance_score", 0), reverse=True)
        return matched

    def get_paper_topic_scores(
        self,
        paper_id: str,
    ) -> list[dict[str, Any]]:
        """获取某篇论文在所有主题下的得分"""
        records = self.storage.load_collection("topic_scores")
        return [r for r in records if r.get("paper_id") == paper_id]

    def recompute_topic_scores(
        self,
        project_id: str,
        topic: str,
    ) -> list[dict[str, Any]]:
        """重新计算某主题下所有论文的重要性得分

        基于论文的标题和摘要与主题的相关性，使用 BM25 重新评分。
        返回更新后的得分记录列表。
        """
        from src.agents_v3.research_workspace.search.ranking import RankingService
        from src.agents_v3.research_workspace.search.base import SearchResult

        papers = self.list_papers(project_id)
        if not papers:
            return []

        # 将 Paper 转换为 SearchResult 用于评分
        results = []
        for p in papers:
            r = SearchResult(
                result_id=p.paper_id,
                source=p.source_platform or "unknown",
                title=p.title,
                authors=[a.name for a in p.authors],
                year=p.dates.year,
                venue=p.source.venue,
                abstract=p.abstract,
                doi=p.identifiers.doi,
                arxiv_id=p.identifiers.arxiv_id,
                pubmed_id=p.identifiers.pubmed_id,
                semantic_scholar_id=p.identifiers.semantic_scholar_id,
                openalex_id=p.identifiers.openalex_id,
                citations=p.citation.citation_count,
                concepts=p.classification.concepts,
                keywords=p.classification.keywords,
            )
            results.append(r)

        # 使用 RankingService 计算分数
        ranking = RankingService(query=topic)
        ranked = ranking.rank(results, query=topic)

        # 持久化分数
        scored_records = []
        for r in ranked:
            scores = {
                "importance_score": r.final_score,
                "relevance_score": r.relevance_score,
                "quality_score": r.quality_score,
            }
            self.save_topic_score(project_id, r.result_id, topic, scores)
            scored_records.append({
                "paper_id": r.result_id,
                "topic": topic,
                "importance_score": r.final_score,
                "relevance_score": r.relevance_score,
                "quality_score": r.quality_score,
            })

        logger.info(f"Recomputed topic scores for {len(scored_records)} papers @ {topic[:30]}")
        return scored_records
