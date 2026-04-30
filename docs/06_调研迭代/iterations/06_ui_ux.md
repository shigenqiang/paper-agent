# 迭代6：UI/UX问题

## 迭代信息
- 迭代编号：06
- 迭代日期：2026-04-30
- 迭代阶段：UI/UX问题

## 第一部分：用户体验问题

### 1.1 缺少ErrorBoundary

#### 问题
- 组件渲染错误导致整页崩溃
- 没有降级UI

#### 解决方案
```jsx
// components/common/ErrorBoundary.jsx
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle={this.state.error?.message}
          extra={<Button type="primary" onClick={() => window.location.reload()}>刷新页面</Button>}
        />
      );
    }
    return this.props.children;
  }
}
```

### 1.2 缺少Loading状态

#### 问题
- API请求时没有统一的loading反馈
- 用户不知道操作是否在进行

#### 解决方案
```jsx
// components/common/LoadingOverlay.jsx
function LoadingOverlay({ spinning, tip }) {
  return (
    <Spin spinning={spinning} wrapperClassName="loading-overlay" tip={tip}>
      <div />
    </Spin>
  );
}

// 使用示例
function LiteraturePage() {
  const [loading, setLoading] = useState(false);

  return (
    <LoadingOverlay spinning={loading} tip="加载文献中...">
      <LiteratureList />
    </LoadingOverlay>
  );
}
```

### 1.3 缺少快捷键支持

#### 竞品参考
- ChatGPT：Ctrl+Enter发送、Escape清空
- Notion：Cmd+S保存、Cmd+Z撤销

#### 建议实现
```jsx
// hooks/useKeyboardShortcuts.js
function useKeyboardShortcuts(shortcuts) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = `${e.metaKey || e.ctrlKey ? 'cmd+' : ''}${e.key}`;
      const handler = shortcuts[key];
      if (handler) {
        e.preventDefault();
        handler(e);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// 使用
useKeyboardShortcuts({
  'cmd+s': () => savePaper(),
  'cmd+enter': () => sendMessage(),
  'escape': () => clearInput(),
});
```

## 第二部分：视觉一致性问题

### 2.1 缺少统一的空状态

#### 问题
- 各页面空状态不统一
- 用户体验不一致

#### 解决方案
```jsx
// components/common/EmptyState.jsx
function EmptyState({ icon, title, description, action }) {
  return (
    <div className="empty-state">
      {icon || <Empty description={false} />}
      <h4>{title}</h4>
      {description && <p>{description}</p>}
      {action && <Button type="primary" onClick={action.onClick}>{action.label}</Button>}
    </div>
  );
}

// 使用
<EmptyState
  icon={<FileTextOutlined />}
  title="暂无文献"
  description="点击按钮导入文献"
  action={{ label: '导入文献', onClick: () => {} }}
/>
```

### 2.2 缺少统一的确认对话框

#### 问题
- 删除等危险操作没有确认
- 各页面实现不统一

#### 解决方案
```jsx
// hooks/useConfirm.js
function useConfirm() {
  const [confirmProps, setConfirmProps] = useState({});

  const confirm = (props) => new Promise((resolve) => {
    setConfirmProps({
      open: true,
      title: props.title,
      content: props.content,
      onOk: () => { setConfirmProps({}); resolve(true); },
      onCancel: () => { setConfirmProps({}); resolve(false); },
    });
  });

  return { confirm, confirmProps };
}
```

## 第三部分：响应式问题

### 3.1 当前问题
- KnowledgeGraphPage在移动端不可用
- 没有响应式布局

### 3.2 建议
- 添加移动端适配
- 核心功能移动端可用

## 下次迭代方向
迭代07：功能缺失分析 - 核心功能完整性检查
