/**
 * SourceSettingsModal - 数据源设置弹窗组件
 */
import React from 'react'
import { Modal, Space, Typography, Switch, Alert } from 'antd'
import { DatabaseOutlined } from '@ant-design/icons'
import { SOURCE_CONFIG_LIST } from '../../constants/source'

const { Text } = Typography

/**
 * SourceSettingsModal组件
 * @param {boolean} open - 是否打开
 * @param {string[]} sources - 启用的数据源
 * @param {function} onToggle - 切换数据源回调
 * @param {function} onSave - 保存设置回调
 * @param {function} onClose - 关闭回调
 */
export function SourceSettingsModal({
  open,
  sources,
  onToggle,
  onSave,
  onClose,
}) {
  return (
    <Modal
      title={
        <Space>
          <DatabaseOutlined className="text-blue-500" />
          <span>学术数据来源设置</span>
        </Space>
      }
      open={open}
      onOk={onSave}
      onCancel={onClose}
      okText="保存设置"
      cancelText="取消"
      width={500}
    >
      <Alert
        message="数据来源设置"
        description="选择系统从哪些学术数据库搜索论文。不同来源涵盖不同领域，建议全部启用。"
        type="info"
        showIcon
        icon={<DatabaseOutlined />}
        className="!mb-4"
      />

      <Text type="secondary" className="block mb-3">
        当前启用的数据来源（共 {sources.length} 个）:
      </Text>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {SOURCE_CONFIG_LIST.map(source => {
          const isEnabled = sources.includes(source.key)
          return (
            <div
              key={source.key}
              onClick={() => onToggle(source.key)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                isEnabled
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-gray-50 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: source.color }}
                  ></div>
                  <Text strong className={isEnabled ? 'text-blue-700' : 'text-gray-600'}>
                    {source.label}
                  </Text>
                </div>
                <Switch size="small" checked={isEnabled} onChange={() => onToggle(source.key)} />
              </div>
              <Text type="secondary" className="text-xs">{source.desc}</Text>
            </div>
          )
        })}
      </div>
    </Modal>
  )
}

export default SourceSettingsModal