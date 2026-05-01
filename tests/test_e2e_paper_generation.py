"""
端到端论文生成全链路测试

测试完整流程:
1. 创建论文
2. 生成大纲 (OutlineAgent)
3. 逐章生成内容 (DraftWriterAgent)
4. 格式修正/润色 (LanguagePolisherAgent)
5. 组装最终论文

使用mock LLM避免真实API调用，验证管道各环节数据流转正确性。
"""
import pytest
import json
import os
import sys
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, 'D:/pycharmprojects/pythonProject1')

# 直接导入需要的模块，避免通过 __init__.py 的 broken import chain
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig, AgentOutput
from src.agents_v2.paper_agents.outline_agent import OutlineAgent
from src.agents_v2.paper_agents.draft_writer import DraftWriterAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ 测试配置 ============

TEST_TOPIC = "基于深度学习的自然语言处理技术在智能客服系统中的应用研究"


# ============ Mock LLM 响应数据 ============

MOCK_STRUCTURE = json.dumps({
    "structure": {
        "title": "深度学习驱动的智能客服NLP技术研究",
        "paper_type": "empirical",
        "chapters": [
            {"name": "智能客服系统中自然语言理解的技术演进与挑战", "purpose": "梳理技术发展脉络", "order": 1},
            {"name": "基于Transformer的意图识别与槽位填充模型设计", "purpose": "提出核心模型", "order": 2},
            {"name": "多轮对话上下文建模与状态跟踪方法", "purpose": "解决对话连贯性", "order": 3},
            {"name": "实验设计与性能评估", "purpose": "验证模型有效性", "order": 4},
            {"name": "系统部署实践与效果分析", "purpose": "工程落地验证", "order": 5},
        ],
        "total_chapters": 5,
        "word_count_estimate": 12000
    }
}, ensure_ascii=False)

MOCK_CHAPTER_PLANS = json.dumps({
    "chapter_plans": [
        {
            "name": "智能客服系统中自然语言理解的技术演进与挑战",
            "main_points": ["从规则到深度学习的技术演进", "当前NLU在客服场景的核心挑战", "研究目标与贡献"],
            "citations_needed": ["NLU综述", "客服系统架构"],
            "key_arguments": ["深度学习显著优于传统方法"],
            "content_guidance": "从技术演进角度切入，引出研究问题"
        },
        {
            "name": "基于Transformer的意图识别与槽位填充模型设计",
            "main_points": ["BERT预训练模型微调", "联合意图识别框架", "注意力机制优化"],
            "citations_needed": ["BERT", "Joint NLU"],
            "key_arguments": ["联合模型优于独立模型"],
            "content_guidance": "详细描述模型架构和创新点"
        },
        {
            "name": "多轮对话上下文建模与状态跟踪方法",
            "main_points": ["对话状态表示", "上下文编码策略", "状态转移模型"],
            "citations_needed": ["DST", "Dialogue Context"],
            "key_arguments": ["层次化编码有效捕获长距离依赖"],
            "content_guidance": "重点阐述多轮对话的核心技术"
        },
        {
            "name": "实验设计与性能评估",
            "main_points": ["数据集构建", "基线模型对比", "消融实验", "性能指标分析"],
            "citations_needed": ["MultiWOZ", "SNIPS"],
            "key_arguments": ["所提方法在多个指标上超越基线"],
            "content_guidance": "用实验数据支撑论点"
        },
        {
            "name": "系统部署实践与效果分析",
            "main_points": ["系统架构设计", "线上A/B测试", "用户体验指标", "成本效益分析"],
            "citations_needed": ["System Design", "A/B Testing"],
            "key_arguments": ["模型在实际场景中表现优异"],
            "content_guidance": "从工程角度验证研究价值"
        }
    ]
}, ensure_ascii=False)

MOCK_KEY_ARGUMENTS = json.dumps({
    "key_arguments": [
        {
            "id": 1,
            "argument": "基于Transformer的联合意图识别模型显著优于传统独立模型",
            "supporting_evidence": ["BERT在NLU任务上的SOTA表现", "联合学习减少错误传播"],
            "counter_arguments": ["计算成本增加", "小样本场景下可能过拟合"],
            "rebuttal": "通过知识蒸馏和数据增强可有效缓解"
        }
    ]
}, ensure_ascii=False)


def make_chapter_draft(chapter_name, chapter_num):
    """生成模拟的章节草稿内容"""
    return f"""# {chapter_name}

## {chapter_num}.1 研究背景

本章聚焦于"{chapter_name}"的核心问题。随着人工智能技术的快速发展，智能客服系统已经成为企业数字化转型的重要组成部分。自然语言理解（NLU）作为智能客服的核心技术，直接影响着系统的交互质量和用户满意度。

## {chapter_num}.2 技术方案

针对本章研究目标，我们提出以下技术方案：

1. **模型架构设计**：基于Transformer编码器构建特征提取网络
2. **训练策略优化**：采用多任务学习框架联合优化意图识别与槽位填充
3. **推理加速**：通过知识蒸馏实现模型压缩，满足实时性要求

## {chapter_num}.3 核心创新点

本章的主要创新点包括：
- 提出了融合领域知识的注意力机制
- 设计了层次化的特征融合策略
- 引入了对比学习增强语义表示

## {chapter_num}.4 小结

通过上述技术方案的设计与实现，我们为智能客服系统的NLU模块提供了完整的解决方案。实验结果表明，所提方法在多个公开数据集上取得了最优性能。"""


MOCK_POLISH_RESULT = json.dumps({
    "polished_text": "[学术润色版本] 经过语言润色和格式规范化处理后的内容",
    "changes_made": ["提升学术用语规范性", "优化段落结构", "增强逻辑连贯性"],
    "quality_score": 0.85
}, ensure_ascii=False)


# ============ Fixtures ============

@pytest.fixture
def llm_config():
    """测试用LLM配置"""
    return LLMConfig(
        provider="openai",
        model_name="MiniMax-M2.7",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        base_url=os.getenv("OPENAI_BASE_URL", None),
    )


# ============ 大纲生成测试 ============

class TestOutlineGeneration:
    """测试大纲生成环节"""

    @pytest.mark.asyncio
    async def test_outline_agent_returns_valid_structure(self, llm_config):
        """测试 OutlineAgent 能否生成合法的大纲结构"""
        agent = OutlineAgent(llm_config)

        with patch.object(agent, '_llm_call', new_callable=AsyncMock) as mock:
            mock.side_effect = [MOCK_STRUCTURE, MOCK_CHAPTER_PLANS, MOCK_KEY_ARGUMENTS]

            result = await agent.execute({"task_description": TEST_TOPIC})

            assert result.success is True
            outline = result.result["outline"]

            # 验证结构完整性
            assert "structure" in outline
            assert "chapters" in outline
            assert "key_arguments" in outline

            # 验证章节数量
            chapters = outline["chapters"]
            assert len(chapters) >= 3, f"至少3章，实际 {len(chapters)} 章"

            # 验证每个章节有必要的字段
            for ch in chapters:
                assert "name" in ch
                assert "main_points" in ch

            logger.info(f"大纲生成成功: {len(chapters)} 章")

    @pytest.mark.asyncio
    async def test_outline_agent_handles_llm_failure(self, llm_config):
        """测试大纲生成在LLM失败时的降级处理"""
        agent = OutlineAgent(llm_config)

        with patch.object(agent, '_llm_call', new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("LLM connection timeout")

            result = await agent.execute({"task_description": TEST_TOPIC})

            assert result.success is False
            assert result.error is not None
            logger.info(f"错误处理正确: {result.error}")


# ============ 内容生成测试 ============

class TestContentGeneration:
    """测试章节内容生成环节"""

    @pytest.mark.asyncio
    async def test_draft_writer_generates_content(self, llm_config):
        """测试 DraftWriterAgent 能否生成章节内容"""
        agent = DraftWriterAgent(llm_config)

        chapter_name = "智能客服系统中自然语言理解的技术演进与挑战"
        outline = {
            "chapters": [
                {"name": chapter_name, "main_points": ["要点1"], "citations_needed": [], "depends_on": None},
            ]
        }

        with patch.object(agent, '_llm_call', new_callable=AsyncMock) as mock:
            mock.return_value = make_chapter_draft(chapter_name, 1)

            result = await agent.execute(
                input_data={"outline": outline, "section": chapter_name},
                context={"outline": outline, "thesis_statement": TEST_TOPIC, "literature_result": {}}
            )

            assert result.success is True

            content = ""
            if isinstance(result.result, dict):
                content = result.result.get("full_draft", "") or result.result.get("content", "")
            else:
                content = str(result.result)

            assert len(content) > 200, f"内容过短: {len(content)} 字符"
            assert chapter_name in content or "#" in content
            logger.info(f"内容生成成功: {len(content)} 字符")

    @pytest.mark.asyncio
    async def test_draft_writer_generates_multiple_chapters(self, llm_config):
        """测试批量生成多个章节"""
        agent = DraftWriterAgent(llm_config)

        chapters = [
            "智能客服系统中自然语言理解的技术演进与挑战",
            "基于Transformer的意图识别与槽位填充模型设计",
            "多轮对话上下文建模与状态跟踪方法",
        ]

        outline = {
            "chapters": [
                {"name": ch, "main_points": [], "citations_needed": [], "depends_on": None}
                for ch in chapters
            ]
        }

        results = []
        for i, ch in enumerate(chapters):
            with patch.object(agent, '_llm_call', new_callable=AsyncMock) as mock:
                mock.return_value = make_chapter_draft(ch, i + 1)

                result = await agent.execute(
                    input_data={"outline": outline, "section": ch},
                    context={"outline": outline, "thesis_statement": TEST_TOPIC, "literature_result": {}}
                )
                results.append((ch, result))

        # 验证所有章节都生成成功
        success_count = sum(1 for _, r in results if r.success)
        assert success_count == len(chapters), f"成功 {success_count}/{len(chapters)} 章"

        for ch, r in results:
            content = ""
            if isinstance(r.result, dict):
                content = r.result.get("full_draft", "") or r.result.get("content", "")
            else:
                content = str(r.result)
            logger.info(f"  {ch[:25]}... → {len(content)} 字符")


# ============ 内容润色测试 ============

class TestContentPolishing:
    """测试内容润色环节"""

    @pytest.mark.asyncio
    async def test_language_polisher_refines_text(self, llm_config):
        """测试 LanguagePolisherAgent 能否润色内容"""
        try:
            from src.agents_v2.writing.smart_reviser import LanguagePolisherAgent
        except ImportError:
            pytest.skip("LanguagePolisherAgent 不可用")

        agent = LanguagePolisherAgent(llm_config)
        sample_text = "本研究提出了一种新的方法，实验结果表明该方法有效。"

        with patch.object(agent, '_llm_call', new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_POLISH_RESULT

            result = await agent.diagnose({
                "text": sample_text,
                "language": "zh",
                "domain": "computer_science"
            })

            assert result.success is True
            assert result.result is not None
            assert "polished_text" in result.result
            logger.info("内容润色成功")


# ============ API 集成测试 ============

class TestApiIntegration:
    """测试API层面的集成"""

    @pytest.mark.asyncio
    async def test_create_paper_via_api(self):
        """测试通过API创建论文"""
        from src.agents_v2.api.paper_api import create_paper, get_paper, PAPERS_STORAGE

        original = PAPERS_STORAGE.copy()
        PAPERS_STORAGE.clear()

        try:
            request = MagicMock()
            request.content = AsyncMock()
            request.content.read = AsyncMock(return_value=json.dumps({
                "title": TEST_TOPIC,
                "topic": TEST_TOPIC,
            }).encode('utf-8'))
            request.json = AsyncMock(return_value={"title": TEST_TOPIC, "topic": TEST_TOPIC})

            response = await create_paper(request)
            data = json.loads(response.body)

            assert response.status == 201
            assert data["success"] is True
            assert data["data"]["title"] == TEST_TOPIC
            paper_id = data["data"]["id"]

            # 验证可以取回
            get_req = MagicMock()
            get_req.match_info = {"id": paper_id}
            get_resp = await get_paper(get_req)
            assert json.loads(get_resp.body)["data"]["id"] == paper_id

            logger.info(f"API创建论文成功: {paper_id}")

        finally:
            PAPERS_STORAGE.clear()
            PAPERS_STORAGE.update(original)

    @pytest.mark.asyncio
    async def test_api_generate_outline(self):
        """测试通过API生成大纲"""
        from src.agents_v2.api.paper_api import create_paper, generate_outline, PAPERS_STORAGE

        original = PAPERS_STORAGE.copy()
        PAPERS_STORAGE.clear()

        try:
            # 先创建论文
            create_req = MagicMock()
            create_req.content = AsyncMock()
            create_req.content.read = AsyncMock(return_value=json.dumps({
                "title": TEST_TOPIC
            }).encode('utf-8'))
            create_req.json = AsyncMock(return_value={"title": TEST_TOPIC})

            create_resp = await create_paper(create_req)
            paper_id = json.loads(create_resp.body)["data"]["id"]

            # mock OutlineAgent.execute
            with patch('src.agents_v2.paper_agents.outline_agent.OutlineAgent.execute', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = AgentOutput(
                    success=True,
                    result={"outline": {
                        "structure": {"title": "测试", "chapters": [{"name": "第一章", "order": 1}]},
                        "chapters": [{"name": "第一章", "main_points": ["要点1"]}],
                        "key_arguments": []
                    }},
                    agent_name="outline_agent",
                    reasoning="test"
                )

                outline_req = MagicMock()
                outline_req.match_info = {"id": paper_id}
                outline_req.content = AsyncMock()
                outline_req.content.read = AsyncMock(return_value=json.dumps({"topic": TEST_TOPIC}).encode('utf-8'))
                outline_req.json = AsyncMock(return_value={"topic": TEST_TOPIC})

                outline_resp = await generate_outline(outline_req)
                outline_data = json.loads(outline_resp.body)

                assert outline_resp.status == 200
                assert outline_data["success"] is True
                logger.info("API大纲生成成功")

        finally:
            PAPERS_STORAGE.clear()
            PAPERS_STORAGE.update(original)

    @pytest.mark.asyncio
    async def test_api_generate_content(self):
        """测试通过API生成章节内容"""
        from src.agents_v2.api.paper_api import generate_content, PAPERS_STORAGE

        original = PAPERS_STORAGE.copy()
        PAPERS_STORAGE.clear()

        try:
            paper_id = "test-paper-001"
            PAPERS_STORAGE[paper_id] = {
                "id": paper_id,
                "title": TEST_TOPIC,
                "sections": [
                    {"id": "sec1", "title": "技术演进", "content": ""},
                ],
                "status": "draft",
            }

            with patch('src.agents_v2.paper_agents.draft_writer.DraftWriterAgent.execute', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = AgentOutput(
                    success=True,
                    result={"full_draft": make_chapter_draft("技术演进", 1)},
                    agent_name="draft_writer",
                    reasoning="test"
                )

                gen_req = MagicMock()
                gen_req.match_info = {"id": paper_id, "sectionId": "sec1"}
                gen_req.content = AsyncMock()
                gen_req.content.read = AsyncMock(return_value=b'{"prompt":""}')
                gen_req.json = AsyncMock(return_value={"prompt": ""})

                gen_resp = await generate_content(gen_req)
                gen_data = json.loads(gen_resp.body)

                assert gen_resp.status == 200
                assert gen_data["success"] is True
                assert len(gen_data["data"]["content"]) > 100
                logger.info(f"API内容生成成功: {len(gen_data['data']['content'])} 字符")

        finally:
            PAPERS_STORAGE.clear()
            PAPERS_STORAGE.update(original)

    @pytest.mark.asyncio
    async def test_api_format_content(self):
        """测试通过API修正格式"""
        from src.agents_v2.api.paper_api import format_content, PAPERS_STORAGE
        from src.agents_v2.writing import LanguagePolisherAgent

        original = PAPERS_STORAGE.copy()
        PAPERS_STORAGE.clear()

        try:
            paper_id = "test-paper-002"
            PAPERS_STORAGE[paper_id] = {
                "id": paper_id,
                "title": TEST_TOPIC,
                "sections": [{"id": "sec1", "title": "测试", "content": "原始内容"}],
            }

            with patch.object(LanguagePolisherAgent, 'diagnose', new_callable=AsyncMock) as mock_diag:
                mock_diag.return_value = AgentOutput(
                    success=True,
                    result={"polished_text": "[润色后内容]"},
                    agent_name="polisher",
                    reasoning="test"
                )

                fmt_req = MagicMock()
                fmt_req.match_info = {"id": paper_id, "sectionId": "sec1"}
                fmt_req.content = AsyncMock()
                fmt_req.content.read = AsyncMock(return_value=json.dumps({
                    "content": "需要润色的原始内容"
                }).encode('utf-8'))

                fmt_resp = await format_content(fmt_req)
                fmt_data = json.loads(fmt_resp.body)

                assert fmt_resp.status == 200
                assert fmt_data["success"] is True
                logger.info("API格式修正成功")

        finally:
            PAPERS_STORAGE.clear()
            PAPERS_STORAGE.update(original)


# ============ 全链路集成测试 ============

class TestFullPipeline:
    """测试完整的论文生成全链路"""

    @pytest.mark.asyncio
    async def test_full_pipeline_topic_to_final_paper(self, llm_config):
        """
        全链路测试: 主题 → 大纲 → 逐章草稿 → 润色 → 最终论文

        这是最核心的端到端测试，验证整个管道可以产出一篇完整论文。
        """
        logger.info("=" * 70)
        logger.info("开始全链路论文生成测试")
        logger.info(f"论文主题: {TEST_TOPIC}")
        logger.info("=" * 70)

        pipeline = {
            "topic": TEST_TOPIC,
            "outline": None,
            "drafts": [],
            "polished": [],
            "errors": [],
        }

        # ---- Step 1: 生成大纲 ----
        logger.info("\n[Step 1/3] 生成论文大纲...")
        outline_agent = OutlineAgent(llm_config)

        with patch.object(outline_agent, '_llm_call', new_callable=AsyncMock) as mock:
            mock.side_effect = [MOCK_STRUCTURE, MOCK_CHAPTER_PLANS, MOCK_KEY_ARGUMENTS]

            result = await outline_agent.execute({"task_description": TEST_TOPIC})

            assert result.success, f"大纲生成失败: {result.error}"
            pipeline["outline"] = result.result["outline"]

        chapters = pipeline["outline"]["chapters"]
        structure = pipeline["outline"]["structure"]
        logger.info(f"  论文标题: {structure.get('title', '未命名')}")
        logger.info(f"  章节数量: {len(chapters)}")
        for i, ch in enumerate(chapters):
            logger.info(f"    {i+1}. {ch['name'][:40]}")

        # ---- Step 2: 逐章生成草稿 ----
        logger.info(f"\n[Step 2/3] 逐章生成草稿...")
        draft_agent = DraftWriterAgent(llm_config)

        outline_for_draft = {"chapters": [
            {"name": ch["name"], "main_points": ch.get("main_points", []),
             "citations_needed": ch.get("citations_needed", []), "depends_on": None}
            for ch in chapters
        ]}

        for i, ch in enumerate(chapters):
            ch_name = ch["name"]
            logger.info(f"  生成第 {i+1} 章: {ch_name[:35]}...")

            with patch.object(draft_agent, '_llm_call', new_callable=AsyncMock) as mock:
                mock.return_value = make_chapter_draft(ch_name, i + 1)

                draft_result = await draft_agent.execute(
                    input_data={"outline": outline_for_draft, "section": ch_name},
                    context={"outline": outline_for_draft, "thesis_statement": TEST_TOPIC, "literature_result": {}}
                )

                if draft_result.success:
                    content = ""
                    if isinstance(draft_result.result, dict):
                        content = draft_result.result.get("full_draft", "") or draft_result.result.get("content", "")
                    else:
                        content = str(draft_result.result)

                    pipeline["drafts"].append({
                        "chapter": ch_name,
                        "content": content,
                        "length": len(content),
                    })
                    logger.info(f"    ✓ {len(content)} 字符")
                else:
                    pipeline["errors"].append(f"Chapter {i+1} draft failed: {draft_result.error}")
                    logger.error(f"    ✗ 失败: {draft_result.error}")

        # ---- Step 3: 润色各章 ----
        logger.info(f"\n[Step 3/3] 内容润色...")
        try:
            from src.agents_v2.writing.smart_reviser import LanguagePolisherAgent
            polisher = LanguagePolisherAgent(llm_config)
            has_polisher = True
        except ImportError:
            has_polisher = False
            logger.warning("  LanguagePolisherAgent 不可用，跳过润色步骤")

        if has_polisher:
            for draft in pipeline["drafts"]:
                logger.info(f"  润色: {draft['chapter'][:35]}...")

                with patch.object(polisher, '_llm_call', new_callable=AsyncMock) as mock:
                    mock.return_value = json.dumps({
                        "polished_text": f"[已润色] {draft['content'][:200]}...",
                        "changes_made": ["学术用语规范化", "逻辑连贯性优化"],
                        "quality_score": 0.82
                    }, ensure_ascii=False)

                    polish_result = await polisher.diagnose({
                        "text": draft["content"],
                        "language": "zh",
                        "domain": "computer_science"
                    })

                    if polish_result.success and polish_result.result:
                        polished_text = polish_result.result.get("polished_text", draft["content"])
                        pipeline["polished"].append({
                            "chapter": draft["chapter"],
                            "content": polished_text,
                            "length": len(polished_text),
                        })
                        logger.info(f"    ✓ {len(polished_text)} 字符")
                    else:
                        pipeline["polished"].append({
                            "chapter": draft["chapter"],
                            "content": draft["content"],
                            "length": len(draft["content"]),
                        })
        else:
            pipeline["polished"] = [
                {"chapter": d["chapter"], "content": d["content"], "length": d["length"]}
                for d in pipeline["drafts"]
            ]

        # ---- 汇总结果 ----
        logger.info("\n" + "=" * 70)
        logger.info("全链路测试结果汇总")
        logger.info("=" * 70)
        logger.info(f"  论文主题: {pipeline['topic']}")
        logger.info(f"  大纲章节数: {len(chapters)}")
        logger.info(f"  成功生成草稿: {len(pipeline['drafts'])} 章")
        logger.info(f"  成功润色: {len(pipeline['polished'])} 章")
        logger.info(f"  错误数量: {len(pipeline['errors'])}")

        # 组装最终论文
        final_paper = f"# {structure.get('title', TEST_TOPIC)}\n\n"
        final_paper += f"> 论文主题: {TEST_TOPIC}\n"
        final_paper += f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_paper += f"> 章节数量: {len(pipeline['polished'])}\n\n"
        final_paper += "---\n\n"

        for section in pipeline["polished"]:
            final_paper += section["content"] + "\n\n---\n\n"

        total_chars = sum(s["length"] for s in pipeline["polished"])
        logger.info(f"  最终论文字数: {len(final_paper)} 字符")
        logger.info(f"  各章内容总字数: {total_chars} 字符")

        # ---- 断言 ----
        assert pipeline["outline"] is not None, "大纲必须生成"
        assert len(pipeline["drafts"]) >= 3, f"至少生成3章草稿，实际 {len(pipeline['drafts'])}"
        assert len(pipeline["polished"]) >= 3, f"至少润色3章，实际 {len(pipeline['polished'])}"
        assert len(pipeline["errors"]) == 0, f"不应有错误，实际: {pipeline['errors']}"
        assert len(final_paper) > 1000, f"最终论文至少1000字符，实际 {len(final_paper)}"

        # 验证每章内容都足够充实
        for section in pipeline["polished"]:
            assert section["length"] > 100, f"{section['chapter']} 内容过短: {section['length']}字符"

        logger.info("\n✓ 全链路测试通过!")
        return pipeline


# ============ 统计与报告 ============

class TestPipelineReport:
    """生成测试报告"""

    @pytest.mark.asyncio
    async def test_generate_pipeline_report(self, llm_config):
        """运行全链路并生成详细报告"""
        test = TestFullPipeline()
        pipeline = await test.test_full_pipeline_topic_to_final_paper(llm_config)

        report = f"""
{'='*70}
论文生成全链路测试报告
{'='*70}

论文主题: {pipeline['topic']}
大纲章节数: {len(pipeline['outline']['chapters'])}

各章节详情:
"""
        for i, draft in enumerate(pipeline["drafts"]):
            polished = pipeline["polished"][i] if i < len(pipeline["polished"]) else None
            report += f"""
  第{i+1}章: {draft['chapter'][:50]}
    草稿字数: {draft['length']} 字符
    润色字数: {polished['length'] if polished else 'N/A'} 字符
"""

        report += f"""
错误数: {len(pipeline['errors'])}
总字数: {sum(s['length'] for s in pipeline['polished'])} 字符

结论: {'通过 ✓' if len(pipeline['errors']) == 0 else '失败 ✗'}
{'='*70}
"""
        logger.info(report)
        assert len(pipeline["errors"]) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
