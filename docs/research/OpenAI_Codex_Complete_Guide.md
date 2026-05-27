# OpenAI Codex 使用指南（精简版）

## 核心方案对比

| 方案 | 难度 | 成本 | 适用场景 |
|------|------|------|----------|
| **API 中转平台** | 低 | 5-50%折扣 | **国内用户首选** |
| **虚拟信用卡 + 官方API** | 中 | 开卡费+3-5%手续费 | 需要官方账号充值 |
| **Azure OpenAI** | 高（需企业资质） | 较高 | 企业合规 |

---

## 一、网络访问

### 1.1 为什么需要 VPN 或中转
- OpenAI 官方不支持中国内地和港澳地区
- 自2024年7月9日起已封锁非支持地区API流量

### 1.2 节点选择原则
1. **避免亚洲节点**（日本、韩国、新加坡）- 被封锁概率高
2. **推荐美国/欧洲节点**
3. **保持IP稳定**：不要频繁切换

### 1.3 中转平台（国内用户主流选择）
| 平台 | 价格 | 特点 |
|------|------|------|
| **诗云API** | 官方50%起 | SLA 99.92%，国内直连 |
| **Weelinking** | 0.8元/美元 | 20ms低延迟 |
| **硅基流动** | 中等 | 国内直连，模型丰富 |

配置示例：
```toml
model_provider = "custom"
model = "gpt-5.2-codex"
[model_providers.custom]
base_url = "https://api.中转平台.com/v1"
api_key = "sk-your-key"
```

---

## 二、IP 稳定性测试

### 2.1 快速检测方法

**方法一：Ping测试**
```bash
# Windows
ping 服务器IP

# Linux/Mac
ping -c 4 服务器IP
```
- 国内+国外都ping不通 → 服务器问题
- 国内不通，国外通 → **IP被封**

**方法二：Traceroute路由跟踪**
```bash
# Windows
tracert 服务器IP

# Linux/Mac
traceroute 服务器IP
```
- 国内路径正常，国外节点出现 `* * *` → **IP被封**

**方法三：端口检测**
```bash
telnet 服务器IP 端口
```
- 常用检测端口：22(SSH)、443(HTTPS)

### 2.2 在线工具检测
- **国内检测**：tool.chinaz.com/port/（端口开放状态）
- **海外检测**：www.yougetsignal.com/tools/open-ports/
- **综合检测**：IP可用性检测工具（同时测国内+国外）

### 2.3 稳定性四维度检测法

| 指标 | 合格标准 | 测试方法 |
|------|----------|----------|
| 响应一致性 | 波动≤±15ms | `curl`连续访问20次 |
| HTTPS握手 | ≤300ms | 在线工具检测 |
| SOCKS5认证 | 100%成功 | 实际请求测试 |
| HTTP头完整性 | 无X-Forwarded缺失 | 协议检测工具 |

### 2.4 持续监控测试
```python
# Python脚本每30秒检测一次，持续2小时
import requests
import time

success_count = 0
total = 240  # 2小时 = 120次 * 30秒间隔
for i in range(total):
    try:
        r = requests.get("https://api.openai.com", timeout=5)
        if r.status_code == 200:
            success_count += 1
    except:
        pass
    time.sleep(30)

print(f"成功率: {success_count/total*100}%")
```

### 2.5 判断标准
- **IP正常**：国内+国外均可访问
- **IP被封**：国外可用，国内不可用
- **服务器宕机**：国内+国外均不可用（检查防火墙/重启）

---

## 三、支付方式

### 3.1 虚拟信用卡

| 平台 | 开卡费 | 充值手续费 | 特点 |
|------|--------|------------|------|
| **WildCard** | $11.99/年或$16.99/2年 | 3.5% | 支持支付宝、海外手机号 |
| **Fomepay** | ~$10 | 较低 | 无需KYC |
| **Depay** | 较低 | 1-2% | 支持USDT |

**WildCard注册（邀请码JPQBUN6O可减$1）：**
1. 访问 https://bewildcard.com
2. 支付宝扫码认证（无需身份证）
3. 充值建议$25起（绑定预扣$5）

### 3.2 API中转平台（最简单）
1. 注册中转平台 → 2. 支付宝充值 → 3. 获取API Key → 4. 开始使用

---

## 四、注册与API Key

### 4.1 注册前置条件
| 条件 | 说明 |
|------|------|
| 电子邮箱 | Gmail/Outlook（国内邮箱可能被限） |
| 海外手机号 | WildCard/SMS-activate获取 |
| VPN | 访问官网（非必需，可走中转） |

### 4.2 海外手机号获取
| 平台 | 费用 | 特点 |
|------|------|------|
| **WildCard** | 包含在开卡费中 | 一站式服务 |
| **SMS-activate** | $0.5-2/次 | 最大接码平台 |
| **5SIM** | $0.3-1/次 | 多国家支持 |

### 4.3 获取官方API Key
1. 登录 https://platform.openai.com/api-keys
2. 点击 "Create new secret key"
3. **立即复制保存**（只显示一次）

**注意：** 连续两次扣款失败将封号

---

## 五、Codex CLI 安装配置

### 5.1 安装
```bash
npm install -g @openai/codex --registry=https://registry.npmmirror.com
codex --version
```

### 5.2 认证方式

**方式一：ChatGPT账号登录（普通用户）**
```bash
codex login
```

**方式二：API Key登录（自动化场景）**
```bash
export OPENAI_API_KEY="sk-your-api-key"
```

### 5.3 配置文件
- 位置：`~/.codex/config.toml`
- **优先级**：命令行参数 > 当前目录config > 用户目录config

```toml
# 中转平台配置
model_provider = "custom"
model = "gpt-5.2-codex"
[model_providers.custom]
base_url = "https://your-provider.com/v1"
api_key = "sk-your-key"
```

---

## 六、常用命令

| 命令 | 功能 |
|------|------|
| `codex` | 进入交互式会话 |
| `codex "任务"` | 带提示直接执行 |
| `codex start` | 在当前项目启动AI辅助 |
| `codex edit 文件 "修改"` | 编辑文件 |
| `codex diff` | 查看改动差异 |
| `codex accept/reject` | 应用/放弃修改 |
| `codex context add .` | 添加项目上下文 |
| `codex config edit` | 编辑配置文件 |
| `codex mcp add <name> --url <url>` | 添加MCP服务器 |
| `codex resume` | 恢复历史对话 |

---

## 七、MCP配置

MCP允许Codex连接外部系统（Jira、Wiki、数据库等）。

**命令行配置：**
```bash
codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp
codex mcp list
```

**配置文件配置：**
```toml
[mcp_servers.jira]
command = "docker"
args = ["run", "--rm", "-i", "-e", "JIRA_URL=https://...", "mcp/jira"]
```

---

## 八、套餐推荐

| 套餐 | 价格/月 | 额度 | 适合场景 |
|------|---------|------|----------|
| **Plus** | $20 | 5倍基础 | 常规开发 |
| **Pro $100** | $100 | 5倍Plus | 高强度编码 |
| **Pro $200** | $200 | 20倍Plus | 极限用量 |

| 使用频率 | 推荐方案 |
|----------|----------|
| 偶尔（<1小时/天） | API按量付费 或 Plus $20 |
| 经常（1-4小时/天） | Plus $20 或 Pro $100 |
| 高强度（>4小时/天） | Pro $100 或 Pro $200 |

---

## 九、常见问题

| 问题 | 解决方案 |
|------|----------|
| 账号/API被封 | 使用中转平台备援 |
| npm权限错误 | 使用nvm管理Node.js |
| 认证失败 | 更换VPN节点为美国/欧洲 |
| 配置文件不生效 | 确认路径 `~/.codex/`，重启终端 |

**风险提示：**
- 企业用户建议 Azure OpenAI
- 个人开发者用中转平台需注意风险
- 做好备用方案避免单点依赖

---

## 十、快速开始Checklist

### 方案一：国内最简（中转平台）
- [ ] 注册中转平台
- [ ] 支付宝充值
- [ ] 获取API Key
- [ ] 安装Codex CLI
- [ ] 配置`~/.codex/config.toml`
- [ ] 开始使用

### 方案二：官方直连
- [ ] VPN准备（美国/欧洲节点）
- [ ] 注册OpenAI账号
- [ ] 获取海外手机号
- [ ] 注册WildCard虚拟信用卡
- [ ] 充值API
- [ ] 安装配置Codex CLI