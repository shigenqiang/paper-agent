# Personalization 个性化系统详解

> 位置: `src/agents_v2/personalization/`

## 一、架构概览

```
personalization/
├── __init__.py
├── preference_learner.py    # 偏好学习 (10KB)
└── user_profile_manager.py # 用户画像 (10KB)
```

## 二、功能描述

### 2.1 PreferenceLearner 偏好学习

**功能**: 学习用户写作偏好，自动调整生成风格

**学习维度**:
| 维度 | 说明 | 行为 |
|------|------|------|
| writing_style | 写作风格 | 简洁/详细/学术 |
| citation_density | 引用密度 | 高引用/低引用 |
| section_order | 章节顺序 | 标准/自定义 |
| language_level | 语言水平 | 简单/进阶/专业 |
| topic_preference | 主题偏好 | 研究领域倾向 |

**学习方式**:
1. **显式反馈**: 用户修改历史
2. **隐式反馈**: 交互行为分析
3. **直接配置**: 用户主动设置

**输出**:
```python
UserPreferences:
    writing_style: str           # "concise" | "detailed" | "academic"
    citation_density: float      # 0.0-1.0
    preferred_sections: List[str]
    language_level: str          # "simple" | "advanced" | "professional"
    topic_interests: List[str]
    excluded_topics: List[str]
```

### 2.2 UserProfileManager 用户画像

**功能**: 管理用户完整画像，支持跨会话记忆

**画像构成**:
```
UserProfile
├── 基础信息
│   ├── user_id
│   ├── name
│   ├── institution
│   └── research_field
│
├── 写作偏好
│   ├── preference_learner 输出
│   └── custom_settings
│
├── 历史交互
│   ├── past_papers: List[PaperSummary]
│   ├── past_topics: List[str]
│   └── feedback_history: List[Feedback]
│
└── 知识图谱
    └── user_entities: List[Entity]  # 用户关注的实体
```

**用途**:
- 个性化论文推荐
- 写作风格适配
- 智能补全建议
- 参考文献推荐

## 三、在工作流中的集成

### 3.1 个性化写作流程

```
用户查询
    │
    ▼
┌─────────────────────────────────────────┐
│  加载用户画像                             │
│  - 偏好设置                              │
│  - 历史交互                              │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  查询增强                                │
│  - 加入用户偏好关键词                      │
│  - 加入历史研究背景                       │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  个性化生成                              │
│  - 应用写作风格                           │
│  - 调整引用密度                           │
│  - 选择合适语言水平                       │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  更新用户画像                             │
│  - 记录本次交互                          │
│  - 更新偏好模型                          │
└─────────────────────────────────────────┘
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/personalization/`