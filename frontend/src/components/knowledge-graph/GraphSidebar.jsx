/**
 * 知识图谱侧边栏组件
 * 包含文献库列表、搜索和操作
 */
import React from 'react'
import {
  Card,
  Input,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Text,
  Tooltip,
  Modal,
  Form,
  Upload,
  message,
  Empty,
} from 'antd'
import {
  SearchOutlined,
  BuildOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  PlusCircleOutlined,
  UploadOutlined,
  FilePdfOutlined,
} from '@ant-design/icons'

const { Search } = Input

const literatureColumns = [
  {
    title: '标题',
    dataIndex: 'title',
    key: 'title',
    width: 200,
    ellipsis: true,
    render: (text) => <Text ellipsis>{text}</Text>,
  },
  { title: '作者', dataIndex: 'authors', key: 'authors', width: 120, ellipsis: true },
  { title: '年份', dataIndex: 'year', key: 'year', width: 60 },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 70,
    render: (status) => {
      const statusMap = {
        cited: { color: 'green', text: '已引用' },
        pending: { color: 'orange', text: '待引用' },
      }
      const { color, text } = statusMap[status] || { color: 'default', text: status }
      return <Tag color={color}>{text}</Tag>
    },
  },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (_, record) => (
      <Space size="small">
        <Tooltip title="添加到知识图谱">
          <Button
            type="text"
            size="small"
            icon={<BuildOutlined />}
            onClick={() => record.onBuildGraph?.(record.id)}
          />
        </Tooltip>
        <Tooltip title="引用">
          <Button
            type="text"
            size="small"
            icon={<CheckCircleOutlined />}
            onClick={() => record.onCite?.(record.id)}
          />
        </Tooltip>
        <Tooltip title="删除">
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => record.onDelete?.(record.id)}
          />
        </Tooltip>
      </Space>
    ),
  },
]

const GraphSidebar = ({
  literature,
  searchText,
  onSearchChange,
  onAddLiterature,
  onDeleteLiterature,
  onCiteLiterature,
  onBuildFromLiterature,
  onUpload,
  filteredLiterature,
}) => {
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = React.useState(false)
  const [form] = Form.useForm()

  const handleAddLiterature = (values) => {
    onAddLiterature?.({
      ...values,
      id: Date.now(),
      citations: 0,
      status: 'pending',
    })
    message.success('文献添加成功')
    setIsAddModalOpen(false)
    form.resetFields()
  }

  const handleUpload = (file) => {
    onUpload?.(file)
    return false
  }

  const beforeUpload = (file) => {
    const isPdf = file.type === 'application/pdf'
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    if (!isPdf && !isDocx) {
      message.error('只支持 PDF、Word 文件！')
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

  // 增强columns，添加回调
  const columnsWithActions = literatureColumns.map(col => {
    if (col.key === 'action') {
      return {
        ...col,
        render: (_, record) => (
          <Space size="small">
            <Tooltip title="添加到知识图谱">
              <Button
                type="text"
                size="small"
                icon={<BuildOutlined />}
                onClick={() => onBuildFromLiterature?.(record.id)}
              />
            </Tooltip>
            <Tooltip title="引用">
              <Button
                type="text"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => onCiteLiterature?.(record.id)}
              />
            </Tooltip>
            <Tooltip title="删除">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => {
                  Modal.confirm({
                    title: '确认删除',
                    content: '确定要删除这条文献吗？',
                    okText: '删除',
                    okType: 'danger',
                    onOk() {
                      onDeleteLiterature?.(record.id)
                      message.success('文献已删除')
                    }
                  })
                }}
              />
            </Tooltip>
          </Space>
        ),
      }
    }
    return col
  })

  return (
    <Card
      size="small"
      title="文献库"
      extra={
        <Space>
          <Button
            size="small"
            type="text"
            icon={<PlusCircleOutlined />}
            onClick={() => setIsAddModalOpen(true)}
          />
          <Upload
            beforeUpload={beforeUpload}
            showUploadList={false}
          >
            <Button size="small" type="text" icon={<UploadOutlined />} />
          </Upload>
        </Space>
      }
    >
      <div className="space-y-3">
        {/* 搜索 */}
        <Input
          placeholder="搜索文献..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          allowClear
          size="small"
        />

        {/* 文献列表 */}
        <Table
          dataSource={filteredLiterature}
          columns={columnsWithActions}
          rowKey="id"
          size="small"
          pagination={{
            pageSize: 5,
            size: 'small',
          }}
          scroll={{ y: 300 }}
          locale={{
            emptyText: <Empty description="暂无文献" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          }}
        />
      </div>

      {/* 添加文献弹窗 */}
      <Modal
        title="添加文献"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddLiterature}
        >
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入论文标题" />
          </Form.Item>
          <Form.Item name="authors" label="作者">
            <Input placeholder="请输入作者，多个作者用逗号分隔" />
          </Form.Item>
          <Form.Item name="year" label="年份">
            <Input type="number" placeholder="请输入年份" />
          </Form.Item>
          <Form.Item name="journal" label="期刊/会议">
            <Input placeholder="请输入期刊或会议名称" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

export default GraphSidebar
