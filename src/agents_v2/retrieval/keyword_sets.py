"""
Keyword Sets - Query classification keyword collections

Used by QueryTypeClassifier for rule-based query classification.
Organized by priority (higher priority types checked first).
"""

# Priority 1: Complex Reasoning Keywords
REASONING_KEYWORDS = {
    # Chinese
    "为什么", "原因", "分析", "推理", "证明", "分析原因", "为什么是",
    "怎么证明", "推导", "推论", "论证",
    # English
    "why", "reason", "analyze", "prove", "analysis", "reasoning",
    "explain why", "how to prove", "deduce", "derive", "argument"
}

# Priority 2: Comparison Keywords
COMPARISON_KEYWORDS = {
    # Chinese
    "对比", "比较", "差异", "区别", "哪个好", "哪个更好", "有什么不同",
    "有什么优势", "孰优孰劣", "差别", "差异点", "不同点", "哪个更", "更好",
    "哪一个",
    # English
    "compare", "difference", "vs", "versus", "different from",
    "compare to", "contrast", "advantage", "disadvantage", "pros cons"
}

# Priority 3: Definition Keywords
DEFINITION_KEYWORDS = {
    # Chinese
    "什么是", "定义", "含义", "解释", "什么叫", "是指", "概念", "定义是",
    "解释是",
    # English
    "definition", "what is", "means", "defined as", "refers to", "define",
    "meaning of"
}

# Priority 4: Fact Lookup Keywords
FACT_KEYWORDS = {
    # Chinese
    "谁", "哪一年", "多少", "何时", "哪里", "哪个", "多少个", "什么时候",
    "谁发明的", "谁提出", "何时发表",
    # English
    "who", "when", "where", "how many", "how much", "which year",
    "invented by", "proposed by", "published", "created by"
}

# Priority 5: Exploration Keywords
EXPLORATION_KEYWORDS = {
    # Chinese
    "探索", "了解", "研究", "最新", "趋势", "发展", "前沿", "方向", "领域",
    "进展", "发现",
    # English
    "explore", "recent", "latest", "trend", "development", "frontier",
    "research", "discover", "new", "emerging"
}

# All keywords in priority order for classification
KEYWORD_GROUPS = [
    (REASONING_KEYWORDS, "reasoning"),
    (COMPARISON_KEYWORDS, "comparison"),
    (DEFINITION_KEYWORDS, "definition"),
    (FACT_KEYWORDS, "fact"),
    (EXPLORATION_KEYWORDS, "exploration"),
]


def get_all_keywords() -> set:
    """Get all keywords as a single set"""
    all_kw = set()
    for keywords, _ in KEYWORD_GROUPS:
        all_kw.update(keywords)
    return all_kw


def validate_keyword_sets() -> bool:
    """Validate that all keyword sets are lowercase and non-empty"""
    for keywords, name in KEYWORD_GROUPS:
        if not keywords:
            raise ValueError(f"Keyword set '{name}' is empty")
        for kw in keywords:
            if kw.isalpha() and kw != kw.lower():
                raise ValueError(f"Keyword '{kw}' in '{name}' is not lowercase")
    return True
