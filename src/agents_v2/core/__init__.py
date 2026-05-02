"""Core 模块 - 已重构，向后兼容

目录结构重组后，核心模块分布如下：
- core/: 核心基础类（base_agent, exceptions, streaming, user_manager, config_manager, llm_fallback）
- config/: 配置管理（从 core/config.py 迁移）
- plugins/: 插件系统（从 core/plugins.py 迁移）
- security/: 安全模块（从 core/security.py 迁移，含 rbac.py）
- validation/: 验证器（从 core/validators.py 迁移）
"""

import warnings

# 检测是否使用了旧路径
def _warn_deprecation():
    warnings.warn(
        "从 src.agents_v2.core.* 导入的方式已弃用，请使用新的模块路径："
        "\n  - config/  (配置管理)"
        "\n  - plugins/ (插件系统)"
        "\n  - security/ (安全模块)"
        "\n  - validation/ (验证器)",
        DeprecationWarning,
        stacklevel=3
    )

# 从基础模块导入（保留在 core/）
from .base_agent import (
    BaseAgent,
    AgentInput,
    AgentOutput,
    AgentCapability,
    LLMConfig,
    Tool,
    VirtualTool,
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
from .llm_fallback import (
    LLMCallWithFallback,
    create_llm_caller,
)

# 从新模块导入（config/, plugins/, security/, validation/）
try:
    from ..config import (
        ConfigLoader,
        ConfigValidator,
        AppConfig,
        AgentConfig,
        LLMConfig as ConfigLLMConfig,
        CacheConfig,
        RateLimitConfig,
        SecurityConfig as ConfigSecurityConfig,
        get_model_by_id,
        get_models_by_category,
        get_all_models,
        get_default_model,
        SUPPORTED_MODELS,
        MODEL_CATEGORIES,
    )
except ImportError as e:
    warnings.warn(f"config 模块导入失败: {e}", ImportWarning)

try:
    from ..plugins import (
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
except ImportError as e:
    warnings.warn(f"plugins 模块导入失败: {e}", ImportWarning)

try:
    from ..security import (
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
    from ..security.rbac import (
        Permission,
        RBACManager,
        get_rbac_manager,
    )
except ImportError as e:
    warnings.warn(f"security 模块导入失败: {e}", ImportWarning)

try:
    from ..validation import (
        ValidationType,
        ValidationRule,
        ValidationResult,
        InputValidator,
        OutputFormatter,
        validate_input,
    )
except ImportError as e:
    warnings.warn(f"validation 模块导入失败: {e}", ImportWarning)

__all__ = [
    # base_agent (保留在 core/)
    "BaseAgent", "AgentInput", "AgentOutput", "AgentCapability",
    "LLMConfig", "Tool", "VirtualTool",
    # exceptions (保留在 core/)
    "AgentError", "LLMError", "ValidationError", "ConfigurationError",
    "TimeoutError", "ExternalAPIError", "CacheError", "CircuitBreakerOpenError",
    "AgentNotFoundError", "InvalidStateError",
    # streaming (保留在 core/)
    "StreamEventType", "StreamEvent", "StreamResponse", "StreamingHandler",
    "PhaseStreamer", "stream_to_async_iterator", "create_streaming_handler",
    # user_manager (保留在 core/)
    "UserSession", "User", "UserManager", "get_user_manager",
    # config_manager (保留在 core/)
    "ConfigChange", "ConfigManager", "get_config_manager",
    # llm_fallback (保留在 core/)
    "LLMCallWithFallback", "create_llm_caller",
    # config (新模块)
    "ConfigLoader", "ConfigValidator", "AppConfig", "AgentConfig",
    "ConfigLLMConfig", "CacheConfig", "RateLimitConfig", "ConfigSecurityConfig",
    "get_model_by_id", "get_models_by_category", "get_all_models", "get_default_model",
    "SUPPORTED_MODELS", "MODEL_CATEGORIES",
    # plugins (新模块)
    "PluginType", "PluginState", "PluginMetadata", "PluginInfo", "PluginInterface",
    "AgentPlugin", "ToolPlugin", "PluginSandbox", "PluginManager",
    "PluginError", "DependencyError", "get_plugin_manager", "agent_plugin", "tool_plugin",
    # security (新模块)
    "AuditEventType", "AuditSeverity", "AuditEvent", "SecurityAudit",
    "PermissionChecker", "InputSanitizer", "SecretManager", "CoreSecurityConfig",
    "get_secrets", "sanitize_input",
    # rbac (在 security/ 下)
    "Permission", "RBACManager", "get_rbac_manager",
    # validation (新模块)
    "ValidationType", "ValidationRule", "ValidationResult", "InputValidator",
    "OutputFormatter", "validate_input",
]