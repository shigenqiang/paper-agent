"""Core foundation modules for the agent framework."""
from .base_agent import (
    BaseAgent,
    AgentInput,
    AgentOutput,
    AgentCapability,
    LLMConfig,
    Tool,
    VirtualTool,
)
from .config import (
    ConfigLoader,
    ConfigValidator,
    AppConfig,
    AgentConfig,
    LLMConfig as ConfigLLMConfig,
    CacheConfig,
    RateLimitConfig,
    SecurityConfig,
    get_model_by_id,
    get_models_by_category,
    get_all_models,
    get_default_model,
)
from .exceptions import (
    AgentError,
    LLMError,
    ValidationError,
    ConfigurationError,
    TimeoutError,
    ExternalAPIError,
    CacheError,
    CircuitBreakerOpenError,
    AgentNotFoundError,
    InvalidStateError,
)
from .streaming import (
    StreamEventType,
    StreamEvent,
    StreamResponse,
    StreamingHandler,
    PhaseStreamer,
    stream_to_async_iterator,
    create_streaming_handler,
)
from .validators import (
    ValidationType,
    ValidationRule,
    ValidationResult,
    InputValidator,
    OutputFormatter,
    validate_input,
)
from .plugins import (
    PluginType,
    PluginState,
    PluginMetadata,
    PluginInfo,
    PluginInterface,
    AgentPlugin,
    ToolPlugin,
    PluginSandbox,
    PluginManager,
    PluginError,
    DependencyError,
    get_plugin_manager,
    agent_plugin,
    tool_plugin,
)
from .security import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    SecurityAudit,
    PermissionChecker,
    InputSanitizer,
    SecretManager,
    SecurityConfig as CoreSecurityConfig,
    get_secrets,
    sanitize_input,
)
from .rbac import (
    Permission,
    RBACManager,
    get_rbac_manager,
)
from .user_manager import (
    UserSession,
    User,
    UserManager,
    get_user_manager,
)
from .config_manager import (
    ConfigChange,
    ConfigManager,
    get_config_manager,
)

__all__ = [
    # base_agent
    "BaseAgent", "AgentInput", "AgentOutput", "AgentCapability",
    "LLMConfig", "Tool", "VirtualTool",
    # config
    "ConfigLoader", "ConfigValidator", "AppConfig", "AgentConfig",
    "ConfigLLMConfig", "CacheConfig", "RateLimitConfig", "SecurityConfig",
    "get_model_by_id", "get_models_by_category", "get_all_models", "get_default_model",
    # exceptions
    "AgentError", "LLMError", "ValidationError", "ConfigurationError",
    "TimeoutError", "ExternalAPIError", "CacheError", "CircuitBreakerOpenError",
    "AgentNotFoundError", "InvalidStateError",
    # streaming
    "StreamEventType", "StreamEvent", "StreamResponse", "StreamingHandler",
    "PhaseStreamer", "stream_to_async_iterator", "create_streaming_handler",
    # validators
    "ValidationType", "ValidationRule", "ValidationResult", "InputValidator",
    "OutputFormatter", "validate_input",
    # plugins
    "PluginType", "PluginState", "PluginMetadata", "PluginInfo", "PluginInterface",
    "AgentPlugin", "ToolPlugin", "PluginSandbox", "PluginManager",
    "PluginError", "DependencyError", "get_plugin_manager", "agent_plugin", "tool_plugin",
    # security
    "AuditEventType", "AuditSeverity", "AuditEvent", "SecurityAudit",
    "PermissionChecker", "InputSanitizer", "SecretManager", "CoreSecurityConfig",
    "get_secrets", "sanitize_input",
    # rbac
    "Permission", "RBACManager", "get_rbac_manager",
    # user_manager
    "UserSession", "User", "UserManager", "get_user_manager",
    # config_manager
    "ConfigChange", "ConfigManager", "get_config_manager",
]
