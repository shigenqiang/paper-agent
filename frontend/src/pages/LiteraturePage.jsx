import React, { useState, useMemo } from 'react'
import { Card, Input, Table, Tag, Button, Space, Typography, Modal, Form, Select, message, Tooltip, Row, Col, Empty, Upload, Spin } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, CheckCircleOutlined, FileTextOutlined, UploadOutlined, FilePdfOutlined } from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'
import { literatureAPI } from '../services/api'

const { Title, Text } = Typography

const LiteraturePage = () => {
  const { literature, addLiterature, deleteLiterature } = usePaperStore()
  const [searchText, setSearchText] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [form] = Form.useForm()

  const displayLiterature = literature

  const filteredLiterature = useMemo(() => {
    if (!searchText.trim()) return displayLiterature
    const lower = searchText.toLowerCase()
    return displayLiterature.filter(item =>
      item.title?.toLowerCase().includes(lower) ||
      item.authors?.toLowerCase().includes(lower) ||
      item.journal?.toLowerCase().includes(lower)
    )
  }, [displayLiterature, searchText])

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

  const handleCiteLiterature = (id) => {
    message.success('文献已引用')
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

      const response = await fetch('/api/literature/upload', {
        method: 'POST',
        headers: {
          'X-API-Key': localStorage.getItem('api_key') || 'dev-api-key'
        },
        body: formData
      })

      const result = await response.json()

      if (result.success) {
        addLiterature(result.data)
        message.success('文献上传成功！已自动提取元数据')
        setIsUploadModalOpen(false)
      } else {
        throw new Error(result.error)
      }
    } catch (error) {
      message.error('上传失败：' + error.message)
    } finally {
      setUploading(false)
    }
    return false // 阻止默认上传行为
  }

  // 上传前的验证
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

  const totalCount = filteredLiterature.length
  const citedCount = filteredLiterature.filter(l => l.status === 'cited').length
  const pendingCount = filteredLiterature.filter(l => l.status === 'pending').length

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      width: 180,
    },
    {
      title: '年份',
      dataIndex: 'year',
      key: 'year',
      width: 80,
    },
    {
      title: '期刊',
      dataIndex: 'journal',
      key: 'journal',
      width: 150,
      ellipsis: true,
    },
    {
      title: '引用',
      dataIndex: 'citations',
      key: 'citations',
      width: 80,
    },
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

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Space>
          <Input
            placeholder="搜索文献..."
            prefix={<SearchOutlined />}
            className="w-64"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            placeholder="筛选状态"
            className="w-32"
            allowClear
            options={[
              { label: '已引用', value: 'cited' },
              { label: '待引用', value: 'pending' },
              { label: '未引用', value: 'not_cited' },
            ]}
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

      <Row gutter={16}>
        <Col span={6}>
          <Card className="text-center">
            <Title level={3} className="!mb-0">{totalCount}</Title>
            <Text type="secondary">总文献数</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Title level={3} className="!mb-0 text-green">{citedCount}</Title>
            <Text type="secondary">已引用</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Title level={3} className="!mb-0 text-orange">{pendingCount}</Title>
            <Text type="secondary">待引用</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Title level={3} className="!mb-0 text-gray">{totalCount - citedCount - pendingCount}</Title>
            <Text type="secondary">未引用</Text>
          </Card>
        </Col>
      </Row>

      <Card>
        {filteredLiterature.length === 0 ? (
          <div className="text-center py-8">
            <Empty description="暂无文献" />
          </div>
        ) : (
          <Table
            dataSource={filteredLiterature}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            size="middle"
          />
        )}
      </Card>

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
