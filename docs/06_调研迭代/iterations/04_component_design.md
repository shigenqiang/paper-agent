# 迭代4：组件设计问题

## 迭代信息
- 迭代编号：04
- 迭代日期：2026-04-30
- 迭代阶段：组件设计问题

## 第一部分：组件拆分方案

### 1.1 KnowledgeGraphPage.jsx (1559行 → 5组件)

#### 拆分方案
```
KnowledgeGraphPage/
├── index.jsx                    # 主入口，组装子组件
├── GraphVisualization.jsx        # D3图谱渲染（~400行）
├── GraphControls.jsx             # 控制面板（~200行）
├── GraphSidebar.jsx             # 侧边详情面板（~300行）
├── GraphFilters.jsx             # 过滤器和搜索（~200行）
└── hooks/
    ├── useGraphData.js          # 数据获取和处理
    ├── useGraphLayout.js        # 布局算法
    └── useGraphInteraction.js   # 交互事件处理
```

#### 关键实现
```jsx
// index.jsx - 主组件只负责组装
function KnowledgeGraphPage() {
  const { nodes, edges, loading } = useGraphData();
  const { selectedNode, setSelectedNode } = useGraphInteraction();
  const layout = useGraphLayout();

  return (
    <div className="knowledge-graph">
      <GraphControls layout={layout} />
      <GraphVisualization nodes={nodes} edges={edges} selected={selectedNode} />
      {selectedNode && (
        <GraphSidebar node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  );
}
```

### 1.2 WritingPage.jsx (1137行 → 4组件)

#### 拆分方案
```
WritingPage/
├── index.jsx                    # 主入口
├── Editor/
│   ├── SectionEditor.jsx        # 章节编辑器（~300行）
│   ├── OutlineTree.jsx          # 大纲树形结构（~200行）
│   └── CitationPanel.jsx        # 引用管理面板（~200行）
├── Toolbar/
│   ├── FormatToolbar.jsx        # 格式工具栏（~150行）
│   └── WritingAssistant.jsx     # AI写作助手（~200行）
└── hooks/
    ├── usePaperSections.js      # 章节管理
    └── useAutoSave.js           # 自动保存
```

### 1.3 LiteraturePage.jsx (913行 → 3组件)

#### 拆分方案
```
LiteraturePage/
├── index.jsx                    # 主入口
├── LiteratureList.jsx           # 文献列表（~300行）
├── LiteratureDetail.jsx         # 文献详情（~250行）
├── ImportPanel.jsx              # 导入面板（~200行）
└── hooks/
    ├── useLiteratureSearch.js   # 搜索逻辑
    └── useLiteratureImport.js   # 导入逻辑
```

## 第二部分：公共组件抽象

### 2.1 缺失的公共组件

| 组件名 | 用途 | 建议位置 |
|--------|------|----------|
| OperationBar | 列表操作栏（编辑、删除等） | components/common/ |
| ConfirmDialog | 确认对话框 | components/common/ |
| EmptyState | 空状态展示 | components/common/ |
| LoadingOverlay | 加载遮罩 | components/common/ |
| ErrorBoundary | 错误边界 | components/common/ |

### 2.2 组件设计规范建议

```jsx
// components/common/OperationBar.jsx
function OperationBar({ actions, selectedCount }) {
  return (
    <div className="operation-bar">
      <span>{selectedCount}项选中</span>
      <Space>
        {actions.map(action => (
          <Button
            key={action.key}
            icon={action.icon}
            onClick={action.onClick}
            disabled={action.disabled}
          >
            {action.label}
          </Button>
        ))}
      </Space>
    </div>
  );
}
```

## 第三部分：AIAssistantPage问题分析

### 3.1 模式切换丢失上下文问题

#### 问题根因
```jsx
// 当前实现：模式切换时重新挂载组件
const [mode, setMode] = useState('chat'); // 'chat' | 'agent'

// 模式切换导致状态丢失
{mode === 'chat' ? <ChatMode /> : <AgentMode />}
```

#### 解决方案
```jsx
// 方案1：保持状态
const [sharedContext, setSharedContext] = useState({});
<ChatMode context={sharedContext} onContextUpdate={setSharedContext} />
<AgentMode context={sharedContext} onContextUpdate={setSharedContext} />

// 方案2：使用Context共享状态
const AIContext = createContext({});
<AIContext.Provider value={sharedState}>
  {mode === 'chat' ? <ChatMode /> : <AgentMode />}
</AIContext.Provider>
```

### 3.2 流式输出与打字效果

#### 竞品参考
ChatGPT使用SSE实现流式输出，前端逐步消费响应并显示打字效果。

#### 建议实现
```jsx
function useStreamingMessage() {
  const [displayText, setDisplayText] = useState('');
  const messageIdRef = useRef(null);

  const startStream = async (message) => {
    const eventSource = new EventSource(/*...*/);
    eventSource.onmessage = (e) => {
      setDisplayText(prev => prev + e.data); // 打字效果
    };
  };

  return { displayText, startStream };
}
```

## 下次迭代方向
迭代05：状态管理问题 - Zustand store拆分方案
