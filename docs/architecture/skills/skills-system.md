# Skills Agent技能系统详解

> 位置: `src/agents_v2/skills/`

## 一、架构概览

```
skills/
├── __init__.py
├── loader.py            # Skill加载器 (11KB)
├── semantic_matcher.py # 语义匹配器 (9KB)
└── definitions/        # Skill定义目录
    ├── _template/     # Skill模板
    ├── topic-agent/    # 选题Skill
    └── query-router/   # 查询路由Skill
```

## 二、Skill定义结构

```
skill_name/
├── SKILL.md           # Skill元数据定义
├── scripts/           # 辅助脚本
│   └── helper.py
├── references/        # 参考文档
│   └── conventions.md
└── assets/           # 静态资源
    └── template.md
```

### 2.1 SKILL.md 结构

```markdown
# Skill Name

## Metadata
- name: skill-name
- version: 1.0.0
- description: 技能描述
- trigger: trigger-keywords

## Core Instructions
核心指令...

## Parameters
- param1: string, 描述
- param2: number, 描述

## Output Format
输出格式描述...
```

## 三、SkillLoader 加载器

```python
class SkillLoader:
    """Skill加载器"""

    def __init__(self, skills_dir: str = "src/agents_v2/skills/definitions"):
        self.skills_dir = Path(skills_dir)
        self._cache: Dict[str, Skill] = {}

    def load_skill(self, skill_name: str) -> Skill:
        """加载指定Skill"""
        if skill_name in self._cache:
            return self._cache[skill_name]

        skill_path = self.skills_dir / skill_name

        if not skill_path.exists():
            raise SkillNotFoundError(skill_name)

        skill = self._parse_skill(skill_path)
        self._cache[skill_name] = skill

        return skill

    def _parse_skill(self, skill_path: Path) -> Skill:
        """解析Skill目录"""
        # 读取SKILL.md
        skill_md = (skill_path / "SKILL.md").read_text()

        # 解析元数据
        metadata = self._parse_metadata(skill_md)

        # 加载辅助脚本
        scripts = self._load_scripts(skill_path / "scripts")

        # 加载参考文档
        references = self._load_references(skill_path / "references")

        return Skill(
            name=skill_name,
            path=skill_path,
            metadata=metadata,
            scripts=scripts,
            references=references
        )

    def list_skills(self) -> List[str]:
        """列出所有可用Skill"""
        return [d.name for d in self.skills_dir.iterdir() if d.is_dir()]
```

## 四、SemanticMatcher 语义匹配

```python
class SemanticMatcher:
    """Skill语义匹配器"""

    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model = embedding_model
        self.encoder = SentenceEncoder(embedding_model)

    def find_matching_skills(
        self,
        query: str,
        skills: List[Skill],
        top_k: int = 3
    ) -> List[MatchedSkill]:
        """
        1. 向量化查询
        2. 计算与各Skill的语义相似度
        3. 返回Top-K匹配结果
        """
        query_vec = self.encoder.encode(query)

        matched = []
        for skill in skills:
            skill_vec = self.encoder.encode(skill.metadata.description)
            similarity = cosine_similarity(query_vec, skill_vec)

            matched.append(MatchedSkill(
                skill=skill,
                score=similarity,
                matched_keywords=self._extract_matched_keywords(query, skill)
            ))

        return sorted(matched, key=lambda x: x.score, reverse=True)[:top_k]
```

## 五、渐进式披露

```python
class ProgressiveDisclosure:
    """渐进式披露 - 根据需要加载Skill层级"""

    # 第一层：Metadata触发层 (~50 token/skill)
    METADATA_TOKENS = 50

    # 第二层：Core Instructions核心指令层 (500-2000 token/skill)
    CORE_INSTRUCTION_TOKENS = 1500

    def get_trigger_context(self, skill: Skill) -> str:
        """获取触发层上下文"""
        return f"{skill.name}: {skill.metadata.description}"

    def get_active_context(self, skill: Skill) -> str:
        """获取活跃层上下文（完整指令）"""
        return self._build_prompt(
            skill.metadata.instructions,
            skill.parameters,
            token_limit=self.CORE_INSTRUCTION_TOKENS
        )

    def get_deep_context(self, skill: Skill) -> str:
        """获取深度层上下文（完整加载）"""
        return self._load_reference_materials(skill.references)
```

## 六、Skill执行

```python
class SkillExecutor:
    """Skill执行器"""

    def __init__(self, skill_loader: SkillLoader):
        self.loader = skill_loader
        self.executors: Dict[str, Callable] = {}

    def register_executor(self, skill_name: str, executor: Callable):
        """注册Skill执行器"""
        self.executors[skill_name] = executor

    async def execute(
        self,
        skill_name: str,
        params: dict,
        context: dict = None
    ) -> SkillResult:
        """执行Skill"""
        skill = self.loader.load_skill(skill_name)

        # 渐进式加载上下文
        active_context = ProgressiveDisclosure().get_active_context(skill)

        # 执行
        executor = self.executors.get(skill_name)
        if executor:
            result = await executor(
                params=params,
                context=active_context,
                **context or {}
            )
        else:
            result = await self._default_execute(skill, params, active_context)

        return SkillResult(
            skill_name=skill_name,
            output=result,
            metadata={"execution_time": time.time()}
        )
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/skills/`
