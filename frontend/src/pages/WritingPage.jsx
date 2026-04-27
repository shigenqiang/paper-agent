import React, { useState } from 'react'
import { Card, Button, Space, Typography, Tabs, Tree, Input, Divider, Empty, Tag, Tooltip } from 'antd'
import {
  PlusOutlined,
  SaveOutlined,
  AlignLeftOutlined,
  NodeIndexOutlined,
  CommentOutlined,
  FullscreenOutlined,
  CompressOutlined,
} from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'

const { Title, Text } = Typography
const { TextArea } = Input

const WritingPage = () => {
  const { project, updateSection } = usePaperStore()
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [aiPanelExpanded, setAiPanelExpanded] = useState(true)

  // 大纲树形结构
  const outlineData = [
    {
      title: '第1章 引言',
      key: '1',
      children: [
        { title: '1.1 研究背景', key: '1-1' },
        { title: '1.2 研究意义', key: '1-2' },
        { title: '1.3 研究目标', key: '1-3' },
      ],
    },
    {
      title: '第2章 文献综述',
      key: '2',
      children: [
        { title: '2.1 国内研究现状', key: '2-1' },
        { title: '2.2 国外研究现状', key: '2-2' },
      ],
    },
    { title: '第3章 研究方法', key: '3' },
    { title: '第4章 实验结果', key: '4' },
    { title: '第5章 讨论', key: '5' },
    { title: '第6章 结论', key: '6' },
  ]

  // AI助手消息
  const [messages, setMessages] = useState([
    { role: 'user', content: '请帮我生成关于深度学习的研究大纲' },
    { role: 'assistant', content: '好的，我来为您生成深度学习的研究大纲。\n\n1. 引言\n   - 深度学习的发展历程\n   - 研究背景与意义\n\n2. 相关工作\n   - CNN在图像领域的应用\n   - RNN在序列数据中的应用\n\n3. 方法\n   - 数据预处理\n   - 模型设计\n   - 训练策略\n\n4. 实验\n   - 数据集描述\n   - 对比实验\n\n5. 结论与展望' },
  ])
  const [inputValue, setInputValue] = useState('')

  const handleSend = () => {
    if (!inputValue.trim()) return

    setMessages([...messages, { role: 'user', content: inputValue }])
    setInputValue('')

    // 模拟AI响应
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '正在为您处理，请稍候...'
      }])
    }, 500)
  }

  return (
    <div className={`h-full flex flex-col ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      {/* 顶部工具栏 */}
      <div className="flex justify-between items-center mb-4">
        <Space>
          <Button type="primary" icon={<PlusOutlined />}>新建章节</Button>
          <Button icon={<SaveOutlined />}>保存</Button>
        </Space>

        <Space>
          <Tooltip title={isFullscreen ? '退出全屏' : '全屏模式'}>
            <Button
              icon={isFullscreen ? <CompressOutlined /> : <FullscreenOutlined />}
              onClick={() => setIsFullscreen(!isFullscreen)}
            />
          </Tooltip>
        </Space>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* 左侧大纲 */}
        <Card className="w-64 flex-shrink-0" title="论文大纲">
          <Tree
            treeData={outlineData}
            defaultExpandAll
            draggable
            blockNode
            className="mb-4"
          />
          <Button type="link" icon={<PlusOutlined />} className="!p-0">
            添加章节
          </Button>
        </Card>

        {/* 中间写作区 */}
        <Card className="flex-1 flex flex-col min-w-0" bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="flex items-center justify-between mb-4">
            <Title level={4} className="!mb-0">1.1 研究背景</Title>
            <Tag color="blue">自动保存中</Tag>
          </div>

          <TextArea
            className="flex-1 !min-h-0"
            placeholder="开始写作..."
            variant="borderless"
            style={{
              resize: 'none',
              fontSize: '16px',
              lineHeight: '1.8',
            }}
            value={`深度学习是机器学习的一个分支，它基于人工神经网络，通过模拟人脑神经元的连接方式来实现对数据的学习和理解。

近年来，深度学习在计算机视觉、自然语言处理、语音识别等领域取得了显著的突破。卷积神经网络（CNN）在图像分类任务中的准确率已经超过了人类水平，循环神经网络（RNN）在序列数据处理方面也展现了强大的能力。

本研究聚焦于深度学习技术在医学影像诊断中的应用，旨在通过深度学习算法提高疾病检测的准确性和效率。`}
            onChange={(e) => updateSection('1-1', e.target.value)}
          />

          <Divider className="!my-4" />

          <div className="flex justify-between items-center text-sm text-gray-500">
            <span>字数: 156</span>
            <span>引用: 3</span>
            <span>更新时间: 刚刚</span>
          </div>
        </Card>

        {/* 右侧引用面板 */}
        <Card className="w-64 flex-shrink-0" title="当前引用">
          <div className="space-y-3">
            <div className="p-3 bg-gray-50 rounded">
              <Text className="text-xs text-gray-500">[1] Smith et al. (2023)</Text>
              <div className="text-sm">Deep Learning in Medical Imaging</div>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <Text className="text-xs text-gray-500">[2] Zhang & Chen (2022)</Text>
              <div className="text-sm">CNN for Image Classification</div>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <Text className="text-xs text-gray-500">[3] Wang (2021)</Text>
              <div className="text-sm">Review of Deep Learning</div>
            </div>
          </div>
          <Button type="link" icon={<PlusOutlined />} className="!mt-2 !p-0">
            添加引用
          </Button>
        </Card>
      </div>

      {/* AI助手面板 */}
      {aiPanelExpanded && (
        <Card className="mt-4" bodyStyle={{ padding: 0 }}>
          <div className="flex items-center justify-between px-4 py-2 border-b">
            <Space>
              <CommentOutlined />
              <span>AI助手</span>
            </Space>
            <Button type="text" size="small" onClick={() => setAiPanelExpanded(false)}>
              收起
            </Button>
          </div>

          <div className="h-64 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2 p-4 border-t">
            <TextArea
              className="flex-1"
              placeholder="输入您的问题或指令..."
              autoSize={{ minRows: 1, maxRows: 3 }}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <Button type="primary" onClick={handleSend}>发送</Button>
          </div>
        </Card>
      )}

      {/* AI面板折叠时显示按钮 */}
      {!aiPanelExpanded && (
        <Button
          type="text"
          className="mt-4 w-full"
          icon={<CommentOutlined />}
          onClick={() => setAiPanelExpanded(true)}
        >
          展开AI助手
        </Button>
      )}
    </div>
  )
}

export default WritingPage