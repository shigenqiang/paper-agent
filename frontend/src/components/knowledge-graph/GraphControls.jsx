/**
 * 知识图谱控制面板组件
 * 负责视图模式切换、缩放控制等
 */
import React from 'react'
import { Card, Button, Space, Slider, Select, Typography, Divider, Badge, Tooltip } from 'antd'
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  AimOutlined,
  ReloadOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons'

const { Text } = Typography

const VIEW_MODES = [
  { value: 'year', label: '按年份' },
  { value: 'community', label: '按社区' },
  { value: 'type', label: '按类型' },
  { value: 'degree', label: '按度数' },
]

const SORT_OPTIONS = [
  { value: 'citations', label: '引用数' },
  { value: 'year', label: '年份' },
  { value: 'title', label: '标题' },
]

const GraphControls = ({
  viewMode,
  onViewModeChange,
  zoomLevel,
  onZoomChange,
  sortBy,
  onSortChange,
  onFitView,
  onReload,
  stats,
}) => {
  return (
    <Card size="small" title="视图控制">
      <div className="space-y-4">
        {/* 视图模式 */}
        <div>
          <Text type="secondary" className="text-xs block mb-1">视图模式</Text>
          <Select
            value={viewMode}
            onChange={onViewModeChange}
            options={VIEW_MODES}
            className="w-full"
            size="small"
          />
        </div>

        {/* 排序方式 */}
        <div>
          <Text type="secondary" className="text-xs block mb-1">排序方式</Text>
          <Select
            value={sortBy}
            onChange={onSortChange}
            options={SORT_OPTIONS}
            className="w-full"
            size="small"
          />
        </div>

        <Divider className="!my-2" />

        {/* 缩放控制 */}
        <div>
          <Text type="secondary" className="text-xs block mb-1">
            缩放: {Math.round(zoomLevel * 100)}%
          </Text>
          <Slider
            min={0.1}
            max={2}
            step={0.1}
            value={zoomLevel}
            onChange={onZoomChange}
            tooltip={{ formatter: (v) => `${Math.round(v * 100)}%` }}
          />
          <Space>
            <Tooltip title="放大">
              <Button
                size="small"
                icon={<ZoomInOutlined />}
                onClick={() => onZoomChange(Math.min(zoomLevel + 0.1, 2))}
              />
            </Tooltip>
            <Tooltip title="缩小">
              <Button
                size="small"
                icon={<ZoomOutOutlined />}
                onClick={() => onZoomChange(Math.max(zoomLevel - 0.1, 0.1))}
              />
            </Tooltip>
            <Tooltip title="适应视图">
              <Button size="small" icon={<AimOutlined />} onClick={onFitView} />
            </Tooltip>
            <Tooltip title="刷新">
              <Button size="small" icon={<ReloadOutlined />} onClick={onReload} />
            </Tooltip>
          </Space>
        </div>

        <Divider className="!my-2" />

        {/* 统计信息 */}
        <div>
          <Text type="secondary" className="text-xs block mb-1">图谱统计</Text>
          <div className="space-y-1">
            <div className="flex justify-between">
              <Text type="secondary" className="text-xs">节点</Text>
              <Badge count={stats?.totalNodes || 0} showZero size="small" />
            </div>
            <div className="flex justify-between">
              <Text type="secondary" className="text-xs">边</Text>
              <Badge count={stats?.totalEdges || 0} showZero size="small" />
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default GraphControls
