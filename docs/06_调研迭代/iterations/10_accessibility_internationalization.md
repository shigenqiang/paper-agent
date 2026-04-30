# 迭代10：可访问性与国际化

## 迭代信息
- 迭代编号：10
- 迭代日期：2026-04-30
- 迭代阶段：可访问性与国际化

## 第一部分：可访问性(A11y)最佳实践

### 1.1 ARIA属性使用

#### 基础ARIA属性
```jsx
// 语义化HTML优先，ARIA作为补充
<button aria-label="关闭" aria-expanded={isOpen}>
  <CloseIcon />
</button>

// 表单关联
<div role="group" aria-labelledby="shipping-address">
  <h3 id="shipping-address">收货地址</h3>
  {/* 表单字段 */}
</div>

// 实时区域
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>
```

### 1.2 键盘导航支持
```jsx
// 使用tabindex管理焦点
<div
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleSelect();
    }
  }}
>
  可键盘选择的项目
</div>

// 焦点陷阱（模态框）
function Modal({ isOpen, onClose, children }) {
  const modalRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      focusableElements[0]?.focus();
    }
  }, [isOpen]);

  return (
    <div ref={modalRef} role="dialog" aria-modal="true">
      {children}
    </div>
  );
}
```

### 1.3 屏幕阅读器支持
```jsx
// 视觉隐藏但屏幕阅读器可读
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

// 使用
<span className="sr-only">当前页面导航到第{currentPage}页</span>
```

## 第二部分：Ant Design无障碍支持

### 2.1 Table无障碍
```jsx
// 大数据量表格使用虚拟滚动
import { Table } from 'antd';

const VirtualTable = () => {
  return (
    <Table
      components={{
        body: {
          wrapper: (props) => <Virtuoso {...props} />,
        },
      }}
      columns={columns}
      dataSource={largeDataset}
    />
  );
};
```

### 2.2 Form无障碍
```jsx
// 表单验证与无障碍结合
<Form>
  <Form.Item
    label="邮箱"
    name="email"
    rules={[{ required: true, type: 'email' }]}
    validateStatus={errors.email ? 'error' : ''}
    help={errors.email?.message}
  >
    <Input aria-describedby="email-help" />
  </Form.Item>
  <span id="email-help" className="sr-only">
    请输入有效的邮箱地址
  </span>
</Form>
```

## 第三部分：国际化(i18n)

### 3.1 react-i18next配置
```javascript
// i18n/index.js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import zh from './locales/zh.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    lng: 'zh',
    fallbackLng: 'zh',
    interpolation: { escapeValue: false },
  });

export default i18n;
```

### 3.2 翻译文件结构
```json
// locales/zh.json
{
  "common": {
    "save": "保存",
    "cancel": "取消",
    "delete": "删除"
  },
  "literature": {
    "title": "文献管理",
    "import": "导入文献",
    "search": "搜索文献"
  },
  "writing": {
    "outline": "论文大纲",
    "citation": "引用管理"
  }
}
```

### 3.3 组件中使用
```jsx
import { useTranslation } from 'react-i18next';

function LiteraturePage() {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
  };

  return (
    <div>
      <h1>{t('literature.title')}</h1>
      <Button onClick={() => changeLanguage('en')}>English</Button>
      <Button onClick={() => changeLanguage('zh')}>中文</Button>
    </div>
  );
}
```

## 第四部分：SEO优化

### 4.1 Next.js SSR方案
```jsx
// 静态生成
export async function getStaticProps() {
  return {
    props: { paperData },
    revalidate: 60, // ISR
  };
}

// 服务端渲染
export async function getServerSideProps() {
  const res = await fetch('https://api.example.com/papers');
  const paperData = await res.json();

  return { props: { paperData } };
}
```

### 4.2 Meta标签优化
```jsx
import Head from 'next/head';

function PaperPage({ title, description }) {
  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
      </Head>
    </>
  );
}
```

## 第五部分：Monorepo架构

### 5.1 pnpm workspace配置
```yaml
# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

### 5.2 目录结构
```
├── apps
│   ├── web              # 主应用
│   └── admin            # 管理后台
├── packages
│   ├── ui              # 共享UI组件
│   ├── utils           # 工具函数
│   └── constants       # 常量
├── pnpm-workspace.yaml
└── package.json
```

## 下次迭代方向
迭代11：测试策略与CI/CD
