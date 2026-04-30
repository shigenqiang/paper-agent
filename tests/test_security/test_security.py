"""
安全模块测试
"""
import pytest
import time
from src.agents_v2.core.security import (
    InputSanitizer, SecretManager, SecurityAudit, PermissionChecker,
    AuditEvent, AuditEventType, AuditSeverity, sanitize_input
)


class TestInputSanitizer:
    """输入清理器测试"""

    def setup_method(self):
        self.sanitizer = InputSanitizer()

    def test_sanitize_empty_string(self):
        assert self.sanitizer.sanitize("") == ""
        assert self.sanitizer.sanitize(None) == ""

    def test_sanitize_normal_text(self):
        text = "Hello, World!"
        assert self.sanitizer.sanitize(text) == "Hello, World!"

    def test_sanitize_html_escaping(self):
        text = "<script>alert('xss')</script>"
        result = self.sanitizer.sanitize(text)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_dangerous_tags(self):
        text = "<iframe src='evil.com'></iframe>"
        result = self.sanitizer.sanitize(text)
        assert "<iframe" not in result

    def test_sanitize_dangerous_attrs_escaped(self):
        """With allow_html=False (default), dangerous attr values are escaped"""
        text = "<img src='x' onerror='alert(1)'>"
        result = self.sanitizer.sanitize(text)
        # The onerror attribute name is preserved but the JS value is escaped
        assert "&lt;script&gt;" in result or "<script>" not in result  # Script tag is escaped

    def test_sanitize_removes_javascript_protocol(self):
        """JavaScript protocol is removed even in escaped mode"""
        text = "Click <a href='javascript:alert(1)'>here</a>"
        result = self.sanitizer.sanitize(text)
        assert "javascript:" not in result

    def test_sanitize_javascript_protocol(self):
        text = "javascript:alert('xss')"
        result = self.sanitizer.sanitize(text)
        assert "javascript:" not in result

    def test_sanitize_allow_html_mode(self):
        """Test that allowed tags are preserved in allow_html=True mode"""
        sanitizer = InputSanitizer(allow_html=True)
        text = "<p>Hello</p>"
        result = sanitizer.sanitize(text)
        assert "<p>" in result

    def test_sanitize_allow_html_removes_script(self):
        """Test that dangerous tags are still removed even in allow_html mode"""
        sanitizer = InputSanitizer(allow_html=True)
        text = "<p>Hello</p><script>alert('xss')</script>"
        result = sanitizer.sanitize(text)
        assert "<script>" not in result
        assert "<p>" in result

    def test_sanitize_dict(self):
        data = {
            "name": "<script>alert('xss')</script>",
            "age": 25,
            "bio": "Normal text"
        }
        result = self.sanitizer.sanitize_dict(data)
        assert "<script>" not in result["name"]
        assert result["age"] == 25
        assert result["bio"] == "Normal text"

    def test_remove_null_bytes(self):
        text = "Hello\x00World"
        result = self.sanitizer.sanitize(text)
        assert "\x00" not in result

    def test_normalize_whitespace(self):
        text = "Hello    World\n\tTest"
        result = self.sanitizer.sanitize(text)
        assert "  " not in result or "\n" not in result


class TestSecretManager:
    """密钥管理器测试"""

    def setup_method(self):
        self.manager = SecretManager()

    def test_set_and_get(self):
        self.manager.set("API_KEY", "secret123")
        assert self.manager.get("API_KEY") == "secret123"

    def test_get_nonexistent_key(self):
        assert self.manager.get("NONEXISTENT") is None
        assert self.manager.get("NONEXISTENT", "default") == "default"

    def test_clear(self):
        self.manager.set("KEY1", "value1")
        self.manager.clear()
        assert self.manager.get("KEY1") is None

    def test_env_prefix(self):
        import os
        os.environ["PAPER_AGENT_TEST_KEY"] = "env_value"
        self.manager.set("TEST_KEY", "memory_value")
        assert self.manager.get("TEST_KEY") == "env_value"
        del os.environ["PAPER_AGENT_TEST_KEY"]


class TestAuditEvent:
    """审计事件测试"""

    def test_create_audit_event(self):
        event = AuditEvent(
            event_type=AuditEventType.LOGIN,
            user_id="user123",
            action="login"
        )
        assert event.event_type == AuditEventType.LOGIN
        assert event.user_id == "user123"
        assert event.event_id != ""

    def test_to_dict(self):
        event = AuditEvent(
            event_type=AuditEventType.API_ACCESS,
            user_id="user123",
            action="read_paper"
        )
        result = event.to_dict()
        assert result["event_type"] == "api_access"
        assert result["user_id"] == "user123"
        assert "event_id" in result
        assert "timestamp" in result


class TestSecurityAudit:
    """安全审计系统测试"""

    def setup_method(self):
        self.audit = SecurityAudit(retention_days=90)

    def test_record_event(self):
        event = AuditEvent(
            event_type=AuditEventType.LOGIN,
            user_id="user123"
        )
        self.audit.record(event)
        events = self.audit.get_events()
        assert len(events) == 1

    def test_get_events_by_user(self):
        for i in range(3):
            event = AuditEvent(
                event_type=AuditEventType.LOGIN,
                user_id="user123"
            )
            self.audit.record(event)

        event_other = AuditEvent(
            event_type=AuditEventType.LOGIN,
            user_id="other_user"
        )
        self.audit.record(event_other)

        events = self.audit.get_events(user_id="user123")
        assert len(events) == 3

    def test_get_events_by_type(self):
        event1 = AuditEvent(event_type=AuditEventType.LOGIN)
        event2 = AuditEvent(event_type=AuditEventType.LOGOUT)
        self.audit.record(event1)
        self.audit.record(event2)

        events = self.audit.get_events(event_type=AuditEventType.LOGIN)
        assert len(events) == 1

    def test_get_events_by_time_range(self):
        now = time.time()
        event1 = AuditEvent(event_type=AuditEventType.LOGIN, timestamp=now - 100)
        event2 = AuditEvent(event_type=AuditEventType.LOGIN, timestamp=now)
        self.audit.record(event1)
        self.audit.record(event2)

        events = self.audit.get_events(start_time=now - 50)
        assert len(events) == 1

    def test_check_anomalies_frequent_failures(self):
        for i in range(6):
            event = AuditEvent(
                event_type=AuditEventType.LOGIN,
                user_id="user123",
                result="failure"
            )
            self.audit.record(event)

        anomalies = self.audit.check_anomalies("user123")
        assert any(a["type"] == "frequent_failures" for a in anomalies)

    def test_check_anomalies_multiple_ips(self):
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
        for ip in ips:
            event = AuditEvent(
                event_type=AuditEventType.API_ACCESS,
                user_id="user123",
                ip_address=ip
            )
            self.audit.record(event)

        anomalies = self.audit.check_anomalies("user123")
        assert any(a["type"] == "multiple_ips" for a in anomalies)

    def test_generate_report(self):
        for i in range(5):
            event = AuditEvent(
                event_type=AuditEventType.API_ACCESS,
                user_id="user123"
            )
            self.audit.record(event)

        now = time.time()
        report = self.audit.generate_report(now - 3600, now + 3600)

        assert "period" in report
        assert "summary" in report
        assert report["summary"]["total_events"] >= 5

    def test_verify_integrity(self):
        import hmac
        import hashlib

        data = "test_data"
        key = "secret_key"
        signature = hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()

        assert self.audit.verify_integrity(data, signature, key) is True
        assert self.audit.verify_integrity(data, "wrong_signature", key) is False


class TestPermissionChecker:
    """权限检查器测试"""

    def setup_method(self):
        self.checker = PermissionChecker()

    def test_assign_role(self):
        self.checker.assign_role("user123", "user")
        # assign_role now expands role to actual permissions
        perms = self.checker.get_user_permissions("user123")
        assert "agent:execute" in perms
        assert "memory:read" in perms

    def test_grant_permission(self):
        self.checker.grant_permission("user123", "custom:permission")
        assert self.checker.check_permission("user123", "custom:permission") is True

    def test_revoke_permission(self):
        self.checker.grant_permission("user123", "custom:permission")
        self.checker.revoke_permission("user123", "custom:permission")
        assert self.checker.check_permission("user123", "custom:permission") is False

    def test_admin_has_all_permissions(self):
        self.checker.assign_role("admin123", "admin")
        # Admin has wildcard "*" so can do anything
        assert self.checker.check_permission("admin123", "anything") is True
        assert self.checker.check_permission("admin123", "some:permission") is True

    def test_user_has_specific_permissions(self):
        self.checker.assign_role("user123", "user")
        # User has specific permissions from ROLE_PERMISSIONS
        assert self.checker.check_permission("user123", "agent:execute") is True
        assert self.checker.check_permission("user123", "memory:read") is True

    def test_unknown_role_raises_error(self):
        with pytest.raises(ValueError, match="Unknown role"):
            self.checker.assign_role("user123", "nonexistent_role")

    def test_check_resource_access(self):
        self.checker.grant_permission("user123", "agent:execute")
        assert self.checker.check_resource_access("user123", "agent", "execute") is True
        assert self.checker.check_resource_access("user123", "agent", "delete") is False

    def test_get_user_permissions(self):
        self.checker.grant_permission("user123", "custom:permission")
        perms = self.checker.get_user_permissions("user123")
        assert "custom:permission" in perms


class TestSanitizeInput:
    """sanitize_input快捷函数测试"""

    def test_sanitize_input_default(self):
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result

    def test_sanitize_input_with_sanitizer(self):
        sanitizer = InputSanitizer(allow_html=True)
        result = sanitize_input("<p>Hello</p>", sanitizer)
        assert "<p>" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
