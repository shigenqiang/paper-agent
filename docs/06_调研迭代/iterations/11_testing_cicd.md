# 迭代11：测试策略与CI/CD

## 迭代信息
- 迭代编号：11
- 迭代日期：2026-04-30
- 迭代阶段：测试策略与CI/CD

## 第一部分：测试策略

### 1.1 测试金字塔
```
        ┌─────────────┐
        │     E2E     │    少量、关键路径
        │   Tests     │
        ├─────────────┤
        │ Integration │    中等数量、模块交互
        │   Tests     │
        ├─────────────┤
        │   Unit      │    大量、快速、独立
        │   Tests     │
        └─────────────┘
```

### 1.2 Jest + React Testing Library配置
```javascript
// jest.config.js
module.exports = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss)$': 'identity-obj-proxy',
  },
  testPathIgnorePatterns: ['<rootDir>/node_modules/'],
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/**/*.test.{js,jsx}',
  ],
};
```

```javascript
// jest.setup.js
import '@testing-library/jest-dom';
```

### 1.3 组件测试示例
```jsx
// Button.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  test('renders with correct text', () => {
    render(<Button>点击我</Button>);
    expect(screen.getByText('点击我')).toBeInTheDocument();
  });

  test('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick}>点击我</Button>);
    fireEvent.click(screen.getByText('点击我'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test('is disabled when disabled prop is true', () => {
    render(<Button disabled>禁用</Button>);
    expect(screen.getByText('禁用')).toBeDisabled();
  });
});
```

### 1.4 Zustand Store测试
```javascript
// paperStore.test.js
import { renderHook, act } from '@testing-library/react';
import { usePaperStore } from './paperStore';

describe('paperStore', () => {
  test('setProject updates project', () => {
    const { result } = renderHook(() => usePaperStore());
    const newProject = { id: '1', title: 'Test Paper' };

    act(() => {
      result.current.setProject(newProject);
    });

    expect(result.current.project).toEqual(newProject);
  });

  test('addSection adds a section', () => {
    const { result } = renderHook(() => usePaperStore());
    const newSection = { id: '2', title: 'New Section' };

    act(() => {
      result.current.addSection(newSection);
    });

    expect(result.current.project.sections).toContainEqual(newSection);
  });
});
```

## 第二部分：Playwright E2E测试

### 2.1 Playwright配置
```javascript
// playwright.config.js
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
```

### 2.2 E2E测试示例
```javascript
// e2e/literature.spec.js
const { test, expect } = require('@playwright/test');

test.describe('文献管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/literature');
  });

  test('should display literature list', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('文献管理');
    await expect(page.locator('.literature-item')).toHaveCount(10);
  });

  test('should add new literature', async ({ page }) => {
    await page.click('button:has-text("导入文献")');
    await page.fill('input[type="file"]', 'test-paper.pdf');
    await expect(page.locator('.toast')).toContainText('导入成功');
  });

  test('should support responsive design', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('.mobile-menu')).toBeVisible();
  });
});
```

## 第三部分：GitHub Actions CI/CD

### 3.1 基础工作流
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v4

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: build
```

### 3.2 部署工作流
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: npm run deploy
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

## 第四部分：代码质量工具

### 4.1 ESLint + Prettier配置
```json
// .eslintrc.json
{
  "extends": ["airbnb", "airbnb-typescript", "prettier"],
  "plugins": ["prettier"],
  "rules": {
    "prettier/prettier": "error",
    "no-console": "warn",
    "react/react-in-jsx-scope": "off"
  }
}
```

```json
// .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2
}
```

### 4.2 Husky + lint-staged
```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged"
    }
  },
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{css,less,scss}": ["stylelint --fix", "prettier --write"]
  }
}
```

## 下次迭代方向
迭代12：最终总结与实施路线图
