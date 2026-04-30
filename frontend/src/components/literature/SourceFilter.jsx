/**
 * SourceFilter - 数据源筛选组件
 */
import React from 'react'
import { Card, Button, Space, Typography, Switch, message } from 'antd'
import { SOURCE_CONFIG_LIST, SOURCE_CONFIG } from '../../constants/source'

const { Text } = Typography

/**
 * SourceFilter组件
 * @param {string[]} sources - 当前选中的数据源
 * @param {function} onToggle - 切换数据源的回调
 * @param {function} onSave - 保存设置的回调
 */
export function SourceFilter({
  sources = [],
  onToggle,
  onSave,
  compact = false
}) {
  const handleToggle = (key) => {
    if (sources.includes(key)) {
      if (sources.length > 1) {
        onToggle(key)
      } else {
        message.warning('至少需要保留一个数据源')
      }
    } else {
      onToggle(key)
    }
  }

  return (
    <Card
      size="small"
      title={compact ? null : <Text strong>数据来源</Text>}
      extra={
        onSave && (
          <Button type="link" size="small" onClick={onSave}>
            保存
          </Button>
        )
      }
    >
      <Space wrap size={compact ? 4 : 8}>
        {SOURCE_CONFIG_LIST.map(source => {
          const isActive = sources.includes(source.key)
          const config = SOURCE_CONFIG[source.key] || {}

          return (
            <Button
              key={source.key}
              type={isActive ? 'primary' : 'default'}
              size={compact ? 'small' : 'middle'}
              onClick={() => handleToggle(source.key)}
              style={{
                borderColor: isActive ? config.color : undefined,
                backgroundColor: isActive ? config.color : undefined,
              }}
            >
              {config.icon}
              {!compact && <span style={{ marginLeft: 4 }}>{source.label}</span>}
            </Button>
          )
        })}
      </Space>
    </Card>
  )
}

export default SourceFilter
