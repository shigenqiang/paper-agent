import React from 'react'
import { Card, Row, Col, Typography, Space, Divider, Button, Progress, Tag, Avatar } from 'antd'
import {
  SearchOutlined,
  FileTextOutlined,
  ReadOutlined,
  BulbOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  GlobalOutlined,
  ExperimentOutlined,
  CheckSquareOutlined,
  MessageOutlined,
  BuildOutlined,
  DatabaseOutlined,
  ArrowRightOutlined,
  FireOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography

// 功能模块配置
const FEATURE_CATEGORIES = [
  {
    title: '论文搜索',
    key: 'search',
    icon: <SearchOutlined />,
    color: '#1890ff',
    bgGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    features: [
      { key: 'arxiv', label: 'arXiv 搜索', description: '搜索预印本论文，覆盖物理、数学、计算机等学科', icon: <GlobalOutlined />, hot: true },
      { key: 'pubmed', label: 'PubMed 搜索', description: '医学/生物文献数据库，权威医学研究成果', icon: <ExperimentOutlined />, hot: true },
      { key: 'semantic', label: 'Semantic Scholar', description: 'AI学术搜索，智能相关论文推荐', icon: <RobotOutlined /> },
      { key: 'openalex', label: 'OpenAlex 搜索', description: '开放学术数据，全学科覆盖', icon: <DatabaseOutlined /> },
    ]
  },
  {
    title: '论文管理',
    key: 'paper',
    icon: <FileTextOutlined />,
    color: '#52c41a',
    bgGradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    features: [
      { key: 'create', label: '新建论文', description: '创建论文项目，开始新的写作之旅', icon: <FileTextOutlined />, hot: true },
      { key: 'outline', label: '大纲生成', description: 'AI智能分析，生成完整论文结构', icon: <CheckSquareOutlined />, hot: true },
      { key: 'draft', label: '初稿撰写', description: 'AI辅助写作，快速生成章节内容', icon: <EditOutlined /> },
      { key: 'revise', label: '智能修订', description: '语法检查、结构优化、语言润色', icon: <BuildOutlined /> },
    ]
  },
  {
    title: '文献综述',
    key: 'literature',
    icon: <ReadOutlined />,
    color: '#722ed1',
    bgGradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    features: [
      { key: 'search', label: '文献搜索', description: '多源文献检索，跨库统一搜索', icon: <SearchOutlined /> },
      { key: 'review', label: '综述生成', description: '自动分析整理，生成文献综述', icon: <FileTextOutlined /> },
      { key: 'citation', label: '引用管理', description: 'BibTeX/Zotero，规范化引用格式', icon: <ReadOutlined /> },
    ]
  },
  {
    title: '学术资讯',
    key: 'digest',
    icon: <BulbOutlined />,
    color: '#fa8c16',
    bgGradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    features: [
      { key: 'daily', label: '每日资讯', description: '每日学术快报，掌握最新研究动态', icon: <BulbOutlined />, hot: true },
      { key: 'weekly', label: '每周资讯', description: '每周研究汇总，追踪领域进展', icon: <BulbOutlined /> },
      { key: 'monthly', label: '每月资讯', description: '月度研究总结，深度分析趋势', icon: <BulbOutlined /> },
    ]
  },
  {
    title: '系统设置',
    key: 'settings',
    icon: <SettingOutlined />,
    color: '#8c8c8c',
    bgGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    features: [
      { key: 'keywords', label: '关键词设置', description: '配置学术资讯监测关键词', icon: <SettingOutlined /> },
      { key: 'api', label: 'API配置', description: '设置API密钥和大模型参数', icon: <SettingOutlined /> },
      { key: 'zotero', label: 'Zotero同步', description: '连接Zotero文献库同步管理', icon: <DatabaseOutlined /> },
    ]
  },
]

const FeaturesPage = () => {
  const navigate = useNavigate()

  const handleFeatureClick = (categoryKey, featureKey) => {
    if (categoryKey === 'settings') {
      navigate('/settings')
    } else if (categoryKey === 'paper') {
      navigate('/writing')
    } else if (categoryKey === 'literature') {
      navigate('/literature')
    } else if (categoryKey === 'search') {
      navigate('/literature')
    } else if (categoryKey === 'digest') {
      navigate('/reports')
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题区 */}
      <div className="text-center py-6 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-xl text-white">
        <Title level={2} className="!text-white">
          <ThunderboltOutlined /> Paper Agent 功能概览
        </Title>
        <Text className="text-white/90 text-lg">
          完整的AI学术论文写作解决方案 · 便捷 · 专业 · 舒适
        </Text>
      </div>

      {/* 功能分类卡片 */}
      {FEATURE_CATEGORIES.map(category => (
        <Card
          key={category.key}
          className="!rounded-xl !overflow-hidden"
          styles={{ body: { padding: 0 }}}
        >
          {/* 分类头部 */}
          <div
            className="px-6 py-4 text-white flex items-center gap-3"
            style={{ background: category.bgGradient }}
          >
            <span style={{ fontSize: '24px' }}>{category.icon}</span>
            <Title level={4} className="!mb-0 !text-white">{category.title}</Title>
          </div>

          {/* 功能卡片网格 */}
          <div className="p-4 bg-gray-50">
            <Row gutter={[16, 16]}>
              {category.features.map(feature => (
                <Col xs={24} sm={12} md={8} lg={6} key={feature.key}>
                  <Card
                    hoverable
                    className="h-full transition-all hover:shadow-lg hover:-translate-y-1"
                    onClick={() => handleFeatureClick(category.key, feature.key)}
                    styles={{ body: { padding: '16px' }}}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg flex-shrink-0"
                        style={{ background: category.bgGradient }}
                      >
                        {feature.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Text strong className="text-base">{feature.label}</Text>
                          {feature.hot && (
                            <Tag className="!m-0" color="red" style={{ fontSize: '10px', padding: '0 4px' }}>
                              <FireOutlined /> HOT
                            </Tag>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{feature.description}</div>
                      </div>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        </Card>
      ))}

    </div>
  )
}

export default FeaturesPage
