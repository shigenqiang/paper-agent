import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Input, Select, Divider, Tag, message, Spin, Empty, Avatar, Tooltip, Modal, List, Popconfirm } from 'antd'
import {
  SendOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  ClearOutlined,
  CopyOutlined,
  ScissorOutlined,
  PlusOutlined,
  FileTextOutlined,
  RobotOutlined,
  UserOutlined,
  EditOutlined,
  SwapOutlined,
  DeleteOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { aiAPI, paperAPI } from '../services/api'

const { Title, Text } = Typography
const { TextArea } = Input

// 模式配置
const MODES = {
  WRITE: 'write',
  REVISE: 'revise'
}

const MODE_CONFIG = {
  [MODES.WRITE]: {
    label: '写作模式',
    icon: <EditOutlined />,
    color: '#1890ff',
    description: '生成大纲、续写内容'
  },
  [MODES.REVISE]: {
    label: '修改模式',
    icon: <ScissorOutlined />,
    color: '#722ed1',
    description: '润色、翻译、精简、扩展'
  }
}

// 消息气泡组件
const MessageBubble = ({ message, onCopy, onInsert }) => {
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

  if (isSystem && message.isModeTip) {
    return (
      <div className="flex justify-center my-2">
        <div className={`text-xs px-3 py-1 rounded-full ${message.mode === MODES.WRITE ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'}`}>
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-3 my-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar
        size={32}
        className={isUser ? '!bg-blue-500' : '!bg-gradient-to-br from-blue-400 to-purple-500'}
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
      />
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-2 rounded-2xl text-sm ${
            isUser
              ? '!bg-blue-500 text-white rounded-tr-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
          }`}
          style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: '1.6' }}
        >
          {message.content}
        </div>
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : ''}`}>
          <Space size="small">
            {message.time && <span>{message.time}</span>}
            {!isUser && message.content && (
              <Space size="small">
                <Tooltip title="复制">
                  <Button type="text" size="small" icon={<CopyOutlined />} onClick={() => onCopy(message.content)} className="!text-gray-400 !w-6 !h-6" />
                </Tooltip>
              </Space>
            )}
          </Space>
        </div>
      </div>
    </div>
  )
}

// 快速操作按钮
const QuickAction = ({ mode, onAction }) => {
  const actions = mode === MODES.WRITE ? [
    { key: 'outline', label: '生成大纲', icon: <FileTextOutlined /> },
    { key: 'continue', label: 'AI续写', icon: <EditOutlined /> },
  ] : [
    { key: 'polish', label: '润色', icon: <EditOutlined /> },
    { key: 'translate', label: '翻译', icon: <SwapOutlined /> },
    { key: 'shorten', label: '精简', icon: <DeleteOutlined /> },
    { key: 'expand', label: '扩展', icon: <PlusOutlined /> },
  ]

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {actions.map(action => (
        <Tag
          key={action.key}
          className="cursor-pointer hover:bg-blue-50 border-dashed"
          onClick={() => onAction(action.key)}
        >
          {action.icon} {action.label}
        </Tag>
      ))}
    </div>
  )
}

const AIAssistantPage = () => {
  const [mode, setMode] = useState(MODES.WRITE)
  const [papers, setPapers] = useState([])
  const [selectedPaperId, setSelectedPaperId] = useState(null)
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newPaperTitle, setNewPaperTitle] = useState('')
  const [reviseType, setReviseType] = useState('polish')

  const [chatMessages, setChatMessages] = useState([
    { role: 'system', content: '对话已开启，当前为写作模式' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [contextText, setContextText] = useState('')
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

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const loadPapers = async () => {
    try {
      const response = await paperAPI.getPapers()
      setPapers(response.data || [])
    } catch (e) {
      console.error('加载论文列表失败:', e)
    }
  }

  const handleModeSwitch = (newMode) => {
    setMode(newMode)
    const modeConfig = MODE_CONFIG[newMode]
    setChatMessages(prev => [...prev, {
      role: 'system',
      content: `已切换到${modeConfig.label}：${modeConfig.description}`,
      isModeTip: true,
      mode: newMode
    }])
  }

  const handleQuickAction = (action) => {
    let prompt = ''
    if (mode === MODES.WRITE) {
      if (action === 'outline') {
        prompt = '请帮我生成论文大纲，输入选题后我会为您生成详细的大纲结构。'
      } else if (action === 'continue') {
        prompt = '请续写论文内容。请提供当前章节的内容或写作方向，我会为您续写。'
      }
    } else {
      // REVISE mode
      const actionMap = {
        polish: '润色 - 优化语言表达，使其更加流畅专业',
        translate: '翻译 - 中英文互译，保持学术风格',
        shorten: '精简 - 压缩冗余内容，保留核心观点',
        expand: '扩展 - 丰富详细内容，增加细节和深度'
      }
      prompt = `请帮我进行【${actionMap[action]}】操作。请提供需要修改的文本。`
      if (action === 'polish') setReviseType('polish')
      else if (action === 'translate') setReviseType('translate')
      else if (action === 'shorten') setReviseType('shorten')
      else if (action === 'expand') setReviseType('expand')
    }
    setChatInput(prompt)
  }

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
    if (paperId) {
      setChatMessages(prev => [...prev, {
        role: 'system',
        content: `已选择论文：${paper?.title || '未知'}`
      }])
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
    addChatMessage([{
      role: 'user',
      content: msg,
      time: new Date().toLocaleTimeString()
    }])

    // 构建prompt
    let prompt = msg
    if (contextText.trim()) {
      prompt = `【上下文】\n${contextText}\n\n【请求】\n${msg}`
    }

    // 如果是修改模式，添加修改类型提示
    if (mode === MODES.REVISE && reviseType) {
      const reviseHints = {
        polish: '请润色以下内容，使其更加流畅专业：',
        translate: '请翻译以下内容，保持学术风格：',
        shorten: '请精简以下内容，保留核心观点：',
        expand: '请扩展以下内容，增加细节和深度：'
      }
      if (reviseHints[reviseType] && !msg.startsWith('请')) {
        prompt = reviseHints[reviseType] + '\n\n' + (contextText.trim() || msg)
      }
    }

    try {
      const response = await aiAPI.sendMessage(selectedPaperId, prompt, userId, sessionId)

      if (response.success && response.data) {
        const content = response.data.response || ''
        addChatMessage([{
          role: 'assistant',
          content: content,
          time: new Date().toLocaleTimeString()
        }])
        // 清空上下文
        setContextText('')
      } else {
        throw new Error(response.error)
      }
    } catch (error) {
      message.error('发送失败')
      addChatMessage([{
        role: 'assistant',
        content: '抱歉，发送失败，请稍后重试。',
        time: new Date().toLocaleTimeString()
      }])
    } finally {
      setChatSending(false)
    }
  }

  const handleCopy = (content) => {
    navigator.clipboard.writeText(content)
    message.success('已复制到剪贴板')
  }

  const MAX_CHAT_HISTORY = 10

  const handleClearChat = () => {
    setChatMessages([{ role: 'system', content: '对话已清空' }])
    setContextText('')
  }

  // 添加消息时限制历史长度
  const addChatMessage = (newMessages) => {
    setChatMessages(prev => {
      const updated = [...prev, ...newMessages]
      // 限制消息数量，保留system消息和最后MAX_CHAT_HISTORY条
      if (updated.length > MAX_CHAT_HISTORY + 1) {
        return [updated[0], ...updated.slice(-MAX_CHAT_HISTORY)]
      }
      return updated
    })
  }

  return (
    <div className="h-full flex gap-4">
      {/* 左侧论文列表 */}
      <Card
        className="w-64 flex-shrink-0 !rounded-lg"
        title={
          <Space>
            <FileTextOutlined className="text-blue-500" />
            <span className="text-sm">论文项目</span>
          </Space>
        }
        extra={
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)} />
        }
        bodyStyle={{ padding: 0, maxHeight: 'calc(100vh - 180px)', overflow: 'auto' }}
      >
        {papers.length === 0 ? (
          <div className="p-4 text-center">
            <Text type="secondary" className="text-xs">暂无论文</Text>
            <Button type="link" size="small" onClick={() => setIsCreateModalOpen(true)}>创建论文</Button>
          </div>
        ) : (
          <List
            size="small"
            dataSource={papers}
            renderItem={paper => (
              <List.Item
                className={`px-3 py-2 cursor-pointer hover:bg-blue-50 ${selectedPaperId === paper.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''}`}
                onClick={() => handleSelectPaper(paper.id)}
              >
                <Text ellipsis className="text-sm">{paper.title || '未命名'}</Text>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 中间主对话区 */}
      <Card
        className="flex-1 !rounded-lg"
        bodyStyle={{ display: 'flex', flexDirection: 'column', padding: 0, height: 'calc(100vh - 120px)' }}
      >
        {/* 模式切换 */}
        <div className="px-4 py-3 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <Space>
              <RobotOutlined className="text-lg text-blue-500" />
              <Text strong>AI写作助手</Text>
            </Space>
            <Space>
              <Tooltip title="写作：生成大纲、续写内容">
                <Tag
                  color={mode === MODES.WRITE ? 'blue' : 'default'}
                  className={`cursor-pointer ${mode !== MODES.WRITE ? 'opacity-60' : ''}`}
                  onClick={() => handleModeSwitch(MODES.WRITE)}
                >
                  <EditOutlined /> 写作
                </Tag>
              </Tooltip>
              <Tooltip title="修改：润色、翻译、精简、扩展">
                <Tag
                  color={mode === MODES.REVISE ? 'purple' : 'default'}
                  className={`cursor-pointer ${mode !== MODES.REVISE ? 'opacity-60' : ''}`}
                  onClick={() => handleModeSwitch(MODES.REVISE)}
                >
                  <ScissorOutlined /> 修改
                </Tag>
              </Tooltip>
            </Space>
          </div>
          {/* 快速操作 */}
          <QuickAction mode={mode} onAction={handleQuickAction} />
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-4 py-2" style={{ minHeight: 0 }}>
          {chatMessages.map((msg, index) => (
            <MessageBubble key={index} message={msg} onCopy={handleCopy} />
          ))}
          {chatSending && (
            <div className="flex gap-3 my-3">
              <Avatar size={32} className="!bg-gradient-to-br from-blue-400 to-purple-500" icon={<RobotOutlined />} />
              <div className="px-4 py-2 rounded-2xl bg-white border border-gray-200">
                <Spin size="small" /> <Text type="secondary" className="ml-2">思考中...</Text>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="p-3 border-t bg-gray-50 flex-shrink-0">
          {mode === MODES.REVISE && (
            <div className="mb-2">
              <Select
                size="small"
                value={reviseType}
                onChange={setReviseType}
                className="!w-32"
                options={[
                  { label: '润色', value: 'polish' },
                  { label: '翻译', value: 'translate' },
                  { label: '精简', value: 'shorten' },
                  { label: '扩展', value: 'expand' },
                ]}
              />
              <Text type="secondary" className="ml-2 text-xs">选择修改类型</Text>
            </div>
          )}
          {mode === MODES.REVISE && (
            <TextArea
              placeholder="粘贴要修改的原文（可选，提供上下文可获得更好的结果）..."
              rows={2}
              value={contextText}
              onChange={(e) => setContextText(e.target.value)}
              className="mb-2 !text-sm"
            />
          )}
          <Space.Compact className="w-full">
            <Input
              placeholder={mode === MODES.WRITE ? "输入选题或写作要求..." : "输入修改要求或直接发送要修改的内容..."}
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
          <div className="flex justify-between items-center mt-2">
            <Text type="secondary" className="text-xs">
              {!selectedPaperId ? '请先选择论文项目' : `当前模式：${MODE_CONFIG[mode].label}`}
            </Text>
            <Button type="text" size="small" icon={<ClearOutlined />} onClick={handleClearChat}>
              清空对话
            </Button>
          </div>
        </div>
      </Card>

      {/* 右侧：当前论文信息 */}
      <Card
        className="w-64 flex-shrink-0 !rounded-lg"
        title={
          <Space>
            <FileTextOutlined className="text-purple-500" />
            <span className="text-sm">当前论文</span>
          </Space>
        }
        bodyStyle={{ padding: 0, maxHeight: 'calc(100vh - 180px)', overflow: 'auto' }}
      >
        {selectedPaper ? (
          <div className="p-3">
            <Text strong className="text-sm block mb-2">{selectedPaper.title}</Text>
            <Text type="secondary" className="text-xs block mb-2">
              章节：{selectedPaper.sections?.length || 0} 个
            </Text>
            <Divider className="!my-2" />
            <Text strong className="text-xs">快速导航</Text>
            <div className="mt-2 space-y-1">
              <Button type="link" size="small" className="!p-0 !h-auto text-xs" icon={<EditOutlined />} onClick={() => window.location.href = '/writing'}>
                前往写作
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-4 text-center">
            <Text type="secondary" className="text-xs">未选择论文</Text>
            <div className="mt-2">
              <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                新建论文
              </Button>
            </div>
          </div>
        )}
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