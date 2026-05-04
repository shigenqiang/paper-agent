import React, { useState, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Input, Select, Tag, App, Spin, Avatar, message, Dropdown, Steps, Divider, Modal } from 'antd'
import {
  SendOutlined,
  ClearOutlined,
  CopyOutlined,
  FileTextOutlined,
  RobotOutlined,
  UserOutlined,
  EditOutlined,
  ScissorOutlined,
  BookOutlined,
  ProfileOutlined,
  ThunderboltOutlined,
  MessageOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { aiAPI, paperAPI } from '../services/api'
import { useAssistantStore } from '../store/assistantStore'

const { Title, Text } = Typography
const { TextArea } = Input

// Agent类型定义
const AGENTS = {
  OUTLINE: {
    key: 'outline',
    name: '大纲生成',
    icon: <ProfileOutlined />,
    color: '#1890ff',
    description: '根据研究主题生成完整的论文大纲结构',
    inputs: ['topic'],
    outputs: 'outline'
  },
  LITERATURE: {
    key: 'literature',
    name: '文献综述',
    icon: <BookOutlined />,
    color: '#52c41a',
    description: '搜索和分析相关文献，生成文献综述',
    inputs: ['topic', 'keywords'],
    outputs: 'literature_review'
  },
  DRAFT: {
    key: 'draft',
    name: '内容生成',
    icon: <EditOutlined />,
    color: '#722ed1',
    description: '根据大纲生成论文各章节内容',
    inputs: ['outline', 'section'],
    outputs: 'content'
  },
  REVISE: {
    key: 'revise',
    name: '智能改稿',
    icon: <ScissorOutlined />,
    color: '#fa8c16',
    description: '润色、翻译、精简、扩展论文内容',
    inputs: ['content', 'revise_type'],
    outputs: 'revised_content'
  }
}

const AGENT_COLORS = {
  outline: '#1890ff',
  literature: '#52c41a',
  draft: '#722ed1',
  revise: '#fa8c16'
}

const AIAssistantPage = () => {
  const {
    papers, setPapers, deletePaper,
    selectedPaperId, setSelectedPaperId,
    clearChat,
  } = useAssistantStore()
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newPaperTitle, setNewPaperTitle] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const chatEndRef = useRef(null)
  const { messageApi, contextHolder } = message.useMessage()

  // Agent相关状态
  const [activeAgent, setActiveAgent] = useState(null)
  const [agentResult, setAgentResult] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)

  // 各Agent的输入状态
  const [topic, setTopic] = useState('')
  const [keywords, setKeywords] = useState('')
  const [sectionContent, setSectionContent] = useState('')
  const [reviseType, setReviseType] = useState('polish')

  const userId = 'user_' + Math.random().toString(36).substr(2, 9)

  useEffect(() => {
    loadPapers()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [agentResult])

  const loadPapers = async () => {
    try {
      const response = await paperAPI.getPapers()
      setPapers(response.data || [])
    } catch (e) {
      console.error('加载论文列表失败:', e)
    }
  }

  const handleSelectPaper = (paper) => {
    setSelectedPaperId(paper.id)
    setSelectedPaper(paper)
  }

  const handleCreatePaper = async () => {
    if (!newPaperTitle.trim()) {
      messageApi.warning('请输入论文标题')
      return
    }
    try {
      const response = await paperAPI.createPaper({
        title: newPaperTitle,
        topic: '待定'
      })
      if (response.success && response.data) {
        const paper = response.data
        setPapers(prev => [paper, ...prev])
        setSelectedPaperId(paper.id)
        setSelectedPaper(paper)
        setIsCreateModalOpen(false)
        setNewPaperTitle('')
        message.success('论文创建成功')
      }
    } catch (e) {
      messageApi.error('创建论文失败')
    }
  }

  // 执行Agent
  const executeAgent = async () => {
    if (!selectedPaperId) {
      messageApi.warning('请先选择论文')
      return
    }

    if (!activeAgent) {
      messageApi.warning('请选择要使用的功能')
      return
    }

    setAgentLoading(true)
    setAgentResult(null)

    try {
      let result = ''
      let prompt = ''

      switch (activeAgent) {
        case 'outline':
          if (!topic.trim()) {
            messageApi.warning('请输入研究主题')
            setAgentLoading(false)
            return
          }
          // 调用后端生成大纲
          const outlineResult = await paperAPI.generateOutline(selectedPaperId, topic)
          if (outlineResult.success) {
            result = outlineResult.data?.outline || '大纲生成完成'
          } else {
            result = outlineResult.error || '大纲生成失败'
          }
          break

        case 'literature':
          if (!topic.trim()) {
            messageApi.warning('请输入研究主题')
            setAgentLoading(false)
            return
          }
          prompt = `请搜索并分析以下主题的文献：${topic}\n关键词：${keywords}`
          break

        case 'draft':
          if (!topic.trim()) {
            messageApi.warning('请输入论文大纲')
            setAgentLoading(false)
            return
          }
          prompt = `请根据以下大纲生成内容：\n${topic}\n\n相关方向：${sectionContent}`
          break

        case 'revise':
          if (!sectionContent.trim()) {
            messageApi.warning('请输入要修改的内容')
            setAgentLoading(false)
            return
          }
          const reviseResult = await paperAPI.formatContent(
            selectedPaperId,
            selectedPaper?.sections?.[0]?.id || '1',
            sectionContent
          )
          if (reviseResult.success) {
            const revisedContent = reviseResult.data?.content || reviseResult.data?.revised_text
            result = revisedContent || '修改完成'
          } else {
            result = reviseResult.error || '修改失败'
          }
          setAgentLoading(false)
          return

        default:
          result = '未知功能'
      }

      // 其他Agent使用通用chat接口
      if (prompt) {
        const response = await aiAPI.sendMessage(selectedPaperId, prompt, userId, `agent_${activeAgent}`)
        if (response.success) {
          result = response.data?.response || ''
        } else {
          result = response.error || '执行失败'
        }
      }

      setAgentResult(result)
    } catch (e) {
      console.error('Agent执行失败:', e)
      setAgentResult('执行出错：' + e.message)
    } finally {
      setAgentLoading(false)
    }
  }

  const getRevisePrompt = () => {
    const prompts = {
      polish: '请润色以下内容，使其更加流畅专业：\n\n',
      translate: '请翻译以下内容，保持学术风格：\n\n',
      shorten: '请精简以下内容，保留核心观点：\n\n',
      expand: '请扩展以下内容，增加细节和深度：\n\n'
    }
    return prompts[reviseType] || prompts.polish
  }

  const handleCopy = (content) => {
    navigator.clipboard.writeText(content)
    message.success('已复制')
  }

  const paperMenuItems = papers.map(paper => ({
    key: paper.id,
    label: (
      <Space>
        {selectedPaperId === paper.id ? <FileTextOutlined style={{ color: '#1890ff' }} /> : <FileTextOutlined />}
        <span>{paper.title || '未命名'}</span>
      </Space>
    ),
    onClick: () => handleSelectPaper(paper)
  }))

  const paperDropdownContent = (
    <div className="p-2 w-72">
      <div className="text-xs text-gray-500 mb-2">选择论文</div>
      {papers.length === 0 ? (
        <Text type="secondary" className="text-xs">暂无论文</Text>
      ) : (
        papers.map(paper => (
          <div
            key={paper.id}
            className={`flex items-center justify-between p-2 rounded hover:bg-gray-50 cursor-pointer ${selectedPaperId === paper.id ? 'bg-blue-50' : ''}`}
            onClick={() => handleSelectPaper(paper)}
          >
            <Space>
              <FileTextOutlined style={{ color: selectedPaperId === paper.id ? '#1890ff' : '#999' }} />
              <span className="text-sm">{paper.title || '未命名'}</span>
            </Space>
          </div>
        ))
      )}
      <div className="mt-2 pt-2 border-t">
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => setIsCreateModalOpen(true)} className="!pl-0">
          新建论文
        </Button>
      </div>
    </div>
  )

  // 渲染Agent输入面板
  const renderAgentInput = () => {
    if (!activeAgent) {
      return (
        <div className="text-center py-8 text-gray-400">
          <RobotOutlined className="text-4xl mb-3" />
          <div>选择左侧功能开始使用</div>
        </div>
      )
    }

    switch (activeAgent) {
      case 'outline':
        return (
          <div className="space-y-4">
            <div>
              <Text strong>研究主题 *</Text>
              <TextArea
                placeholder="请输入论文的研究主题，例如：基于深度学习的图像识别技术研究"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                rows={3}
                className="mt-2"
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={executeAgent}
                loading={agentLoading}
              >
                生成大纲
              </Button>
            </div>
          </div>
        )

      case 'revise':
        return (
          <div className="space-y-4">
            <div>
              <Text strong>修改类型</Text>
              <div className="flex gap-2 mt-2 flex-wrap">
                {['polish', 'translate', 'shorten', 'expand'].map(type => (
                  <Tag
                    key={type}
                    color={reviseType === type ? AGENT_COLORS.revise : 'default'}
                    className="cursor-pointer"
                    onClick={() => setReviseType(type)}
                  >
                    {type === 'polish' && '润色'}
                    {type === 'translate' && '翻译'}
                    {type === 'shorten' && '精简'}
                    {type === 'expand' && '扩展'}
                  </Tag>
                ))}
              </div>
            </div>
            <div>
              <Text strong>待修改内容 *</Text>
              <TextArea
                placeholder="粘贴要修改的原文..."
                value={sectionContent}
                onChange={(e) => setSectionContent(e.target.value)}
                rows={6}
                className="mt-2"
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="primary"
                icon={<ScissorOutlined />}
                onClick={executeAgent}
                loading={agentLoading}
                style={{ backgroundColor: AGENT_COLORS.revise }}
              >
                执行修改
              </Button>
            </div>
          </div>
        )

      case 'literature':
        return (
          <div className="space-y-4">
            <div>
              <Text strong>研究主题 *</Text>
              <TextArea
                placeholder="请输入要搜索文献的主题"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                rows={3}
                className="mt-2"
              />
            </div>
            <div>
              <Text strong>关键词（可选）</Text>
              <TextArea
                placeholder="输入关键词，用逗号分隔"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                rows={2}
                className="mt-2"
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="primary"
                icon={<BookOutlined />}
                onClick={executeAgent}
                loading={agentLoading}
                style={{ backgroundColor: AGENT_COLORS.literature }}
              >
                搜索文献
              </Button>
            </div>
          </div>
        )

      case 'draft':
        return (
          <div className="space-y-4">
            <div>
              <Text strong>论文大纲 *</Text>
              <TextArea
                placeholder="请输入论文大纲结构"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                rows={4}
                className="mt-2"
              />
            </div>
            <div>
              <Text strong>章节内容（可选）</Text>
              <TextArea
                placeholder="输入章节内容或研究方向"
                value={sectionContent}
                onChange={(e) => setSectionContent(e.target.value)}
                rows={3}
                className="mt-2"
              />
            </div>
            <div className="flex justify-end">
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={executeAgent}
                loading={agentLoading}
                style={{ backgroundColor: AGENT_COLORS.draft }}
              >
                生成内容
              </Button>
            </div>
          </div>
        )

      default:
        return (
          <div className="text-center py-8 text-gray-400">
            <MessageOutlined className="text-4xl mb-3" />
            <div>该功能开发中...</div>
          </div>
        )
    }
  }

  return (
    <App>
      {contextHolder}
      <div className="h-full flex flex-col bg-gray-50">
        {/* 顶部导航 */}
        <div className="bg-white border-b px-4 py-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <Space>
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <RobotOutlined className="text-white text-sm" />
              </div>
              <div>
                <Title level={5} className="!mb-0">AI论文助手</Title>
              </div>
            </Space>

            {/* 论文选择 */}
            <Dropdown
              dropdownRender={() => paperDropdownContent}
              trigger={['click']}
              placement="bottomRight"
            >
              <Button className="!min-w-[160px]">
                <Space>
                  <FileTextOutlined />
                  <span className="truncate max-w-[120px]">
                    {selectedPaper?.title || '选择论文'}
                  </span>
                </Space>
              </Button>
            </Dropdown>
          </div>
        </div>

        {/* 主内容区 - 三栏布局 */}
        <div className="flex-1 flex overflow-hidden">
          {/* 左侧：Agent选择 */}
          <div className="w-64 bg-white border-r flex-shrink-0 overflow-y-auto">
            <div className="p-4">
              <Text type="secondary" className="text-xs uppercase tracking-wider">选择功能</Text>
              <div className="mt-3 space-y-2">
                {Object.values(AGENTS).map(agent => (
                  <Card
                    key={agent.key}
                    size="small"
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      activeAgent === agent.key ? 'ring-2' : ''
                    }`}
                    style={{
                      borderColor: activeAgent === agent.key ? agent.color : undefined,
                      ringColor: activeAgent === agent.key ? agent.color : undefined
                    }}
                    onClick={() => {
                      setActiveAgent(activeAgent === agent.key ? null : agent.key)
                      setAgentResult(null)
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: agent.color + '15', color: agent.color }}
                      >
                        {agent.icon}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{agent.name}</div>
                        <div className="text-xs text-gray-400">{agent.description}</div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>

            {/* 已选论文信息 */}
            {selectedPaper && (
              <>
                <Divider className="!my-2" />
                <div className="p-4">
                  <Text type="secondary" className="text-xs uppercase tracking-wider">当前论文</Text>
                  <div className="mt-2">
                    <div className="font-medium text-sm truncate">{selectedPaper.title}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      章节：{selectedPaper.sections?.length || 0} 个
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* 中间：输入面板 */}
          <div className="flex-1 flex flex-col bg-white overflow-hidden">
            <div className="p-4 border-b flex-shrink-0">
              <div className="flex items-center gap-2">
                {activeAgent && (
                  <>
                    {AGENTS[activeAgent].icon}
                    <Text strong>{AGENTS[activeAgent].name}</Text>
                  </>
                )}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {renderAgentInput()}

              {/* 结果展示 */}
              {agentResult && (
                <div className="mt-6">
                  <Divider>
                    <Space>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      <span>执行结果</span>
                    </Space>
                  </Divider>
                  <Card className="bg-gray-50">
                    <div
                      className="whitespace-pre-wrap text-sm"
                      style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                    >
                      {agentResult}
                    </div>
                  </Card>
                  <div className="mt-2 flex justify-end">
                    <Button
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopy(agentResult)}
                    >
                      复制结果
                    </Button>
                  </div>
                </div>
              )}

              {agentLoading && (
                <div className="mt-6 text-center">
                  <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                  <div className="mt-2 text-gray-500">AI正在处理中...</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 新建论文弹窗 */}
        <Modal
          title="新建论文"
          open={isCreateModalOpen}
          onCancel={() => setIsCreateModalOpen(false)}
          onOk={handleCreatePaper}
          okText="创建"
        >
          <div className="py-4">
            <Text strong>论文标题</Text>
            <Input
              className="mt-2"
              placeholder="请输入论文标题"
              value={newPaperTitle}
              onChange={(e) => setNewPaperTitle(e.target.value)}
              onPressEnter={() => handleCreatePaper()}
            />
          </div>
        </Modal>
      </div>
    </App>
  )
}

export default AIAssistantPage