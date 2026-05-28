"""搜索错误分类"""

from __future__ import annotations

from enum import Enum


class SearchErrorCategory(str, Enum):
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    API_ERROR = "API_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    UNKNOWN = "UNKNOWN"


class SearchError(Exception):
    """搜索异常基类"""

    def __init__(
        self,
        message: str,
        source: str = "",
        category: SearchErrorCategory = SearchErrorCategory.UNKNOWN,
        retryable: bool = True,
    ):
        super().__init__(message)
        self.source = source
        self.category = category
        self.retryable = retryable
