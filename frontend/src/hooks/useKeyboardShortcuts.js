/**
 * useKeyboardShortcuts - 快捷键Hook
 * 提供统一的快捷键支持
 */
import { useEffect, useCallback } from 'react'

/**
 * 快捷键配置格式
 * {
 *   'ctrl+s': handleSave,
 *   'ctrl+enter': handleSubmit,
 *   'escape': handleCancel,
 * }
 */

/**
 * useKeyboardShortcuts - 注册快捷键
 * @param {Object} shortcuts - 快捷键映射表
 * @param {boolean} enabled - 是否启用
 */
export function useKeyboardShortcuts(shortcuts, enabled = true) {
  const handleKeyDown = useCallback((event) => {
    if (!enabled) return

    // 构建修饰键前缀
    const modifiers = []
    if (event.ctrlKey || event.metaKey) modifiers.push('ctrl')
    if (event.shiftKey) modifiers.push('shift')
    if (event.altKey) modifiers.push('alt')

    // 获取按下的键（统一转小写）
    const key = event.key.toLowerCase()

    // 组合快捷键
    const shortcutKey = modifiers.length > 0
      ? `${modifiers.join('+')}+${key}`
      : key

    // 查找对应的处理器
    const handler = shortcuts[shortcutKey]
    if (handler) {
      // 避免与其他快捷键冲突
      event.preventDefault()
      handler(event)
    }
  }, [shortcuts, enabled])

  useEffect(() => {
    if (!enabled) return

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown, enabled])
}

/**
 * useSaveShortcut - 保存快捷键 (Ctrl/Cmd + S)
 */
export function useSaveShortcut(onSave, enabled = true) {
  useKeyboardShortcuts({
    'ctrl+s': onSave,
    'meta+s': onSave, // Mac
  }, enabled)
}

/**
 * useEscapeShortcut - 取消/关闭快捷键 (Escape)
 */
export function useEscapeShortcut(onEscape, enabled = true) {
  useKeyboardShortcuts({
    'escape': onEscape,
  }, enabled)
}

/**
 * useSubmitShortcut - 提交快捷键 (Ctrl/Cmd + Enter)
 */
export function useSubmitShortcut(onSubmit, enabled = true) {
  useKeyboardShortcuts({
    'ctrl+enter': onSubmit,
    'meta+enter': onSubmit, // Mac
  }, enabled)
}

export default useKeyboardShortcuts
