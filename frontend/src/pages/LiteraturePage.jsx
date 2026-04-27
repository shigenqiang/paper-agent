import React, { useState } from 'react'
import { Card, Input, Table, Tag, Button, Space, Typography, Modal, Form, Select, message } from 'antd'
import { PlusOutlined, SearchOutlined, DownloadOutlined, SyncOutlined, DeleteOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

const LiteraturePage = () => {
  const [searchText, setSearchText] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [form] = Form.useForm()

  const literatureData = [
    {
      id: 1,
      title: 'Deep Learning in Medical Imaging: A Comprehensive Review',
      authors: 'Smith, J., Johnson, A., Williams, B.',
      year: 2023,
      journal: 'Journal of AI in Medicine',
      citations: 156,
      status: 'cited',
      tags: ['深度学习', '医学影像', '综述'],
    },
    {
      id: 2,
      title: 'CNN-based Methods for Image Classification',
      authors: 'Zhang, L., Chen, M.',
      year: 2022,
      journal: 'IEEE Transactions on Pattern Analysis',
      citations: 89,
      status: 'cited',
      tags: ['CNN', '图像分类'],
    },
    {
      id: 3,
      title: 'A Survey on Transformer Models',
      authors: 'Wang, R., Li, H.',
      year: 2021,
      journal: 'Nature Machine Intelligence',
      citations: 234,
      status: 'pending',
      tags: ['Transformer', '综述'],
    },
    {
      id: 4,
      title: 'Reinforcement Learning for Autonomous Driving',
      authors: 'Liu, Y., Zhou, Q.',
      year: 2023,
      journal: 'ICLR 2023',
      citations: 45,
      status: 'not_cited',
      tags: ['强化学习', '自动驾驶'],
    },
  ]

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
      sorter: (a, b) => a.citations - b.citations,
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
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags) => (
        <>
          {tags.map((tag, index) => (
            <Tag key={index} className="mr-1">{tag}</Tag>
          ))}
        </>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small">查看</Button>
          <Button type="link" size="small" danger onClick={() => message.info('删除功能')}>
            <DeleteOutlined />
          </Button>
        </Space>
      ),
    },
  ]

  const handleAddLiterature = (values) => {
    console.log('Add literature:', values)
    message.success('文献添加成功')
    setIsAddModalOpen(false)
    form.resetFields()
  }

  return (
    <div className="space-y-4">
      {/* 顶部操作栏 */}
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
          <Button icon={<SyncOutlined />}>同步Zotero</Button>
          <Button icon={<DownloadOutlined />}>导出文献</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsAddModalOpen(true)}>
            添加文献
          </Button>
        </Space>
      </div>

      {/* 文献统计 */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="text-center">
          <Title level={3} className="!mb-0">12</Title>
          <Text type="secondary">总文献数</Text>
        </Card>
        <Card className="text-center">
          <Title level={3} className="!mb-0 text-green">5</Title>
          <Text type="secondary">已引用</Text>
        </Card>
        <Card className="text-center">
          <Title level={3} className="!mb-0 text-orange">4</Title>
          <Text type="secondary">待引用</Text>
        </Card>
        <Card className="text-center">
          <Title level={3} className="!mb-0 text-gray">3</Title>
          <Text type="secondary">未引用</Text>
        </Card>
      </div>

      {/* 文献列表 */}
      <Card>
        <Table
          dataSource={literatureData}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          size="middle"
        />
      </Card>

      {/* 添加文献弹窗 */}
      <Modal
        title="添加文献"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleAddLiterature} layout="vertical">
          <Form.Item label="标题" name="title" rules={[{ required: true }]}>
            <Input placeholder="请输入论文标题" />
          </Form.Item>

          <Form.Item label="作者" name="authors" rules={[{ required: true }]}>
            <Input placeholder="请输入作者，多个作者用逗号分隔" />
          </Form.Item>

          <Space className="w-full" size="large">
            <Form.Item label="年份" name="year" rules={[{ required: true }]} className="flex-1">
              <Input type="number" placeholder="年份" />
            </Form.Item>
            <Form.Item label="期刊" name="journal" className="flex-1">
              <Input placeholder="期刊名称" />
            </Form.Item>
          </Space>

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
    </div>
  )
}

export default LiteraturePage