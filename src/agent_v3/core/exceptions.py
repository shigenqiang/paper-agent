"""Agent v3 exceptions."""


class AgentV3Error(Exception):
    """Base exception for agent_v3."""


class ConfigError(AgentV3Error):
    """Configuration error."""


class LLMError(AgentV3Error):
    """LLM call error."""


class ParseError(AgentV3Error):
    """Paper parsing error."""


class KGError(AgentV3Error):
    """Knowledge graph error."""


class QAError(AgentV3Error):
    """QA error."""


class ReportError(AgentV3Error):
    """Report generation error."""
