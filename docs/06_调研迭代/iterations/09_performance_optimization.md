# 迭代9：性能优化与最佳实践

## 迭代信息
- 迭代编号：09
- 迭代日期：2026-04-30
- 迭代阶段：性能优化与最佳实践

## 第一部分：代码分割与加载优化

### 1.1 React.lazy与Suspense

#### 核心原理
```jsx
// 路由级别的代码分割
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'));
const WritingPage = lazy(() => import('./pages/WritingPage'));
const LiteraturePage = lazy(() => import('./pages/LiteraturePage'));

function App() {
  return (
    <Suspense fallback={<LoadingOverlay spinning tip="加载中..." />}>
      <Routes>
        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="/writing" element={<WritingPage />} />
        <Route path="/literature" element={<LiteraturePage />} />
      </Routes>
    </Suspense>
  );
}
```

#### 组件级别的分割
```jsx
// 大组件内部动态导入
const GraphVisualization = lazy(() => import('./components/GraphVisualization'));
const GraphControls = lazy(() => import('./components/GraphControls'));

// 使用
<Suspense fallback={<Skeleton />}>
  <GraphVisualization />
</Suspense>
```

### 1.2 预加载策略
```jsx
// 预加载即将使用的路由
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'));

// Hover时预加载
<div onMouseEnter={() => { KnowledgeGraphPage.preload(); }}>
  <Link to="/knowledge-graph">知识图谱</Link>
</div>
```

## 第二部分：Zustand中间件最佳实践

### 2.1 persist中间件配置
```javascript
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import localStorage from 'zustand/storage';

export const usePaperStore = create(
  persist(
    (set, get) => ({
      // 状态
    }),
    {
      name: 'paper-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        // 只持久化特定字段
        return {
          project: state.project,
          literature: state.literature,
          messages: state.messages,
        };
      },
      // 开发环境排除某些状态
      exclude: {
        paths: ['isStreaming', 'loading'],
        distance: 1,
      },
    }
  )
);
```

### 2.2 devtools中间件
```javascript
import { devtools, persist } from 'zustand/middleware';

const useStore = create(
  devtools(
    persist(
      (set) => ({
        // 状态和操作
      }),
      { name: 'PaperStore' }
    ),
    { enabled: process.env.NODE_ENV === 'development' }
  )
);
```

## 第三部分：错误边界与监控

### 3.1 错误边界实现
```jsx
// components/ErrorBoundary.jsx
import React from 'react';
import { Result, Button } from 'antd';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught:', error, errorInfo);
    // 可发送到错误监控服务
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle={this.state.error?.message}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

### 3.2 错误监控集成
```javascript
// 错误上报服务
export const errorReporter = {
  report: (error, errorInfo) => {
    // 发送到监控服务
    console.log('Error reported:', { error, errorInfo });
  },
};

// 使用
<ErrorBoundary onError={errorReporter.report}>
  <App />
</ErrorBoundary>
```

## 第四部分：Ant Design主题定制

### 4.1 基础主题配置
```javascript
// theme/antdTheme.js
export const antdTheme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 4,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
    // 暗色模式
    colorBgContainer: '#141414',
    colorText: '#ffffff',
  },
  components: {
    Button: {
      primaryShadow: 'none',
    },
    Menu: {
      darkItemBg: '#001529',
    },
  },
};
```

### 4.2 动态主题切换
```jsx
// context/ThemeContext.jsx
import { ConfigProvider } from 'antd';
import React, { createContext, useContext, useState } from 'react';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');

  const themeConfig = {
    light: { /* 亮色主题 */ },
    dark: { /* 暗色主题 */ },
  }[theme];

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <ConfigProvider theme={themeConfig}>
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}
```

## 第五部分：性能优化清单

| 优化项 | 预期效果 | 工作量 |
|--------|----------|--------|
| 路由级代码分割 | 首屏加载减少40% | 低 |
| 组件级懒加载 | 主bundle减小30% | 中 |
| 预加载策略 | 页面切换速度提升 | 低 |
| persist优化 | 存储性能提升 | 低 |
| 错误边界 | 稳定性提升 | 低 |
| 主题定制 | UI一致性 | 中 |

## 下次迭代方向
继续迭代10：可访问性与国际化
