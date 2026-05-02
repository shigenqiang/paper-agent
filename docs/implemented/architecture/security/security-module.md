# Security 模块

> 版本：v1.0
> 更新日期：2026-05-03
> 基于：`src/agents_v2/security/`

## 模块概述

security 模块提供安全相关功能：

- **rbac.py**：基于角色的访问控制
- **__init__.py**：安全组件导出

## 目录结构

```
security/
├── __init__.py              # 安全组件 (16KB)
└── rbac.py                  # RBAC 实现 (5KB)
```

## 核心组件

### RBAC (基于角色的访问控制)

```python
class RBAC:
    def __init__(self)
    def add_role(self, role: str, permissions: list[str])
    def add_user_role(self, user_id: str, role: str)
    def check_permission(self, user_id: str, permission: str) -> bool
```

**权限模型**：
- `user:read` - 读取用户信息
- `user:write` - 修改用户信息
- `paper:read` - 读取论文
- `paper:write` - 修改论文
- `admin:*` - 管理员所有权限

### 输入验证

- API 请求校验
- SQL 注入防护
- XSS 防护

## 与其他模块关系

```
server/api_server.py
        │
        ▼
    security/
        │
        ├─► RBAC.check_permission()  # 权限检查
        └─► 输入验证                  # 安全校验
```

---

**版本**：v1.0
**更新日期**：2026-05-03