import React from 'react'
import { Card, Button, Space, Typography, Progress, List, Tag } from 'antd'
import { PlusOutlined, PlayCircleOutlined, FileTextOutlined, ThunderboltOutlined, BookOutlined, EditOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

const HomePage = () => {
  const recentProjects = [
    { id: 1, title: '深度学习在医学影像中的应用研究', progress: 65, updatedAt: '2小时前' },
    { id: 2, title: '基于Transformer的文本摘要方法', progress: 40, updatedAt: '昨天' },
    { id: 3, title: '强化学习在自动驾驶决策中的应用', progress: 20, updatedAt: '3天前' },
  ]

  return (
    <div className="space-y-6">
      {/* 欢迎区域 */}
      <Card className="bg-gradient-to-r from-primary to-blue-400 text-white">
        <div className="flex justify-between items-center">
          <div>
            <Title level={3} className="!text-white !mb-2">欢迎使用 Paper Agent</Title>
            <Text className="text-white/90">
              AI驱动的学术论文写作助手，让您的研究更高效
            </Text>
          </div>
          <Space>
            <Button type="default" icon={<PlusOutlined />} className="!bg-white/20 !border-white/30 !text-white">
              新建论文
            </Button>
            <Button type="default" icon={<ThunderboltOutlined />} className="!bg-white/20 !border-white/30 !text-white">
              快速开始
            </Button>
          </Space>
        </div>
      </Card>

      {/* 快捷操作 */}
      <div className="grid grid-cols-4 gap-4">
        <Card hoverable className="text-center">
          <FileTextOutlined className="text-4xl text-primary mb-2" />
          <div>选题分析</div>
        </Card>
        <Card hoverable className="text-center">
          <BookOutlined className="text-4xl text-primary mb-2" />
          <div>文献搜索</div>
        </Card>
        <Card hoverable className="text-center">
          <EditOutlined className="text-4xl text-primary mb-2" />
          <div>大纲生成</div>
        </Card>
        <Card hoverable className="text-center">
          <PlayCircleOutlined className="text-4xl text-primary mb-2" />
          <div>AI写作</div>
        </Card>
      </div>

      {/* 最近项目 */}
      <Card title="最近项目">
        <List
          dataSource={recentProjects}
          renderItem={(item) => (
            <List.Item
              className="cursor-pointer hover:bg-gray-50 -mx-4 px-4"
              onClick={() => {}}
            >
              <List.Item.Meta
                title={item.title}
                description={`更新于 ${item.updatedAt}`}
              />
              <Progress percent={item.progress} size="small" className="w-32" />
              <Tag color="blue" className="ml-4">论文</Tag>
            </List.Item>
          )}
        />
      </Card>

      {/* 写作流程进度 */}
      <Card title="论文完成进度">
        <div className="flex justify-between items-center">
          <Text>整体进度</Text>
          <Text type="secondary">35%</Text>
        </div>
        <Progress percent={35} className="mt-2" />

        <div className="grid grid-cols-6 gap-4 mt-6">
          {[
            { label: '选题', percent: 80 },
            { label: '文献', percent: 45 },
            { label: '大纲', percent: 30 },
            { label: '写作', percent: 10 },
            { label: '修改', percent: 0 },
            { label: '导出', percent: 0 },
          ].map((item, index) => (
            <div key={index} className="text-center">
              <Progress
                percent={item.percent}
                type="circle"
                size={50}
                format={() => item.label}
              />
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default HomePage