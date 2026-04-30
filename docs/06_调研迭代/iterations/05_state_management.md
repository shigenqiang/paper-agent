# 迭代5：状态管理问题

## 迭代信息
- 迭代编号：05
- 迭代日期：2026-04-30
- 迭代阶段：状态管理问题

## 第一部分：当前Store分析

### 1.1 paperStore.js现状
```javascript
// 当前：单一store承担6种职责
export const usePaperStore = create(
  persist(
    (set, get) => ({
      // 项目管理
      project: { id, title, sections, citations, status },
      setProject, setTitle, addSection, updateSection, deleteSection,

      // 消息管理
      messages: [],
      addMessage, updateMessage,
      isStreaming: false,
      setStreaming,

      // 文献管理
      literature: [],
      addLiterature, deleteLiterature, setLiterature, updateLiterature,

      // 引用管理
      addCitation, removeCitation,

      // UI状态
      sidebarCollapsed: false,
      toggleSidebar,
      theme: 'light',
    })
  )
);
```

### 1.2 问题识别
1. 违背单一职责原则
2. 状态字段逻辑不相关
3. 持久化策略不清晰
4. 难以进行单元测试

## 第二部分：Store拆分方案

### 2.1 拆分后的Store结构
```
store/
├── projectStore.js    # 项目管理
├── chatStore.js       # 对话消息
├── literatureStore.js # 文献管理
└── uiStore.js         # UI状态
```

### 2.2 具体实现

#### projectStore.js
```javascript
// 项目管理 - sections, citations, status
export const useProjectStore = create(
  persist(
    (set, get) => ({
      project: {
        id: null,
        title: '',
        sections: DEFAULT_SECTIONS,
        citations: [],
        status: 'idle'
      },

      setProject: (project) => set({ project }),
      setTitle: (title) => set(state => ({
        project: { ...state.project, title }
      })),
      addSection: (section) => set(state => ({
        project: { ...state.project, sections: [...state.project.sections, section] }
      })),
      updateSection: (id, content) => set(state => ({
        project: {
          ...state.project,
          sections: state.project.sections.map(s =>
            s.id === id ? { ...s, content } : s
          )
        }
      })),
      deleteSection: (id) => set(state => ({
        project: {
          ...state.project,
          sections: state.project.sections.filter(s => s.id !== id)
        }
      })),
      addCitation: (citation) => set(state => ({
        project: { ...state.project, citations: [...state.project.citations, citation] }
      })),
      removeCitation: (id) => set(state => ({
        project: {
          ...state.project,
          citations: state.project.citations.filter(c => c.id !== id)
        }
      })),
      resetProject: () => set({
        project: { id: null, title: '', sections: DEFAULT_SECTIONS, citations: [], status: 'idle' }
      })
    }),
    { name: 'paper-project-storage' }
  )
);
```

#### chatStore.js
```javascript
// 对话消息 - messages, isStreaming
export const useChatStore = create(
  persist(
    (set, get) => ({
      messages: [],
      isStreaming: false,

      addMessage: (message) => set(state => ({
        messages: [...state.messages, message]
      })),
      updateMessage: (id, updates) => set(state => ({
        messages: state.messages.map(m =>
          m.id === id ? { ...m, ...updates } : m
        )
      })),
      clearMessages: () => set({ messages: [] }),
      setStreaming: (isStreaming) => set({ isStreaming }),
    }),
    { name: 'paper-chat-storage', partialize: (state) => ({ messages: state.messages }) }
  )
);
```

#### literatureStore.js
```javascript
// 文献管理 - literature
export const useLiteratureStore = create(
  persist(
    (set) => ({
      literature: [],
      addLiterature: (item) => set(state => ({ literature: [...state.literature, item] })),
      deleteLiterature: (id) => set(state => ({
        literature: state.literature.filter(item => item.id !== id)
      })),
      setLiterature: (items) => set({ literature: items }),
      updateLiterature: (id, updates) => set(state => ({
        literature: state.literature.map(l => l.id === id ? { ...l, ...updates } : l)
      })),
    }),
    { name: 'paper-literature-storage' }
  )
);
```

#### uiStore.js
```javascript
// UI状态 - sidebarCollapsed, theme
export const useUIStore = create(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'light',
      toggleSidebar: () => set(state => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'paper-ui-storage' }
  )
);
```

## 第三部分：常量提取

### 3.1 DEFAULT_SECTIONS常量
```javascript
// constants/paper.js
export const DEFAULT_SECTIONS = [
  { id: '1', title: '第1章 引言', parentId: null, content: '' },
  { id: '1-1', title: '1.1 研究背景', parentId: '1', content: '' },
  { id: '1-2', title: '1.2 研究意义', parentId: '1', content: '' },
  { id: '1-3', title: '1.3 研究目标', parentId: '1', content: '' },
  { id: '2', title: '第2章 文献综述', parentId: null, content: '' },
  { id: '2-1', title: '2.1 国内研究现状', parentId: '2', content: '' },
  { id: '2-2', title: '2.2 国外研究现状', parentId: '2', content: '' },
  { id: '3', title: '第3章 研究方法', parentId: null, content: '' },
  { id: '4', title: '第4章 实验结果', parentId: null, content: '' },
  { id: '5', title: '第5章 讨论', parentId: null, content: '' },
  { id: '6', title: '第6章 结论', parentId: null, content: '' },
];
```

## 下次迭代方向
迭代06：UI/UX问题 - 交互体验和视觉设计问题
