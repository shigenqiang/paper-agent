/**
 * 知识图谱节点详情组件
 * 显示选中节点的详细信息
 */
import React from 'react'
import { Card, Typography, Space, Tag, Button, Descriptions, Divider, List, Avatar } from 'antd'
import {
  FileTextOutlined,
  CalendarOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  StarOutlined,
  CloseOutlined,
} from '@ant-design/icons'

const { Text, Title } = Typography

const GraphNodeDetail = ({ node, onClose, onBuildGraph }) => {
  if (!node) {
    return (
      <Card size="small" title="节点详情">
        <div className="text-center py-8 text-gray-400">
          <FileTextOutlined style={{ fontSize: 48 }} />
          <div className="mt-2">点击节点查看详情</div>
        </div>
      </Card>
    )
  }

  return (
    <Card
      size="small"
      title="节点详情"
      extra={
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          onClick={onClose}
        />
      }
    >
      <div className="space-y-3">
        {/* 标题 */}
        <div>
          <Title level={5} className="!mb-1">{node.title || node.label || '未知'}</Title>
          <Space size="small">
            <Tag color="blue">{node.type || 'paper'}</Tag>
            {node.year && (
              <Tag icon={<CalendarOutlined />}>{node.year}</Tag>
            )}
          </Space>
        </div>

        <Divider className="!my-2" />

        {/* 作者 */}
        {(node.authors || node.author) && (
          <div>
            <Text type="secondary" className="text-xs block mb-1">
              <TeamOutlined className="mr-1" />
              作者
            </Text>
            <Text>
              {Array.isArray(node.authors)
                ? node.authors.join(', ')
                : node.authors || node.author}
            </Text>
          </div>
        )}

        {/* 引用数 */}
        {(node.citations !== undefined || node.citedCount !== undefined) && (
          <div>
            <Text type="secondary" className="text-xs block mb-1">
              <StarOutlined className="mr-1" />
              引用数
            </Text>
            <Text strong>{node.citations || node.citedCount || 0}</Text>
          </div>
        )}

        {/* 摘要 */}
        {node.abstract && (
          <div>
            <Text type="secondary" className="text-xs block mb-1">摘要</Text>
            <Text className="text-xs" ellipsis={{ rows: 4 }}>
              {node.abstract}
            </Text>
          </div>
        )}

        {/* 来源 */}
        {node.source && (
          <div>
            <Text type="secondary" className="text-xs block mb-1">来源</Text>
            <Tag>{node.source}</Tag>
          </div>
        )}

        {/* URL */}
        {node.url && (
          <div>
            <Button
              type="link"
              size="small"
              href={node.url}
              target="_blank"
            >
              查看原文
            </Button>
          </div>
        )}

        <Divider className="!my-2" />

        {/* 操作按钮 */}
        <Space direction="vertical" className="w-full">
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => onBuildGraph?.(node.id)}
            block
          >
            构建相关图谱
          </Button>
        </Space>
      </div>
    </Card>
  )
}

export default GraphNodeDetail
