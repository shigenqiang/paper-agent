/**
 * SearchBox - 学术文献搜索框组件
 */
import React from 'react'
import { Input, Button, Space, Typography, Tag } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { SOURCE_CONFIG_LIST } from '../../constants/source'

const { Text } = Typography

/**
 * SearchBox组件
 * @param {string} searchQuery - 搜索关键词
 * @param {function} onSearchQueryChange - 关键词变化回调
 * @param {function} onSearch - 执行搜索回调
 * @param {string[]} sources - 启用的数据源
 * @param {function} onToggleSource - 切换数据源回调
 * @param {boolean} loading - 加载状态
 */
export function SearchBox({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  sources,
  onToggleSource,
  loading = false,
}) {
  return (
    <div className="text-center py-8">
      <Input.Search
        placeholder="输入关键词搜索学术文献，如: machine learning, deep learning..."
        prefix={<SearchOutlined />}
        size="large"
        value={searchQuery}
        onChange={(e) => onSearchQueryChange(e.target.value)}
        onSearch={(value) => onSearch(value)}
        enterButton={
          <Button type="primary" size="large" loading={loading}>
            搜索
          </Button>
        }
        loading={loading}
        className="!text-lg"
      />
      <div className="flex justify-center gap-2 flex-wrap mt-4">
        {SOURCE_CONFIG_LIST.map(source => (
          <Tag
            key={source.key}
            color={sources.includes(source.key) ? source.color : 'default'}
            className="!px-3 !py-1 !text-sm cursor-pointer"
            onClick={() => onToggleSource(source.key)}
          >
            {source.label}
          </Tag>
        ))}
      </div>
    </div>
  )
}

export default SearchBox