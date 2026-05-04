"""
引用格式定义 - Citation Style Definitions

定义支持的引用格式及其规则
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List


class CitationStyle(Enum):
    """引用样式枚举"""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    GB7714 = "gb7714"
    NATURE = "nature"


# 支持的样式列表
SUPPORTED_STYLES = [
    "apa",
    "mla",
    "chicago",
    "ieee",
    "gb7714",
    "nature"
]


@dataclass
class StyleRules:
    """引用格式规则"""
    name: str
    display_name: str
    author_format: str          # 作者名格式
    title_format: str           # 标题格式
    year_position: str         # 年份位置
    journal_format: str         # 期刊格式
    punctuation: str           # 标点规则
    example: str


# 各格式的详细规则
STYLE_RULES: Dict[str, StyleRules] = {
    "apa": StyleRules(
        name="apa",
        display_name="APA 7th Edition",
        author_format="Last, F. M.",
        title_format="Sentence case, italicized",
        year_position="(Year) after author",
        journal_format="Italicized, volume in parentheses",
        punctuation="Period (.) between sections",
        example="Smith, J. A. (2020). Article title. Journal Name, 12(3), 45-67."
    ),
    "mla": StyleRules(
        name="mla",
        display_name="MLA 9th Edition",
        author_format="Last, First",
        title_format="Title Case in Quotes",
        year_position="(Year) after journal",
        journal_format="Italicized, no volume",
        punctuation="Period (.) at end",
        example="Smith, John. \"Article Title.\" Journal Name, vol. 12, 2020, pp. 45-67."
    ),
    "chicago": StyleRules(
        name="chicago",
        display_name="Chicago Manual of Style 17th",
        author_format="Last, First",
        title_format="Title Case in Quotes",
        year_position="(Year) in parentheses after journal",
        journal_format="Italicized",
        punctuation="Period (.) at end",
        example="Smith, John. \"Article Title.\" Journal Name 12 (2020): 45-67."
    ),
    "ieee": StyleRules(
        name="ieee",
        display_name="IEEE",
        author_format="F. M. Last",
        title_format="Sentence case in quotes",
        year_position="(Year) after journal",
        journal_format="Italicized",
        punctuation="Comma (,) between sections",
        example="J. A. Smith, \"Article title,\" Journal Name, vol. 12, no. 3, pp. 45-67, 2020."
    ),
    "gb7714": StyleRules(
        name="gb7714",
        display_name="GB/T 7714-2015 (Chinese Standard)",
        author_format="Last, F.M.",
        title_format="Sentence case, not italicized",
        year_position=". Year after journal",
        journal_format="Not italicized",
        punctuation="Period (.) between sections",
        example="Smith J A. Article title[J]. Journal Name, 2020, 12(3): 45-67."
    ),
    "nature": StyleRules(
        name="nature",
        display_name="Nature Style",
        author_format="Last, F.",
        title_format="Sentence case, not italicized",
        year_position=", Year after journal",
        journal_format="Italicized",
        punctuation="Comma (,) between sections",
        example="Smith, J. Article title, Nature, 2020, 12, 45-67."
    )
}


def get_style_rules(style: str) -> StyleRules:
    """获取指定格式的规则"""
    return STYLE_RULES.get(style.lower(), STYLE_RULES["apa"])


def get_all_styles() -> List[str]:
    """获取所有支持的样式"""
    return SUPPORTED_STYLES


def is_valid_style(style: str) -> bool:
    """检查是否是有效的样式"""
    return style.lower() in SUPPORTED_STYLES


def get_style_display_name(style: str) -> str:
    """获取样式的显示名称"""
    rules = get_style_rules(style)
    return rules.display_name