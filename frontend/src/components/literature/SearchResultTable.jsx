/**
 * SearchResultTable - 搜索结果表格组件
 */
import React from 'react'
import { Table, Button, Space, Typography, Tag, Empty, Spin } from 'antd'
import { PlusCircleOutlined } from '@ant-design/icons'
import { SOURCE_CONFIG } from '../../constants/source'

const { Text } = Typography

/**
 * SearchResultTable组件
 * @param {Array} searchResults - 搜索结果列表
 * @param {Array} selectedRowKeys - 选中的行keys
 * @param {function} onSelectionChange - 选择变化回调
 * @param {function} onBatchAdd - 批量添加回调
 * @param {function} onToggleExpand - 展开/收起作者回调
 * @param {boolean} expandedAuthors - 已展开的作者记录ID数组
 * @param {boolean} hasMore - 是否有更多
 * @param {number} totalCount - 总数
 */
export function SearchResultTable({
  searchResults,
  selectedRowKeys,
  onSelectionChange,
  onBatchAdd,
  onToggleExpand,
  expandedAuthors = [],
  hasMore = false,
  loading = false,
}) {
  const searchResultColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text, record) => (
        <div>
          <Text strong>{text}</Text>
          {record.url && (
            <div><a href={record.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500">{record.url.substring(0, 60)}...</a></div>
          )}
        </div>
      ),
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      width: 220,
      ellipsis: true,
      render: (authors, record) => {
        const authorList = authors ? authors.split(',').map(a => a.trim()) : []
        const isLong = authorList.length > 3
        const displayAuthors = expandedAuthors.includes(record.id)
          ? authorList
          : authorList.slice(0, 3)
        return (
          <div>
            <span>{displayAuthors.join(', ')}{isLong && !expandedAuthors.includes(record.id) ? '...' : ''}</span>
            {isLong && (
              <a
                className="ml-1 text-blue-500"
                onClick={(e) => {
                  e.stopPropagation()
                  onToggleExpand(record.id)
                }}
              >
                {expandedAuthors.includes(record.id) ? '收起' : '展开'}
              </a>
            )}
          </div>
        )
      }
    },
    { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source) => {
        const config = SOURCE_CONFIG[source] || { label: source, color: '#999' }
        return <Tag color={config.color}>{config.label}</Tag>
      },
    },
    { title: '引用数', dataIndex: 'citations', key: 'citations', width: 80 },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: onSelectionChange,
  }

  if (loading) {
    return (
      <div className="text-center py-16">
        <Spin size="large" />
      </div>
    )
  }

  if (searchResults.length === 0) {
    return (
      <Empty
        description={
          <Space direction="vertical">
            <Text>请输入关键词进行学术搜索</Text>
            <Text type="secondary" className="text-sm">支持搜索 arXiv、PubMed、Semantic Scholar、OpenAlex 等多个学术数据库</Text>
          </Space>
        }
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    )
  }

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <Text type="secondary">
          找到 <Text strong>{searchResults.length}</Text> 篇相关文献
          {hasMore && `+更多`}
        </Text>
        {selectedRowKeys.length > 0 && (
          <Button type="primary" icon={<PlusCircleOutlined />} onClick={onBatchAdd}>
            添加到文献库 ({selectedRowKeys.length})
          </Button>
        )}
      </div>

      <Table
        dataSource={searchResults}
        columns={searchResultColumns}
        rowKey="id"
        rowSelection={rowSelection}
        pagination={{ pageSize: 10 }}
        size="middle"
        expandable={{
          rowExpandable: (record) => !!record.abstract,
          expandedRowRender: (record) => (
            <div className="py-2">
              <Text type="secondary" className="text-sm">{record.abstract}</Text>
            </div>
          ),
        }}
      />
    </>
  )
}

export default SearchResultTable