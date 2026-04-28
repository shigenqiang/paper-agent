import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Input, Select, Divider, Tag, message, Spin, Tabs, Modal, Empty, Avatar, Badge, Tooltip, Dropdown } from 'antd'
import {
  SendOutlined,
  EditOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  ClearOutlined,
  CopyOutlined,
  ScissorOutlined,
  PlusOutlined,
  FileTextOutlined,
  RobotOutlined,
  UserOutlined,
  SettingOutlined,
  MoreOutlined,
  LikeOutlined,
  DislikeOutlined,
  StopOutlined,
  MenuFoldOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { aiAPI, paperAPI } from '../services/api'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input
const { Option } = Select

// 消息气泡组件
const MessageBubble = ({ message, onCopy }) => {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-gray-100 text-gray-500 text-xs px-3 py-1 rounded-full">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-3 my-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar
        size={36}
        className={isUser ? '!bg-blue-500' : '!bg-gradient-to-br from-blue-400 to-purple-500'}
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
      />
      <div className={`max-w-[70%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? '!bg-blue-500 text-white rounded-tr-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
          }`}
          style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
        >
          {message.content}
        </div>
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : ''}`}>
          <Space size="small">
            {message.time && <span>{message.time}</span>}
            {!isUser && (
              <Space size="small">
                <Tooltip title="复制">
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => onCopy(message.content)}
                    className="!text-gray-400"
                  />
                </Tooltip>
                <Tooltip title="有帮助">
                  <Button type="text" size="small" icon={<LikeOutlined />} className="!text-gray-400" />
                </Tooltip>
                <Tooltip title="需要改进">
                  <Button type="text" size="small" icon={<DislikeOutlined />} className="!text-gray-400" />
                </Tooltip>
              </Space>
            )}
          </Space>
        </div>
      </div>
    </div>
  )
}

const AIAssistantPage = () => {
  const [mode, setMode] = useState('write')
  const [inputValue, setInputValue] = useState('')
  const [referenceText, setReferenceText] = useState('')
  const [originalText, setOriginalText] = useState('')
  const [outputContent, setOutputContent] = useState('')
  const [sending, setSending] = useState(false)

  const [papers, setPapers] = useState([])
  const [selectedPaperId, setSelectedPaperId] = useState(null)
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newPaperTitle, setNewPaperTitle] = useState('')

  const [chatMessages, setChatMessages] = useState([
    { role: 'system', content: '对话已开启' },
    {
      role: 'assistant',
      content: '您好！我是论文Agent写作助手。\n\n✍️ 我可以帮您：\n• 根据选题生成论文大纲\n• 续写章节内容\n• 润色、翻译、精简、扩展文章\n\n请先选择或创建论文项目，然后开始对话！'
    }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const chatEndRef = useRef(null)

  const userId = useMemo(() => {
    let id = localStorage.getItem('chat_user_id')
    if (!id) {
      id = 'user_' + Math.random().toString(36).substr(2, 9)
      localStorage.setItem('chat_user_id', id)
    }
    return id
  }, [])

  const sessionId = useMemo(() => 'ai_assistant_' + (selectedPaperId || 'no_paper'), [selectedPaperId])

  useEffect(() => {
    loadPapers()
  }, [])

  const loadPapers = async () => {
    try {
      const response = await paperAPI.getPapers()
      setPapers(response.data || [])
    } catch (e) {
      console.error('加载论文列表失败:', e)
    }
  }

  useEffect(() => {
    if (!selectedPaperId) return
    const loadHistory = async () => {
      try {
        const res = await aiAPI.getChatHistory(selectedPaperId, userId, sessionId)
        if (res?.success && res?.data?.messages?.length > 0) {
          setChatMessages(prev => [...prev, ...res.data.messages.slice(-10)])
        }
      } catch (e) {
        console.warn('加载聊天历史失败:', e)
      }
    }
    loadHistory()
  }, [selectedPaperId, userId, sessionId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleCreatePaper = async () => {
    if (!newPaperTitle.trim()) {
      message.warning('请输入论文标题')
      return
    }
    try {
      const response = await paperAPI.createPaper({
        title: newPaperTitle,
        topic: '待定'
      })
      if (response.success && response.data) {
        setPapers(prev => [response.data, ...prev])
        setSelectedPaperId(response.data.id)
        setSelectedPaper(response.data)
        setIsCreateModalOpen(false)
        setNewPaperTitle('')
        message.success('论文创建成功')
      }
    } catch (e) {
      message.error('创建论文失败')
    }
  }

  const handleSelectPaper = (paperId) => {
    const paper = papers.find(p => p.id === paperId)
    setSelectedPaperId(paperId)
    setSelectedPaper(paper)
  }

  const handleWrite = async () => {
    if (!inputValue.trim() || sending) return
    if (!selectedPaperId) {
      message.warning('请先选择或创建论文项目')
      return
    }
    setSending(true)
    setOutputContent('')

    const topic = inputValue
    const reference = referenceText.trim()

    setChatMessages(prev => [...prev, {
      role: 'user',
      content: `请为"${topic}"生成论文大纲${reference ? '，参考以下资料：\n' + reference : ''}`,
      time: new Date().toLocaleTimeString()
    }])

    try {
      const response = await paperAPI.generateOutline(selectedPaperId, topic)

      if (response.success) {
        const outline = response.data || []
        let outlineText = '已生成大纲：\n\n'
        outline.forEach((item, idx) => {
          outlineText += `${idx + 1}. ${item.title}\n`
        })
        setOutputContent(outlineText)
        setChatMessages(prev => [...prev, { role: 'assistant', content: outlineText, time: new Date().toLocaleTimeString() }])
        message.success('大纲生成成功')
      } else {
        throw new Error(response.error)
      }
    } catch (error) {
      message.error('生成失败，请稍后重试')
      setChatMessages(prev => [...prev, { role: 'assistant', content: '抱歉，生成失败，请稍后重试。', time: new Date().toLocaleTimeString() }])
    } finally {
      setSending(false)
    }
  }

  const handleRevise = async () => {
    if (!originalText.trim() || !inputValue.trim() || sending) return
    if (!selectedPaperId) {
      message.warning('请先选择或创建论文项目')
      return
    }
    setSending(true)
    setOutputContent('')

    const reviseType = inputValue
    setChatMessages(prev => [...prev, {
      role: 'user',
      content: `请帮我修改以下内容（${reviseType === 'polish' ? '润色' : reviseType === 'translate' ? '翻译' : reviseType === 'shorten' ? '精简' : '扩展'}）：\n\n${originalText}`,
      time: new Date().toLocaleTimeString()
    }])

    let prompt = ''
    switch (reviseType) {
      case 'polish':
        prompt = `请润色以下论文内容，使其更加流畅，专业、符合学术规范：\n\n${originalText}`
        break
      case 'translate':
        prompt = `请将以下中文论文内容翻译成英文（或将英文翻译成中文），保持学术风格：\n\n${originalText}`
        break
      case 'shorten':
        prompt = `请精简以下论文内容，保留核心观点和方法，去除冗余：\n\n${originalText}`
        break
      case 'expand':
        prompt = `请扩展以下论文内容，增加更多细节、论据和深度分析：\n\n${originalText}`
        break
      default:
        prompt = `请修改以下内容：\n\n${originalText}`
    }

    try {
      const response = await aiAPI.sendMessage(selectedPaperId, prompt, userId, sessionId)

      if (response.success && response.data) {
        const content = response.data.response || ''
        setOutputContent(content)
        setChatMessages(prev => [...prev, { role: 'assistant', content, time: new Date().toLocaleTimeString() }])
      } else {
        throw new Error(response.error)
      }
    } catch (error) {
      message.error('修改失败，请稍后重试')
      setChatMessages(prev => [...prev, { role: 'assistant', content: '抱歉，修改失败，请稍后重试。', time: new Date().toLocaleTimeString() }])
    } finally {
      setSending(false)
    }
  }

  const handleChatSend = async () => {
    if (!chatInput.trim() || chatSending) return
    if (!selectedPaperId) {
      message.warning('请先选择或创建论文项目')
      return
    }
    setChatSending(true)

    const msg = chatInput
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: msg, time: new Date().toLocaleTimeString() }])

    try {
      const response = await aiAPI.sendMessage(selectedPaperId, msg, userId, sessionId)

      if (response.success && response.data) {
        const content = response.data.response || ''
        setChatMessages(prev => [...prev, { role: 'assistant', content, time: new Date().toLocaleTimeString() }])
      } else {
        throw new Error(response.error)
      }
    } catch (error) {
      message.error('发送失败')
      setChatMessages(prev => [...prev, { role: 'assistant', content: '抱歉，发送失败，请稍后重试。', time: new Date().toLocaleTimeString() }])
    } finally {
      setChatSending(false)
    }
  }

  const handleCopy = (content) => {
    navigator.clipboard.writeText(content)
    message.success('已复制到剪贴板')
  }

  const handleClear = () => {
    setInputValue('')
    setOriginalText('')
    setOutputContent('')
  }

  return (
    <div className="h-full flex gap-4">
      {/* 左侧：写作/修改功能 */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* 论文选择器 */}
        <Card size="small" className="!rounded-lg">
          <div className="flex justify-between items-center">
            <Space>
              <FileTextOutlined className="text-gray-400" />
              <Text strong>当前论文：</Text>
              <Select
                placeholder="选择论文项目"
                value={selectedPaperId}
                onChange={handleSelectPaper}
                className="!w-64"
                allowClear
              >
                {papers.map(p => (
                  <Option key={p.id} value={p.id}>{p.title}</Option>
                ))}
              </Select>
            </Space>
            <Button type="primary" icon={<PlusOutlined />} size="small" onClick={() => setIsCreateModalOpen(true)}>
              新建论文
            </Button>
          </div>
        </Card>

        {/* 模式切换 */}
        <Card className="flex-1 !rounded-lg" bodyStyle={{ display: 'flex', flexDirection: 'column' }}>
          <Tabs
            activeKey={mode}
            onChange={setMode}
            items={[
              {
                key: 'write',
                label: <span><EditOutlined /> 写作</span>,
                children: (
                  <div className="space-y-4 flex-1">
                    <div>
                      <Text strong className="mb-2 block">论文选题</Text>
                      <Input
                        placeholder="请输入论文主题，例如：人工智能对未来教育的影响"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onPressEnter={() => handleWrite()}
                        suffix={
                          <Tooltip title="Enter发送">
                            <Button type="text" size="small" icon={<SendOutlined />} onClick={handleWrite} className="!text-blue-500" />
                          </Tooltip>
                        }
                      />
                    </div>
                    <div>
                      <Text strong className="mb-2 block">参考资料（可选）</Text>
                      <TextArea
                        placeholder="可以粘贴参考文章，大纲或要点，AI会结合这些资料生成更准确的内容..."
                        rows={3}
                        value={referenceText}
                        onChange={(e) => setReferenceText(e.target.value)}
                      />
                    </div>
                    <Space>
                      <Button
                        type="primary"
                        icon={<ThunderboltOutlined />}
                        onClick={handleWrite}
                        loading={sending}
                        disabled={!inputValue.trim() || !selectedPaperId}
                      >
                        生成大纲
                      </Button>
                      <Button icon={<ClearOutlined />} onClick={handleClear}>清空</Button>
                    </Space>
                  </div>
                ),
              },
              {
                key: 'revise',
                label: <span><ScissorOutlined /> 修改</span>,
                children: (
                  <div className="space-y-4 flex-1">
                    <div>
                      <Text strong className="mb-2 block">修改类型</Text>
                      <Select
                        className="!w-full"
                        value={inputValue}
                        onChange={setInputValue}
                        placeholder="请选择修改类型"
                      >
                        <Option value="polish">润色 - 优化语言表达</Option>
                        <Option value="translate">翻译 - 中英文互译</Option>
                        <Option value="shorten">精简 - 压缩冗余内容</Option>
                        <Option value="expand">扩展 - 丰富详细内容</Option>
                      </Select>
                    </div>
                    <div className="flex-1">
                      <Text strong className="mb-2 block">原文内容</Text>
                      <TextArea
                        placeholder="请输入要修改的论文内容..."
                        rows={6}
                        value={originalText}
                        onChange={(e) => setOriginalText(e.target.value)}
                        className="h-full"
                      />
                    </div>
                    <Space>
                      <Button
                        type="primary"
                        icon={<ScissorOutlined />}
                        onClick={handleRevise}
                        loading={sending}
                        disabled={!originalText.trim() || !inputValue || !selectedPaperId}
                      >
                        开始修改
                      </Button>
                      <Button icon={<ClearOutlined />} onClick={handleClear}>清空</Button>
                    </Space>
                  </div>
                ),
              },
            ]}
          />
        </Card>

        {/* 生成结果 */}
        <Card
          className="!rounded-lg"
          title={
            <Space>
              <FileTextOutlined />
              <span>生成结果</span>
            </Space>
          }
          extra={
            <Button icon={<CopyOutlined />} onClick={() => handleCopy(outputContent)} disabled={!outputContent}>
              复制
            </Button>
          }
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        >
          {sending ? (
            <div className="flex items-center justify-center h-full">
              <Spin tip="论文Agent正在生成内容..." />
            </div>
          ) : outputContent ? (
            <div className="flex-1 overflow-auto">
              <pre className="whitespace-pre-wrap text-sm leading-relaxed">{outputContent.replace(/\*/g, '')}</pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <Empty description={mode === 'write' ? '输入选题后点击「生成大纲」' : '选择修改类型并输入原文后点击「开始修改」'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          )}
        </Card>
      </div>

      {/* 右侧：对话窗口 */}
      <Card
        className="w-96 flex flex-col !rounded-lg"
        bodyStyle={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 0 }}
      >
        {/* 头部 */}
        <div className="px-4 py-3 border-b flex justify-between items-center bg-gray-50">
          <Space>
            <Avatar size="small" className="!bg-gradient-to-br from-blue-400 to-purple-500" icon={<RobotOutlined />} />
            <Text strong>论文Agent对话</Text>
          </Space>
          <Space>
            {!selectedPaperId && <Tag color="warning" className="text-xs">未选择论文</Tag>}
            {selectedPaperId && <Tag color="success" className="text-xs">已连接</Tag>}
          </Space>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-4">
          {chatMessages.map((msg, index) => (
            <MessageBubble key={index} message={msg} onCopy={handleCopy} />
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* 输入框 */}
        <div className="p-3 border-t bg-gray-50">
          <Space.Compact className="w-full">
            <Input
              placeholder={selectedPaperId ? "输入问题，AI助手为您解答..." : "请先选择论文项目"}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onPressEnter={() => handleChatSend()}
              disabled={chatSending || !selectedPaperId}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleChatSend}
              loading={chatSending}
              disabled={!selectedPaperId}
            />
          </Space.Compact>
        </div>
      </Card>

      {/* 创建论文弹窗 */}
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
  )
}

export default AIAssistantPage
