import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Space, Button, Statistic, Progress, List, Tag, Empty, Spin, Avatar, Badge, Divider, Tooltip, message } from 'antd'
import {
  PlusOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  EditOutlined,
  SearchOutlined,
  BulbOutlined,
  RobotOutlined,
  BookOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  RightOutlined,
  ArrowUpOutlined,
  RiseOutlined,
  GlobalOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  BgColorsOutlined,
  SunOutlined,
  StarOutlined,
  TeamOutlined,
  FrownOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { paperAPI } from '../services/api'

const { Title, Text, Paragraph } = Typography

// 快捷入口配置
const QUICK_ENTRIES = [
  {
    key: 'new-paper',
    icon: <PlusOutlined />,
    label: '新建论文',
    description: '开始新的写作',
    color: '#1890ff',
    bgGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    path: '/writing',
  },
  {
    key: 'search',
    icon: <SearchOutlined />,
    label: '文献搜索',
    description: '多源学术检索',
    color: '#52c41a',
    bgGradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    path: '/literature',
  },
  {
    key: 'digest',
    icon: <BulbOutlined />,
    label: '学术资讯',
    description: '日报/周报/月报',
    color: '#fa8c16',
    bgGradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    path: '/reports',
  },
  {
    key: 'ai',
    icon: <RobotOutlined />,
    label: 'AI助手',
    description: '智能问答',
    color: '#722ed1',
    bgGradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    path: '/ai-assistant',
  },
]

// 数据源统计
const SOURCE_STATS = [
  { icon: <GlobalOutlined />, label: 'arXiv', count: 0, color: '#e84a25', description: '预印本论文' },
  { icon: <ExperimentOutlined />, label: 'PubMed', count: 0, color: '#3e84c8', description: '医学文献' },
  { icon: <RobotOutlined />, label: 'Semantic', count: 0, color: '#5c7fdd', description: 'AI学术搜索' },
  { icon: <DatabaseOutlined />, label: 'OpenAlex', count: 0, color: '#ff6b35', description: '开放学术' },
]

// 系统状态
const SYSTEM_STATUS = [
  { key: 'api', label: 'API状态', icon: <ThunderboltOutlined />, value: '正常', color: '#52c41a' },
  { key: 'sync', label: '数据同步', icon: <SyncOutlined />, value: '已同步', color: '#52c41a' },
  { key: 'ai', label: 'AI模型', icon: <RobotOutlined />, value: 'GPT-4', color: '#1890ff' },
]

// 最近活动
const RECENT_ACTIVITIES = [
  { id: 1, type: 'paper', action: '创建了论文', time: '2小时前', icon: <FileTextOutlined />, color: '#1890ff' },
  { id: 2, type: 'search', action: '搜索了文献', time: '3小时前', icon: <SearchOutlined />, color: '#52c41a' },
  { id: 3, type: 'ai', action: '使用了AI助手', time: '5小时前', icon: <RobotOutlined />, color: '#722ed1' },
  { id: 4, type: 'digest', action: '查看了学术资讯', time: '1天前', icon: <BulbOutlined />, color: '#fa8c16' },
]

const HomePage = () => {
  const navigate = useNavigate()
  const [papers, setPapers] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalPapers: 0,
    completedPapers: 0,
    totalWords: 0,
    citations: 0,
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await paperAPI.getPapers()
      const data = response.data || []

      setPapers(data.slice(0, 5)) // 只取最新的5篇

      // 计算统计
      const total = data.length
      const completed = data.filter(p => p.status === 'completed').length
      const totalWords = data.reduce((sum, p) => sum + (p.content?.length || 0), 0)

      setStats({
        totalPapers: total,
        completedPapers: completed,
        totalWords,
        citations: Math.floor(Math.random() * 50) + 10, // 模拟数据
      })
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePaper = async () => {
    try {
      const response = await paperAPI.createPaper({
        title: '新论文-' + new Date().toLocaleDateString(),
        topic: '待定'
      })
      const paperId = response?.data?.id || response?.id
      navigate('/writing', { state: { paperId } })
    } catch (error) {
      console.error('创建论文失败:', error)
      message.error('创建论文失败')
    }
  }

  // 计算论文总进度
  const overallProgress = stats.totalPapers > 0
    ? Math.round(papers.reduce((sum, p) => {
        if (p.status === 'completed') return sum + 100
        if (p.status === 'draft') return sum + 30
        return sum
      }, 0) / stats.totalPapers)
    : 0

  // 计算完成率
  const completionRate = stats.totalPapers > 0
    ? Math.round((stats.completedPapers / stats.totalPapers) * 100)
    : 0

  return (
    <div className="space-y-5">
      {/* 欢迎横幅 - 优化渐变和视觉层次 */}
      <Card className="!bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-700 text-white border-0 !rounded-2xl shadow-lg" styles={{ body: { padding: '28px 32px' }}}>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur">
              <StarOutlined className="text-3xl text-white" />
            </div>
            <div>
              <Title level={2} className="!text-white !mb-1 flex items-center gap-2">
                你好，学术研究者
              </Title>
              <Text className="text-white/90 text-base">
                今天是学习的好日子，让AI助你一臂之力
              </Text>
            </div>
          </div>
          <Space size="middle" className="mr-4">
            <Button
              type="primary"
              size="large"
              icon={<PlusOutlined />}
              className="!bg-white !text-indigo-600 !border-0 !font-semibold !shadow-lg"
              onClick={handleCreatePaper}
            >
              新建论文
            </Button>
            <Button
              size="large"
              icon={<PlayCircleOutlined />}
              className="!bg-white/20 !text-white !border-white/40 hover:!bg-white/30 !font-semibold"
              onClick={() => navigate('/features')}
            >
              快速开始
            </Button>
          </Space>
        </div>
      </Card>

      {/* 快捷入口 - 卡片式设计 */}
      <Row gutter={[20, 20]}>
        {QUICK_ENTRIES.map((entry, index) => (
          <Col xs={12} sm={12} md={6} key={entry.key}>
            <Card
              hoverable
              className="cursor-pointer h-full transition-all duration-300 hover:shadow-xl hover:-translate-y-1 !rounded-2xl overflow-hidden group"
              onClick={() => navigate(entry.path)}
              styles={{ body: { padding: 0 }}}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div
                className="h-28 flex items-center justify-center relative overflow-hidden"
                style={{ background: entry.bgGradient }}
              >
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-all" />
                <div className="text-white text-5xl transform group-hover:scale-110 transition-transform duration-300">{entry.icon}</div>
              </div>
              <div className="px-5 py-4">
                <Text strong className="text-base block text-gray-800">{entry.label}</Text>
                <Text type="secondary" className="text-sm mt-1">{entry.description}</Text>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 统计和进度 */}
      <Row gutter={[20, 20]} className="mt-5">
        {/* 论文统计 */}
        <Col xs={24} lg={16}>
          <Card
            className="!rounded-2xl shadow-sm"
            title={
              <Space className="!text-base">
                <FileTextOutlined className="!text-blue-500" />
                <span className="font-semibold">论文概览</span>
              </Space>
            }
            extra={<Button type="link" onClick={() => navigate('/writing')} className="!text-blue-500">查看全部 <RightOutlined /></Button>}
          >
            <Row gutter={24}>
              <Col span={6}>
                <Statistic
                  title={<Text type="secondary" className="text-xs">论文总数</Text>}
                  value={stats.totalPapers}
                  prefix={<FileTextOutlined className="text-blue-500 text-lg" />}
                  valueStyle={{ fontSize: '32px', color: '#1890ff', fontWeight: 600 }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<Text type="secondary" className="text-xs">已完成</Text>}
                  value={stats.completedPapers}
                  valueStyle={{ fontSize: '32px', color: '#52c41a', fontWeight: 600 }}
                  prefix={<CheckCircleOutlined className="text-green-500" />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<Text type="secondary" className="text-xs">进行中</Text>}
                  value={stats.totalPapers - stats.completedPapers}
                  valueStyle={{ fontSize: '32px', color: '#1890ff', fontWeight: 600 }}
                  prefix={<EditOutlined className="text-blue-400" />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title={<Text type="secondary" className="text-xs">总字数</Text>}
                  value={stats.totalWords}
                  suffix="字"
                  valueStyle={{ fontSize: '32px', color: '#722ed1', fontWeight: 600 }}
                  prefix={<FileTextOutlined className="text-purple-500" />}
                />
              </Col>
            </Row>

            <Divider className="my-4" />

            {/* 论文列表 */}
            {papers.length === 0 ? (
              <Empty description="暂无论文" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreatePaper}>
                  创建第一篇论文
                </Button>
              </Empty>
            ) : (
              <List
                size="small"
                dataSource={papers}
                renderItem={(paper, index) => (
                  <List.Item
                    className="cursor-pointer hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 -mx-3 px-4 py-4 rounded-xl transition-all border-b border-gray-50"
                    onClick={() => navigate('/writing', { state: { paperId: paper.id } })}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size={44}
                          style={{
                            background: index === 0 ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : index === 1 ? 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' : index === 2 ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                          }}
                          icon={<FileTextOutlined />}
                        />
                      }
                      title={<Text strong className="text-sm">{paper.title || '无标题论文'}</Text>}
                      description={
                        <Space className="mt-1">
                          <Tag color={paper.status === 'completed' ? 'success' : 'processing'} className="!m-0 text-xs">
                            {paper.status === 'completed' ? '已完成' : '进行中'}
                          </Tag>
                          <Text type="secondary" className="text-xs">
                            更新于 {paper.updated_at ? new Date(paper.updated_at).toLocaleDateString() : '未知'}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        {/* 右侧面板 */}
        <Col xs={24} lg={8}>
          <Space direction="vertical" className="w-full" size={16}>
            {/* 整体进度 */}
            <Card size="small" className="!rounded-2xl shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <Space>
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <RiseOutlined className="text-blue-500" />
                  </div>
                  <Text strong className="text-sm">整体进度</Text>
                </Space>
                <Text type="secondary" className="text-sm">{completionRate}%</Text>
              </div>
              <Progress percent={completionRate} showInfo={false} strokeColor="#1890ff" size="small" />
              <div className="flex justify-between mt-3 text-xs text-gray-400">
                <span>已完成 {stats.completedPapers} 篇</span>
                <span>总计 {stats.totalPapers} 篇</span>
              </div>
            </Card>

            {/* 最近活动 */}
            <Card size="small" className="!rounded-2xl shadow-sm" title={
              <Space className="!text-sm">
                <ClockCircleOutlined className="!text-orange-500" />
                <span className="font-semibold">最近活动</span>
              </Space>
            }>
              <List
                size="small"
                dataSource={RECENT_ACTIVITIES}
                renderItem={(item) => (
                  <List.Item className="!py-3">
                    <Space className="w-full">
                      <Avatar size="small" style={{ backgroundColor: item.color }} icon={item.icon} />
                      <div className="flex-1">
                        <Text className="text-sm">{item.action}</Text>
                        <div className="text-xs text-gray-400">{item.time}</div>
                      </div>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>

            {/* 数据来源 */}
            <Card size="small" className="!rounded-2xl shadow-sm" title={
              <Space className="!text-sm">
                <GlobalOutlined className="!text-indigo-500" />
                <span className="font-semibold">数据来源</span>
              </Space>
            }>
              <Row gutter={[12, 12]}>
                {SOURCE_STATS.map(source => (
                  <Col span={12} key={source.label}>
                    <div className="flex items-center gap-2 p-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl">
                      <span style={{ color: source.color, fontSize: '20px' }}>{source.icon}</span>
                      <div>
                        <Text className="text-sm font-medium block">{source.label}</Text>
                        <Text type="secondary" className="text-xs">{source.description}</Text>
                      </div>
                    </div>
                  </Col>
                ))}
              </Row>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  )
}

export default HomePage
