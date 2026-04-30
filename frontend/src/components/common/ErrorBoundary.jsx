/**
 * ErrorBoundary - 全局错误边界组件
 * 捕获子组件树的JavaScript错误，显示降级UI
 */
import React from 'react'
import { Result, Button, Card } from 'antd'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  handleGoBack = () => {
    this.setState({ hasError: false, error: null })
    window.history.back()
  }

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message || '页面发生错误'
      const isDevelopment = import.meta.env.DEV

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <Card className="max-w-lg w-full">
            <Result
              status="error"
              title="页面出现错误"
              subTitle={errorMessage}
              extra={
                <div className="flex gap-3 justify-center">
                  <Button onClick={this.handleGoBack}>
                    返回上页
                  </Button>
                  <Button type="primary" onClick={this.handleReload}>
                    刷新页面
                  </Button>
                </div>
              }
            />
            {isDevelopment && this.state.error?.stack && (
              <div className="mt-4 p-3 bg-gray-100 rounded text-xs overflow-auto">
                <details className="cursor-pointer">
                  <summary className="font-mono text-gray-600">错误堆栈（开发模式）</summary>
                  <pre className="mt-2 whitespace-pre-wrap">{this.state.error.stack}</pre>
                </details>
              </div>
            )}
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
