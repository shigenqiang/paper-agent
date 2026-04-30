# 迭代7：功能缺失分析

## 迭代信息
- 迭代编号：07
- 迭代日期：2026-04-30
- 迭代阶段：功能缺失分析

## 第一部分：核心功能缺失

### 1.1 论文导出功能

#### 缺失情况
- 没有导出为Word/PDF功能
- 用户无法下载完成的论文

#### 竞品对比
- Paperpal：支持多种导出格式
- Notion：支持导出为PDF、Markdown等

#### 建议实现
```javascript
// services/exportService.js
export const exportService = {
  exportToWord: async (paper) => {
    // 使用docx库生成Word文档
  },
  exportToPDF: async (paper) => {
    // 使用jspdf或其他库生成PDF
  },
  exportToMarkdown: (paper) => {
    // 直接转换sections为markdown
  }
};
```

### 1.2 批量操作

#### 缺失情况
- 文献无法批量选择和操作
- 论文章节无法批量管理

#### 建议实现
```jsx
// LiteratureList支持批量选择
<Table
  rowSelection={{
    selectedRowKeys,
    onChange: setSelectedRowKeys,
  }}
/>
<BatchActions selectedCount={selectedRowKeys.length}>
  <Button onClick={batchDelete}>批量删除</Button>
  <Button onClick={batchExport}>批量导出</Button>
</BatchActions>
```

### 1.3 版本控制

#### 缺失情况
- 没有版本历史
- 无法回滚到之前的版本

#### 竞品参考
- Notion：完整的版本历史
- Google Docs：版本管理

#### 建议实现
```javascript
// 版本记录
interface PaperVersion {
  id: string;
  paperId: string;
  sections: Section[];
  createdAt: Date;
  description: string;
}

// store中添加版本相关状态
versions: [],
saveVersion: (description) => {/*...*/},
restoreVersion: (versionId) => {/*...*/},
```

## 第二部分：辅助功能缺失

### 2.1 快捷键提示

#### 缺失情况
- 没有快捷键提示
- 用户不知道可用快捷键

#### 建议实现
```jsx
// components/common/KeyboardShortcutsHelp.jsx
// 在SettingsPage或通过?键触发
const shortcuts = [
  { key: 'Ctrl/Cmd + S', action: '保存' },
  { key: 'Ctrl/Cmd + Enter', action: '发送消息' },
  { key: 'Escape', action: '清空输入' },
];
```

### 2.2 离线支持

#### 缺失情况
- 没有离线缓存
- 断网后无法工作

#### 竞品参考
- Notion：离线可用
- Paperpal：PWA支持

#### 建议实现
- 添加Service Worker
- 使用IndexedDB缓存数据

### 2.3 导入功能增强

#### 缺失情况
- 仅支持PDF导入
- 不支持批量导入

#### 建议实现
```javascript
// 支持的导入格式
const supportedFormats = {
  pdf: ['.pdf'],
  word: ['.doc', '.docx'],
  markdown: ['.md', '.markdown'],
  bibtex: ['.bib'],
};
```

## 第三部分：功能优先级

| 功能 | 优先级 | 工作量 | 建议 |
|------|--------|--------|------|
| 论文导出 | P1 | 中 | 优先实现PDF导出 |
| 批量操作 | P1 | 低 | 文献列表批量选择 |
| ErrorBoundary | P1 | 低 | 全局错误处理 |
| 快捷键 | P2 | 低 | 全局快捷键支持 |
| 版本控制 | P2 | 高 | 建议后期实现 |
| 离线支持 | P2 | 高 | 建议后期实现 |

## 下次迭代方向
迭代08：问题汇总与建议 - 最终总结
