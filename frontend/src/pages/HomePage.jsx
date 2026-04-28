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
      await paperAPI.createPaper({
        title: '新论文-' + new Date().toLocaleDateString(),
        topic: '待定'
      })
      navigate('/writing')
    } catch (error) {
      console.error('创建论文失败:', error)
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
    <div className="space-y-4">
      {/* 欢迎横幅 */}
      <Card className="!bg-gradient-to-r from-blue-500 via-blue-600 to-purple-600 text-white border-0 !rounded-xl">
        <div className="flex justify-between items-center">
          <div>
            <Title level={3} className="!text-white !mb-1 flex items-center gap-2">
              <StarOutlined /> 你好，学术研究者
            </Title>
            <Text className="text-white/90 text-sm">
              今天是学习的好日子，让AI助你一臂之力完成论文
            </Text>
          </div>
          <Space>
            <Button
              type="primary"
              size="large"
              icon={<PlusOutlined />}
              className="!bg-white !text-blue-600 !border-0"
              onClick={handleCreatePaper}
            >
              新建论文
            </Button>
          </Space>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12"><Spin size="large" tip="加载中..." /></div>
      ) : (
        <>
          {/* 快捷入口 */}
          <Row gutter={16}>
            {QUICK_ENTRIES.map(entry => (
              <Col xs={12} sm={12} md={6} key={entry.key}>
                <Card
                  hoverable
                  className="cursor-pointer h-full transition-all hover:shadow-lg !rounded-xl overflow-hidden"
                  onClick={() => navigate(entry.path)}
                  bodyStyle={{ padding: 0 }}
                >
                  <div
                    className="h-24 flex items-center justify-center"
                    style={{ background: entry.bgGradient }}
                  >
                    <div className="text-white text-4xl">{entry.icon}</div>
                  </div>
                  <div className="px-4 py-3">
                    <Text strong className="text-base block">{entry.label}</Text>
                    <Text type="secondary" className="text-xs">{entry.description}</Text>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>

          {/* 统计和进度 */}
          <Row gutter={16}>
            {/* 论文统计 */}
            <Col xs={24} md={16}>
              <Card className="!rounded-xl" title={<Space><FileTextOutlined /><span>论文概览</span></Space>} extra={<Button type="link" onClick={() => navigate('/writing')}>查看全部 <RightOutlined /></Button>}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title={<Text type="secondary" className="text-xs">论文总数</Text>}
                      value={stats.totalPapers}
                      prefix={<FileTextOutlined className="text-blue-500" />}
                      valueStyle={{ fontSize: '28px', color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<Text type="secondary" className="text-xs">已完成</Text>}
                      value={stats.completedPapers}
                      valueStyle={{ fontSize: '28px', color: '#52c41a' }}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<Text type="secondary" className="text-xs">进行中</Text>}
                      value={stats.totalPapers - stats.completedPapers}
                      valueStyle={{ fontSize: '28px', color: '#1890ff' }}
                      prefix={<EditOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={<Text type="secondary" className="text-xs">总字数</Text>}
                      value={stats.totalWords}
                      suffix="字"
                      valueStyle={{ fontSize: '28px', color: '#722ed1' }}
                      prefix={<EditOutlined />}
                    />
                  </Col>
                </Row>

                <Divider />

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
                        className="cursor-pointer hover:bg-gray-50 -mx-2 px-3 py-3 rounded-lg transition-all"
                        onClick={() => navigate('/writing')}
                      >
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              size={40}
                              style={{
                                background: index === 0 ? '#1890ff' : index === 1 ? '#52c41a' : index === 2 ? '#fa8c16' : '#722ed1',
                              }}
                              icon={<FileTextOutlined />}
                            />
                          }
                          title={<Text strong>{paper.title || '无标题论文'}</Text>}
                          description={
                            <Space>
                              <Tag color={paper.status === 'completed' ? 'success' : 'processing'} className="!m-0">
                                {paper.status === 'completed' ? '已完成' : '进行中'}
                              </Tag>
                              <Text type="secondary" className="text-xs">
                                更新于 {paper.updated_at ? new Date(paper.updated_at).toLocaleDateString() : '未知'}
                              </Text>
                            </Space>
                          }
                        />
                        <Progress
                          percent={paper.status === 'completed' ? 100 : 30}
                          size="small"
                          className="w-24"
                          strokeColor={paper.status === 'completed' ? '#52c41a' : '#1890ff'}
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </Col>

            {/* 右侧面板 */}
            <Col xs={24} md={8}>
              <Space direction="vertical" className="w-full" size={16}>
                {/* 整体进度 */}
                <Card size="small" className="!rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <Text strong>整体进度</Text>
                    <Text type="secondary" className="text-sm">{completionRate}%</Text>
                  </div>
                  <Progress percent={completionRate} showInfo={false} strokeColor="#1890ff" size="small" />
                  <div className="flex justify-between mt-2 text-xs text-gray-400">
                    <span>已完成 {stats.completedPapers} 篇</span>
                    <span>总计 {stats.totalPapers} 篇</span>
                  </div>
                </Card>

                {/* 最近活动 */}
                <Card size="small" className="!rounded-xl" title={<Space><ClockCircleOutlined /><span>最近活动</span></Space>}>
                  <List
                    size="small"
                    dataSource={RECENT_ACTIVITIES}
                    renderItem={(item) => (
                      <List.Item className="!py-2">
                        <Space>
                          <Avatar size="small" style={{ backgroundColor: item.color }} icon={item.icon} />
                          <div>
                            <Text className="text-sm">{item.action}</Text>
                            <div className="text-xs text-gray-400">{item.time}</div>
                          </div>
                        </Space>
                      </List.Item>
                    )}
                  />
                </Card>

                {/* 数据来源 */}
                <Card size="small" className="!rounded-xl" title={<Space><GlobalOutlined /><span>数据来源</span></Space>}>
                  <Row gutter={8}>
                    {SOURCE_STATS.map(source => (
                      <Col span={12} key={source.label} className="mb-2">
                        <div className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                          <span style={{ color: source.color, fontSize: '18px' }}>{source.icon}</span>
                          <div>
                            <Text className="text-sm font-medium">{source.label}</Text>
                            <div className="text-xs text-gray-400">{source.description}</div>
                          </div>
                        </div>
                      </Col>
                    ))}
                  </Row>
                </Card>
              </Space>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}

export default HomePage
