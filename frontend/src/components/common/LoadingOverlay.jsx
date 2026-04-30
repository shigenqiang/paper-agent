/**
 * LoadingOverlay - 全局加载状态组件
 * 提供统一的loading体验
 */
import React from 'react'
import { Spin, Card } from 'antd'

/**
 * LoadingOverlay - 加载遮罩组件
 * @param {boolean} spinning - 是否显示loading
 * @param {string} tip - loading提示文字
 * @param {React.ReactNode} children - 被包裹的内容
 * @param {string} wrapperClassName - 包裹层className
 */
function LoadingOverlay({
  spinning = true,
  tip = '加载中...',
  children,
  wrapperClassName = '',
  size = 'default',
}) {
  return (
    <div className={`relative ${wrapperClassName}`}>
      <Spin spinning={spinning} tip={tip} size={size}>
        <div className={spinning ? 'opacity-60 pointer-events-none' : ''}>
          {children}
        </div>
      </Spin>
    </div>
  )
}

/**
 * PageLoading - 页面级加载状态
 */
export function PageLoading({ message = '页面加载中...' }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="text-center">
        <Spin size="large" tip={message} />
      </Card>
    </div>
  )
}

/**
 * InlineLoading - 行内加载状态
 */
export function InlineLoading({ message = '加载中...' }) {
  return (
    <span className="inline-flex items-center gap-2 text-gray-500">
      <Spin size="small" />
      <span className="text-sm">{message}</span>
    </span>
  )
}

/**
 * OverlayLoading - 全屏遮罩加载
 */
export function OverlayLoading({ visible, message = '加载中...' }) {
  if (!visible) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
      <Card className="text-center shadow-lg">
        <Spin size="large" tip={message} />
      </Card>
    </div>
  )
}

export default LoadingOverlay
