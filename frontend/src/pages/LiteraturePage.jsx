import React, { useState, useMemo, useEffect } from 'react'
import { Card, Input, Table, Tag, Button, Space, Typography, Modal, Form, Select, message, Tooltip, Row, Col, Empty, Upload, Spin, Tabs } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, CheckCircleOutlined, FileTextOutlined, UploadOutlined, FilePdfOutlined, PlusCircleOutlined, GlobalOutlined, ExperimentOutlined, RobotOutlined, DatabaseOutlined } from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'
import { literatureAPI } from '../services/api'
import { useLocation } from 'react-router-dom'

const { Title, Text } = Typography

const SOURCE_CONFIG = {
  arxiv: { icon: <GlobalOutlined />, color: '#e84a25', label: 'arXiv' },
  pubmed: { icon: <ExperimentOutlined />, color: '#3e84c8', label: 'PubMed' },
  semantic: { icon: <RobotOutlined />, color: '#5c7fdd', label: 'Semantic' },
  openalex: { icon: <DatabaseOutlined />, color: '#ff6b35', label: 'OpenAlex' },
}

const LiteraturePage = () => {
  const location = useLocation()
  const { literature, addLiterature, deleteLiterature, updateLiterature } = usePaperStore()
  const [searchText, setSearchText] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [form] = Form.useForm()

  // 多源搜索状态
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchLoadingMore, setSearchLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [activeTab, setActiveTab] = useState('library')

  const PAGE_SIZE = 10

  // 从 header 搜索跳转过来时自动触发搜索
  useEffect(() => {
    if (location.state?.searchQuery) {
      setSearchQuery(location.state.searchQuery)
      handleSearch(location.state.searchQuery)
      setActiveTab('search')
    }
  }, [location.state])

  // 多源学术搜索
  const handleSearch = async (query) => {
    const q = query || searchQuery
    if (!q.trim()) {
      message.warning('请输入搜索关键词')
      return
    }
    setSearchLoading(true)
    setSearchResults([])
    setSelectedRowKeys([])
    setCurrentPage(1)
    setHasMore(true)
    try {
      const result = await literatureAPI.search(q, { max_results: PAGE_SIZE })
      if (result.success && result.data) {
        const papers = result.data.map(item => ({
          id: item.paper_id || item.id || Date.now() + Math.random(),
          title: item.title || '',
          authors: Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || ''),
          year: item.year || '',
          journal: item.venue || item.journal || '',
          abstract: item.abstract || '',
          url: item.url || '',
          source: item.source || 'unknown',
          citations: item.citations || 0,
          doi: item.doi || '',
        }))
        setSearchResults(papers)
        setHasMore(result.data.length >= PAGE_SIZE)
        setActiveTab('search')
      } else {
        message.warning('未找到相关文献')
        setSearchResults([])
        setHasMore(false)
      }
    } catch (e) {
      message.error('搜索失败: ' + (e.message || '网络错误'))
      setSearchResults([])
      setHasMore(false)
    } finally {
      setSearchLoading(false)
    }
  }

  // 加载更多搜索结果
  const handleLoadMore = async () => {
    if (searchLoadingMore || !hasMore) return
    setSearchLoadingMore(true)
    try {
      const nextPage = currentPage + 1
      const result = await literatureAPI.search(searchQuery, {
        max_results: PAGE_SIZE,
        page: nextPage,
      })
      if (result.success && result.data) {
        const papers = result.data.map(item => ({
          id: item.paper_id || item.id || Date.now() + Math.random(),
          title: item.title || '',
          authors: Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || ''),
          year: item.year || '',
          journal: item.venue || item.journal || '',
          abstract: item.abstract || '',
          url: item.url || '',
          source: item.source || 'unknown',
          citations: item.citations || 0,
          doi: item.doi || '',
        }))
        setSearchResults(prev => [...prev, ...papers])
        setCurrentPage(nextPage)
        setHasMore(result.data.length >= PAGE_SIZE)
      } else {
        setHasMore(false)
      }
    } catch (e) {
      message.error('加载更多失败')
    } finally {
      setSearchLoadingMore(false)
    }
  }

  // 批量添加选中结果到文献库
  const handleBatchAddSelected = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要添加的文献')
      return
    }
    const selected = searchResults.filter(r => selectedRowKeys.includes(r.id))
    selected.forEach(item => {
      addLiterature({ ...item, status: 'pending' })
    })
    message.success(`已添加 ${selected.length} 篇文献到文献库`)
    setSelectedRowKeys([])
  }

  // 添加搜索结果到文献库
  const handleAddToLibrary = async (record) => {
    try {
      addLiterature({
        ...record,
        status: 'pending',
      })
      message.success('已添加到文献库')
    } catch (e) {
      message.error('添加失败')
    }
  }

  // 修复引用按钮
  const handleCiteLiterature = (id) => {
    updateLiterature(id, { status: 'cited' })
    message.success('文献已引用')
  }

  const handleDeleteLiterature = (id) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条文献吗？',
      okText: '删除',
      okType: 'danger',
      onOk() {
        deleteLiterature(id)
        message.success('文献已删除')
      }
    })
  }

  const handleAddLiterature = (values) => {
    const newItem = {
      ...values,
      id: Date.now(),
      citations: 0,
      status: 'pending',
    }
    addLiterature(newItem)
    message.success('文献添加成功')
    setIsAddModalOpen(false)
    form.resetFields()
  }

  // 上传文件处理
  const handleUpload = async (file) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await literatureAPI.uploadFile(formData)
      if (result.success && result.data) {
        addLiterature({
          ...result.data,
          id: result.data.id || Date.now(),
          status: 'pending',
        })
        message.success('文献上传成功！已自动提取元数据')
        setIsUploadModalOpen(false)
      } else {
        throw new Error(result.error || '上传失败')
      }
    } catch (error) {
      message.error('上传失败：' + (error.message || '未知错误'))
    } finally {
      setUploading(false)
    }
    return false
  }

  const beforeUpload = (file) => {
    const isPdf = file.type === 'application/pdf'
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    const isText = file.type.startsWith('text/')
    if (!isPdf && !isDocx && !isText) {
      message.error('只支持 PDF、Word 或文本文件！')
      return false
    }
    const isLt50M = file.size / 1024 / 1024 < 50
    if (!isLt50M) {
      message.error('文件大小不能超过 50MB！')
      return false
    }
    handleUpload(file)
    return false
  }

  const filteredLiterature = useMemo(() => {
    if (!searchText.trim()) return literature
    const lower = searchText.toLowerCase()
    return literature.filter(item =>
      item.title?.toLowerCase().includes(lower) ||
      item.authors?.toLowerCase().includes(lower) ||
      item.journal?.toLowerCase().includes(lower)
    )
  }, [literature, searchText])

  const totalCount = filteredLiterature.length
  const citedCount = filteredLiterature.filter(l => l.status === 'cited').length
  const pendingCount = filteredLiterature.filter(l => l.status === 'pending').length

  const libraryColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text) => <Text strong>{text}</Text>,
    },
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 180, ellipsis: true },
    { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
    { title: '期刊', dataIndex: 'journal', key: 'journal', width: 150, ellipsis: true },
    { title: '引用', dataIndex: 'citations', key: 'citations', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          cited: { color: 'green', text: '已引用' },
          pending: { color: 'orange', text: '待引用' },
          not_cited: { color: 'default', text: '未引用' },
        }
        const { color, text } = statusMap[status] || { color: 'default', text: status }
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="引用">
            <Button type="text" size="small" icon={<CheckCircleOutlined />} onClick={() => handleCiteLiterature(record.id)} />
          </Tooltip>
          <Tooltip title="删除">
            <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteLiterature(record.id)} />
          </Tooltip>
        </Space>
      ),
    },
  ]

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
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 180, ellipsis: true },
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
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: literature.some(l => l.id === record.id),
    }),
  }

  return (
    <div className="space-y-4">
      {/* 搜索栏 */}
      <Card size="small" className="!rounded-lg">
        <div className="flex justify-between items-center">
          <Space>
            <Input.Search
              placeholder="搜索学术文献 (arXiv, PubMed, Semantic Scholar...)"
              prefix={<SearchOutlined />}
              className="w-96"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onSearch={(value) => handleSearch(value)}
              enterButton="学术搜索"
              loading={searchLoading}
            />
          </Space>
          <Space>
            <Button type="primary" icon={<UploadOutlined />} onClick={() => setIsUploadModalOpen(true)}>
              上传文件
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => setIsAddModalOpen(true)}>
              手动添加
            </Button>
          </Space>
        </div>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card className="text-center !rounded-lg">
            <Title level={3} className="!mb-0">{totalCount}</Title>
            <Text type="secondary">总文献数</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center !rounded-lg">
            <Title level={3} className="!mb-0 !text-green-500">{citedCount}</Title>
            <Text type="secondary">已引用</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center !rounded-lg">
            <Title level={3} className="!mb-0 !text-orange-500">{pendingCount}</Title>
            <Text type="secondary">待引用</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center !rounded-lg">
            <Title level={3} className="!mb-0 !text-gray-400">{totalCount - citedCount - pendingCount}</Title>
            <Text type="secondary">未引用</Text>
          </Card>
        </Col>
      </Row>

      {/* 选项卡：搜索结果 / 我的文献库 */}
      <Card className="!rounded-lg">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'search',
              label: (
                <span>
                  <SearchOutlined /> 搜索结果
                  {searchResults.length > 0 && <Tag color="blue" className="ml-2">{searchResults.length}</Tag>}
                </span>
              ),
              children: searchLoading ? (
                <div className="text-center py-12"><Spin size="large" tip="正在搜索 arXiv, PubMed..." /></div>
              ) : searchResults.length === 0 ? (
                <Empty description="请输入关键词进行学术搜索" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                  <Text type="secondary">支持搜索 arXiv、PubMed 等多个学术数据库</Text>
                </Empty>
              ) : (
                <div>
                  {/* 批量操作栏 */}
                  {selectedRowKeys.length > 0 && (
                    <div className="flex justify-between items-center mb-3 p-2 bg-blue-50 rounded-lg">
                      <Text>已选择 <strong className="text-blue-600">{selectedRowKeys.length}</strong> 篇</Text>
                      <Button type="primary" icon={<PlusCircleOutlined />} onClick={handleBatchAddSelected}>
                        批量添加到文献库
                      </Button>
                    </div>
                  )}
                  {/* 搜索结果表格 - 带滚动加载 */}
                  <div
                    className="max-h-[600px] overflow-auto"
                    onScroll={(e) => {
                      const { scrollTop, scrollHeight, clientHeight } = e.target
                      if (scrollHeight - scrollTop - clientHeight < 100 && hasMore && !searchLoadingMore) {
                        handleLoadMore()
                      }
                    }}
                  >
                    <Table
                      dataSource={searchResults}
                      columns={searchResultColumns}
                      rowKey="id"
                      rowSelection={rowSelection}
                      pagination={false}
                      size="middle"
                      expandable={{
                        rowExpandable: (record) => !!record.abstract,
                        expandedRowRender: (record) => (
                          <div className="py-2 px-4">
                            <Text type="secondary" className="text-sm">{record.abstract}</Text>
                          </div>
                        ),
                      }}
                    />
                    {/* 加载更多提示 */}
                    {hasMore && (
                      <div className="text-center py-4">
                        {searchLoadingMore ? (
                          <Spin size="small" tip="加载更多..." />
                        ) : (
                          <Text type="secondary" className="text-sm">滚动加载更多</Text>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ),
            },
            {
              key: 'library',
              label: (
                <span>
                  <FileTextOutlined /> 我的文献库
                  {literature.length > 0 && <Tag color="green" className="ml-2">{literature.length}</Tag>}
                </span>
              ),
              children: (
                <>
                  <div className="mb-3">
                    <Input
                      placeholder="在文献库中筛选..."
                      prefix={<SearchOutlined />}
                      className="w-64"
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                    />
                  </div>
                  {filteredLiterature.length === 0 ? (
                    <Empty description="暂无文献，请搜索添加或上传文件" />
                  ) : (
                    <Table
                      dataSource={filteredLiterature}
                      columns={libraryColumns}
                      rowKey="id"
                      pagination={{ pageSize: 10 }}
                      size="middle"
                    />
                  )}
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* 添加文献弹窗 */}
      <Modal
        title="添加文献"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        footer={null}
        width={500}
      >
        <Form form={form} onFinish={handleAddLiterature} layout="vertical">
          <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入论文标题' }]}>
            <Input placeholder="请输入论文标题" />
          </Form.Item>
          <Form.Item label="作者" name="authors" rules={[{ required: true, message: '请输入作者' }]}>
            <Input placeholder="请输入作者，多个作者用逗号分隔" />
          </Form.Item>
          <Space className="w-full" size="large">
            <Form.Item label="年份" name="year" className="flex-1">
              <Input type="number" placeholder="年份" />
            </Form.Item>
            <Form.Item label="期刊" name="journal" className="flex-1">
              <Input placeholder="期刊名称" />
            </Form.Item>
          </Space>
          <Form.Item label="DOI" name="doi">
            <Input placeholder="论文DOI (可选)" />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="添加标签" />
          </Form.Item>
          <Form.Item className="!mb-0">
            <Space className="w-full justify-end">
              <Button onClick={() => setIsAddModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">添加</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 文件上传弹窗 */}
      <Modal
        title="上传文献文件"
        open={isUploadModalOpen}
        onCancel={() => setIsUploadModalOpen(false)}
        footer={null}
        width={500}
      >
        <div className="py-4">
          <div className="text-center">
            {uploading ? (
              <Spin tip="正在上传并提取元数据...">
                <div style={{ minHeight: 200 }} />
              </Spin>
            ) : (
              <>
                <Upload.Dragger
                  accept=".pdf,.doc,.docx,.txt"
                  showUploadList={false}
                  beforeUpload={beforeUpload}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <FilePdfOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                  <p className="ant-upload-hint">
                    支持 PDF、Word (.doc/.docx) 或文本文件<br />
                    系统将自动识别文献元数据（标题、作者、年份等）
                  </p>
                </Upload.Dragger>
                <div className="mt-4 text-xs text-gray-400">
                  <Text type="secondary">上传后AI将自动提取文件中的元数据信息</Text>
                </div>
              </>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default LiteraturePage
