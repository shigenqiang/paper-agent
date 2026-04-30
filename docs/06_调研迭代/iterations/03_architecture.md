# 迭代3：架构问题分析

## 迭代信息
- 迭代编号：03
- 迭代日期：2026-04-30
- 迭代阶段：架构问题分析

## 第一部分：核心架构问题

### 1.1 组件职责不清（根本问题）

#### 问题详情
KnowledgeGraphPage.jsx (1559行) 承担了过多职责：
- 图谱渲染（D3.js相关）
- 数据处理和转换
- 交互逻辑（缩放、拖拽、点击）
- UI状态管理（选中的节点、过滤条件）
- API调用和错误处理

#### 竞品对比
- ChatGPT：将ChatArea、InputArea、Sidebar完全分离
- Claude：Artifacts功能独立组件实现
- 我方：所有逻辑混在一个文件

#### 改进建议
**P0优先级**：将KnowledgeGraphPage拆分为：
1. `GraphVisualization.jsx` - 纯D3图谱渲染
2. `GraphControls.jsx` - 控制面板（过滤、布局切换）
3. `GraphSidebar.jsx` - 侧边详情面板
4. `useGraphData.js` - 图谱数据Hook
5. `useGraphInteraction.js` - 交互逻辑Hook

### 1.2 状态管理集中化

#### 问题详情
paperStore.js (133行) 承担6种职责：
1. 项目管理（project, sections, citations）
2. 消息管理（messages, isStreaming）
3. 文献管理（literature）
4. UI状态（sidebarCollapsed, theme）

#### 竞品对比
- Notion：按功能域拆分store（database store, block store, user store）
- Ant Design Pro：dva model按业务拆分

#### 改进建议
**P0优先级**：拆分为3个store：
1. `useProjectStore` - 项目管理
2. `useChatStore` - 对话和消息
3. `useUIStore` - UI状态（主题、侧边栏）

### 1.3 代码重复问题

#### 问题1：DEFAULT_SECTIONS
出现在3处：
1. `store/paperStore.js:4-16`
2. `pages/WritingPage.jsx` (约200行)
3. `pages/OutlinePage.jsx` (约30行)

**改进**：提取到 `constants/paper.js`

#### 问题2：SOURCE_CONFIG
出现在3处API调用

**改进**：统一到 `config/sources.js`

## 第二部分：组件设计问题

### 2.1 页面组件规模

| 组件 | 行数 | 问题 | 建议拆分 |
|------|------|------|----------|
| KnowledgeGraphPage.jsx | 1559 | 职责过多 | 5个子组件 |
| WritingPage.jsx | 1137 | 混合逻辑 | 4个子组件 |
| LiteraturePage.jsx | 913 | 功能复杂 | 3个子组件 |

### 2.2 缺少公共组件抽象

当前问题：
- 没有`components/common/`目录
- 重复的UI模式未抽象（如列表操作栏）

建议：
- 提取 `OperationBar` 公共组件
- 提取 `ConfirmDialog` 公共组件
- 提取 `EmptyState` 公共组件

## 第三部分：API层问题

### 3.1 当前api.js结构
- 222行，涵盖5个模块API
- 部分函数使用原生fetch，部分使用axios
- 错误处理不统一

### 3.2 改进建议
1. 统一使用axios或fetch，不混用
2. 提取统一的错误处理中间件
3. 添加请求重试机制
4. API按域分组到不同文件

## 第四部分：搜索发现（8次搜索）

### 搜索1：React组件拆分最佳实践
- 关键词：React component split refactoring best practices 2025
- 发现：
  1. 每个组件不超过300-500行是最佳实践
  2. 动态import()可实现代码拆分和懒加载
  3. 组件应按职责拆分

### 搜索2：Zustand状态管理
- 关键词：Zustand store split by responsibility React 2025
- 发现：
  1. Zustand极简API，仅需create、setState、getState
  2. 支持中间件（持久化、日志）
  3. 无需Provider包裹

### 搜索3：React自定义Hooks最佳实践
- 关键词：React custom hooks best practices 2025
- 来源：https://zhuanlan.zhihu.com/p/416849812
- 发现：
  1. 自定义Hooks用于提取组件逻辑
  2. useWindowSize、useBoolean等通用Hook可复用
  3. 命名规范：use前缀

### 搜索4：React代码重复DRY原则
- 关键词：React code duplication DRY principle 2025
- 来源：https://blog.csdn.net/Dontla/article/details/151334810
- 发现：
  1. DRY原则：避免重复代码
  2. 抽象和封装是核心
  3. 降低维护成本，提高可读性

### 搜索5：React性能优化
- 关键词：React performance optimization re-render 2025
- 来源：https://cloud.tencent.com/developer/article/2601121
- 发现：
  1. React.memo避免不必要的重新渲染
  2. useMemo和useCallback缓存
  3. 虚拟列表优化长列表

### 搜索6：Ant Design最佳实践
- 关键词：Ant Design component library best practices 2025
- 来源：https://blog.csdn.net/gitblog_00845/article/details/152286617
- 发现：
  1. 统一设计规范确保风格一致
  2. 支持主题定制（cssVar模式）
  3. 分层架构

### 搜索7：React流式响应SSE
- 关键词：React streaming SSE EventSource implementation 2025
- 来源：https://blog.csdn.net/yzcoder/article/details/128378753
- 发现：
  1. Streaming SSR分段传输HTML
  2. Selective Hydration按需注水
  3. 提高首屏加载速度

### 搜索8：React打字效果
- 关键词：React typing effect streaming response chat 2025
- 来源：https://github.com/activat0r/ReactTypingEffectScript
- 发现：
  1. 打字机效果提升用户体验
  2. 逐字显示模拟真实打字
  3. 可自定义速度和延迟

## 第五部分：问题汇总

### 问题清单（按优先级）

| ID | 问题 | 位置 | 严重程度 |
|----|------|------|----------|
| A1 | 组件过大 | KnowledgeGraphPage.jsx | P0 |
| A2 | 组件过大 | WritingPage.jsx | P0 |
| A3 | Store职责过多 | paperStore.js | P0 |
| A4 | 代码重复 | DEFAULT_SECTIONS | P1 |
| A5 | 代码重复 | SOURCE_CONFIG | P1 |
| A6 | 组件过大 | LiteraturePage.jsx | P1 |
| A7 | 模式切换丢上下文 | AIAssistantPage.jsx | P1 |
| A8 | 缺少ErrorBoundary | 全局 | P1 |
| A9 | 缺少loading态 | 多处 | P2 |
| A10 | 缺少快捷键 | 全局 | P2 |

## 下次迭代方向
迭代04：组件设计问题 - 深入分析各页面组件的拆分方案
