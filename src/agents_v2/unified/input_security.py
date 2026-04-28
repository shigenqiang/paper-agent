"""
输入安全验证模块

功能:
1. 文本长度和编码格式验证
2. 恶意输入检测（Prompt注入）
3. 敏感信息脱敏
4. 输入异常处理和错误提示

设计原则:
- 默认拒绝（deny-by-default）
- 安全检查在LLM调用前执行
- 错误信息不泄露系统细节
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import unicodedata

logger = logging.getLogger(__name__)


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    passed: bool
    risk_level: str  # "low", "medium", "high", "critical"
    violations: List[str] = None
    sanitized_input: str = ""
    warnings: List[str] = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_level": self.risk_level,
            "violations": self.violations,
            "sanitized_input": self.sanitized_input,
            "warnings": self.warnings
        }


class InputValidator:
    """输入验证器"""

    # 安全阈值配置
    MAX_TEXT_LENGTH = 100000  # 10万字符
    MAX_LINES = 5000
    MIN_TEXT_LENGTH = 1
    MAX_URLS = 20
    MAX_EMAIL_ADDRESSES = 10

    # 恶意模式
    PROMPT_INJECTION_PATTERNS = [
        # 角色扮演/越狱提示
        r'(?i)(roleplay|角色扮演|你是一个|you are now|pretend to be|act as)',
        r'(?i)(ignore (all )?previous (instructions|commands)|disregard)',
        r'(?i)(forget (all )?instructions|new instructions)',
        # 系统提示提取
        r'(?i)(system prompt|系统提示|指令|instructions:)',
        # 注入攻击
        r'(?i)(\\\\n|\\n|\\r|\\t).*(?:system|prompt|instruction)',
        r'(?i)(<!--|-->|<script|javascript:)',
        # 编码绕过
        r'(?i)(&#|&#x|%3C|%3E|%20)',
    ]

    # 可疑的编码模式
    ENCODING_EVASION_PATTERNS = [
        r'&#\d+;',  # HTML实体编码
        r'&#x[0-9a-f]+;',  # HTML十六进制编码
        r'%[0-9a-f]{2}',  # URL编码
        r'\\x[0-9a-f]{2}',  # 十六进制转义
        r'\u[0-9a-f]{4}',  # Unicode转义
    ]

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        (r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', 'SSN'),  # 社会安全号
        (r'\b\d{16}\b', 'CREDIT_CARD'),  # 信用卡号
        (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', 'EMAIL'),  # 邮箱
    ]

    def __init__(self):
        self.prompt_patterns = [re.compile(p) for p in self.PROMPT_INJECTION_PATTERNS]
        self.encoding_patterns = [re.compile(p) for p in self.ENCODING_EVASION_PATTERNS]

    def validate(self, text: str) -> SecurityCheckResult:
        """执行完整的安全检查

        Args:
            text: 输入文本

        Returns:
            SecurityCheckResult
        """
        violations = []
        warnings = []
        sanitized = text

        # 1. 基础格式检查
        format_check = self._check_format(text)
        if not format_check["valid"]:
            violations.extend(format_check["errors"])
            return SecurityCheckResult(
                passed=False,
                risk_level="critical",
                violations=violations,
                sanitized_input=""
            )

        # 2. Prompt注入检测
        injection_result = self._detect_prompt_injection(text)
        if injection_result["detected"]:
            violations.append(f"Potential prompt injection: {injection_result['pattern']}")
            sanitized = injection_result["sanitized"]

        # 3. 编码绕过检测
        encoding_result = self._detect_encoding_evasion(text)
        if encoding_result["detected"]:
            warnings.append("Encoded content detected and normalized")
            sanitized = encoding_result["sanitized"]

        # 4. 敏感信息检测（不阻断，仅警告）
        sensitive_result = self._detect_sensitive_info(text)
        if sensitive_result["found"]:
            for info in sensitive_result["found"]:
                warnings.append(f"Sensitive info detected (will be masked): {info['type']}")

        # 5. URL/链接检查
        url_check = self._check_urls(sanitized)
        warnings.extend(url_check["warnings"])

        # 计算风险等级
        risk_level = self._calculate_risk_level(violations, warnings)

        return SecurityCheckResult(
            passed=len(violations) == 0,
            risk_level=risk_level,
            violations=violations,
            sanitized_input=sanitized,
            warnings=warnings
        )

    def _check_format(self, text: str) -> Dict[str, Any]:
        """检查基础格式"""
        errors = []

        # 空检查
        if not text or not text.strip():
            errors.append("Input is empty")
            return {"valid": False, "errors": errors}

        # 长度检查
        if len(text) > self.MAX_TEXT_LENGTH:
            errors.append(f"Input exceeds maximum length ({self.MAX_TEXT_LENGTH})")

        # 行数检查
        line_count = text.count('\n') + 1
        if line_count > self.MAX_LINES:
            errors.append(f"Input exceeds maximum lines ({self.MAX_LINES})")

        # 编码检查
        try:
            # 检查是否是有效的UTF-8
            text.encode('utf-8').decode('utf-8')
        except UnicodeError:
            errors.append("Invalid UTF-8 encoding")

        # 控制字符检查（排除常见的换行、制表）
        for i, char in enumerate(text):
            category = unicodedata.category(char)
            if category.startswith('C') and char not in '\n\r\t':
                errors.append(f"Invalid control character at position {i}")

        return {"valid": len(errors) == 0, "errors": errors}

    def _detect_prompt_injection(self, text: str) -> Dict[str, Any]:
        """检测Prompt注入"""
        for pattern in self.prompt_patterns:
            match = pattern.search(text)
            if match:
                return {
                    "detected": True,
                    "pattern": pattern.pattern,
                    "sanitized": self._remove_injection_pattern(text, pattern)
                }

        return {"detected": False, "sanitized": text}

    def _remove_injection_pattern(self, text: str, pattern) -> str:
        """移除注入模式（保留其余内容）"""
        return pattern.sub('', text)

    def _detect_encoding_evasion(self, text: str) -> Dict[str, Any]:
        """检测编码绕过"""
        detected = False
        sanitized = text

        for pattern in self.encoding_patterns:
            if pattern.search(text):
                detected = True
                # 解码并重新编码为普通文本
                sanitized = self._decode_content(sanitized)

        return {"detected": detected, "sanitized": sanitized}

    def _decode_content(self, text: str) -> str:
        """解码各种编码的内容"""
        decoded = text

        # HTML实体解码
        decoded = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), decoded)
        decoded = re.sub(r'&#x([0-9a-f]+);', lambda m: chr(int(m.group(1), 16)), decoded)

        # URL解码
        import urllib.parse
        try:
            decoded = urllib.parse.unquote(decoded)
        except Exception:
            pass

        return decoded

    def _detect_sensitive_info(self, text: str) -> Dict[str, Any]:
        """检测敏感信息"""
        found = []

        for pattern, info_type in self.SENSITIVE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                found.append({
                    "type": info_type,
                    "value": match.group()[:4] + "****",  # 脱敏显示
                    "position": match.start()
                })

        return {"found": found}

    def _check_urls(self, text: str) -> Dict[str, Any]:
        """检查URL"""
        warnings = []

        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)

        if len(urls) > self.MAX_URLS:
            warnings.append(f"Many URLs detected ({len(urls)}), will be processed carefully")

        return {"warnings": warnings}

    def _calculate_risk_level(
        self,
        violations: List[str],
        warnings: List[str]
    ) -> str:
        """计算风险等级"""
        if violations:
            return "critical"
        elif len(warnings) > 5:
            return "high"
        elif len(warnings) > 2:
            return "medium"
        else:
            return "low"

    def sanitize(self, text: str) -> str:
        """脱敏处理"""
        sanitized = text

        # 移除控制字符
        sanitized = ''.join(
            char if unicodedata.category(char) != 'Cc' or char in '\n\r\t'
            else ' ' for char in sanitized
        )

        # 规范化空白字符
        sanitized = re.sub(r'[ \t]+', ' ', sanitized)  # 多个空格合并
        sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)  # 超过两个换行合并

        return sanitized.strip()

    def validate_file_path(self, file_path: str) -> bool:
        """验证文件路径安全性

        防止路径遍历攻击:
        - 不允许包含 ..
        - 不允许绝对路径（除非在白名单目录内）
        """
        if ".." in file_path:
            return False

        # 检查是否是绝对路径
        if file_path.startswith('/') or file_path.startswith('\\'):
            # 检查是否在允许的目录内
            allowed_prefixes = ['/tmp/', '/home/user/uploads/', 'C:\\temp\\']
            return any(file_path.startswith(prefix) for prefix in allowed_prefixes)

        return True


class InputSecurityMiddleware:
    """输入安全中间件

    作为一个包装器，可以在调用Agent前进行安全检查
    """

    def __init__(self, validator: Optional[InputValidator] = None):
        self.validator = validator or InputValidator()

    async def check(self, user_input: str) -> Tuple[bool, SecurityCheckResult]:
        """检查输入安全性

        Returns:
            (is_safe, check_result)
        """
        result = self.validator.validate(user_input)
        return result.passed, result

    def get_safe_input(self, user_input: str) -> str:
        """获取安全的输入（已脱敏）

        如果输入不安全，返回空的或修改后的输入
        """
        result = self.validator.validate(user_input)
        if result.passed:
            return result.sanitized_input
        else:
            # 严重违规，返回空字符串
            logger.warning(f"Input blocked due to security violations: {result.violations}")
            return ""

    def wrap_agent_call(self, agent_func):
        """包装Agent调用，自动进行安全检查"""
        async def wrapped_func(user_input: str, *args, **kwargs):
            is_safe, check_result = await self.check(user_input)

            if not is_safe:
                raise SecurityError(
                    f"Input failed security check: {check_result.violations}",
                    risk_level=check_result.risk_level
                )

            # 使用脱敏后的输入
            safe_input = check_result.sanitized_input
            return await agent_func(safe_input, *args, **kwargs)

        return wrapped_func


class SecurityError(Exception):
    """安全检查失败异常"""

    def __init__(self, message: str, risk_level: str = "high"):
        super().__init__(message)
        self.risk_level = risk_level


# 便捷函数
def validate_input(text: str) -> SecurityCheckResult:
    """验证输入安全性"""
    validator = InputValidator()
    return validator.validate(text)


def sanitize_input(text: str) -> str:
    """脱敏输入"""
    validator = InputValidator()
    return validator.sanitize(text)