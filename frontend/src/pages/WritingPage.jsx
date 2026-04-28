import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Tree, Input, Divider, Tag, Tooltip, message, Modal, Progress, Badge, Empty, Spin, Avatar, notification } from 'antd'
import {
  PlusOutlined,
  SaveOutlined,
  EditOutlined,
  BookOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  FullscreenOutlined,
  CompressOutlined,
  DeleteOutlined,
  RobotOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  CloudUploadOutlined,
  DragOutlined,
  AimOutlined,
  KeyOutlined,
  UndoOutlined,
  RedoOutlined,
} from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'
import { paperAPI } from '../services/api'
import { useLocation, useNavigate } from 'react-router-dom'

const { Title, Text } = Typography
const { TextArea } = Input
const { confirm } = Modal

// 默认章节
const DEFAULT_SECTIONS = [
  { id: '1', title: '第1章 引言', parentId: null, content: '' },
  { id: '1-1', title: '1.1 研究背景', parentId: '1', content: '' },
  { id: '1-2', title: '1.2 研究意义', parentId: '1', content: '' },
  { id: '1-3', title: '1.3 研究目标', parentId: '1', content: '' },
  { id: '2', title: '第2章 文献综述', parentId: null, content: '' },
  { id: '2-1', title: '2.1 国内研究现状', parentId: '2', content: '' },
  { id: '2-2', title: '2.2 国外研究现状', parentId: '2', content: '' },
  { id: '3', title: '第3章 研究方法', parentId: null, content: '' },
  { id: '4', title: '第4章 实验结果', parentId: null, content: '' },
  { id: '5', title: '第5章 讨论', parentId: null, content: '' },
  { id: '6', title: '第6章 结论', parentId: null, content: '' },
]

// 快捷键提示
const SHORTCUTS = [
  { key: 'Ctrl + S', action: '保存' },
  { key: 'Ctrl + Z', action: '撤销' },
  { key: 'Ctrl + Shift', action: '重做' },
  { key: 'Ctrl + Enter', action: 'AI续写' },
]

const WritingPage = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { project, updateSection, addSection, deleteSection, setProject, setTitle } = usePaperStore()
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [selectedSection, setSelectedSection] = useState('1-1')
  const [sectionContent, setSectionContent] = useState('')
  const [paperTitle, setPaperTitle] = useState(project?.title || '未命名论文')
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [generatingContent, setGeneratingContent] = useState(false)
  const [saveStatus, setSaveStatus] = useState('saved') // saved, saving, unsaved
  const [lastSaved, setLastSaved] = useState(null)
  const autoSaveTimer = useRef(null)

  // 从导航状态获取论文ID并加载论文
  useEffect(() => {
    const paperId = location.state?.paperId
    if (paperId) {
      loadPaper(paperId)
    }
  }, [location.state])

  // 当store中的project变化时，同步到组件状态
  useEffect(() => {
    if (project?.title) {
      setPaperTitle(project.title)
    }
    if (project?.sections?.length > 0) {
      const currentExists = project.sections.some(s => s.id === selectedSection)
      if (!currentExists) {
        setSelectedSection(project.sections[0].id)
        setSectionContent(project.sections[0].content || '')
      }
    }
  }, [project])

  // 自动保存
  useEffect(() => {
    if (saveStatus === 'unsaved') {
      autoSaveTimer.current = setTimeout(() => {
        handleSave()
      }, 30000) // 30秒自动保存
    }
    return () => {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current)
      }
    }
  }, [saveStatus])

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault()
        handleSave()
        notification.success({ message: '已保存', duration: 1 })
      }
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault()
        handleGenerateContent()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedSection, sectionContent])

  const loadPaper = async (paperId) => {
    try {
      const response = await paperAPI.getPaper(paperId)
      if (response.success && response.data) {
        const paperData = response.data
        if (paperData.outline && paperData.outline.length > 0 && !paperData.sections) {
          paperData.sections = paperData.outline
        }
        setProject(paperData)
        setPaperTitle(paperData.title || '未命名论文')
        if (paperData.sections && paperData.sections.length > 0) {
          setSelectedSection(paperData.sections[0].id)
          setSectionContent(paperData.sections[0].content || '')
        }
      }
    } catch (e) {
      console.error('加载论文失败:', e)
    }
  }

  const currentPaperId = project?.id || 'test-paper-id'
  const sections = project?.sections?.length > 0 ? project.sections : DEFAULT_SECTIONS

  // 大纲树形结构
  const outlineData = useMemo(() => {
    const roots = sections.filter(s => !s.parentId && !s.id.includes('-'))
    return roots.map(root => ({
      title: root.title,
      key: root.id,
      icon: <FileTextOutlined />,
      children: sections
        .filter(s => s.id.includes('-') && s.id.startsWith(root.id))
        .map(s => ({ title: s.title, key: s.id, isLeaf: true }))
    }))
  }, [sections])

  const getSectionContent = (sectionId) => {
    const section = sections.find(s => s.id === sectionId)
    return section?.content || ''
  }

  const handleOutlineSelect = (selectedKeys) => {
    if (selectedKeys.length > 0) {
      const key = selectedKeys[0]
      setSelectedSection(key)
      setSectionContent(getSectionContent(key))
    }
  }

  const handleAddSection = () => {
    const parentKeys = outlineData.map(d => d.key)
    const lastParent = parentKeys[parentKeys.length - 1] || '1'
    const newParentNum = parseInt(lastParent) + 1
    const newId = String(newParentNum)
    const newTitle = `第${newParentNum}章 新章节`

    addSection({ id: newId, title: newTitle, content: '', parentId: null })
    setSelectedSection(newId)
    setSectionContent('')
    message.success('已添加新章节')
  }

  const handleDeleteSection = (sectionId) => {
    confirm({
      title: '确认删除',
      content: '确定要删除这个章节吗？',
      onOk() {
        deleteSection(sectionId)
        const remaining = sections.filter(s => s.id !== sectionId)
        if (remaining.length > 0) {
          setSelectedSection(remaining[0].id)
          setSectionContent(remaining[0].content || '')
        }
        message.success('章节已删除')
      }
    })
  }

  const handleContentChange = (content) => {
    setSectionContent(content)
    updateSection(selectedSection, content)
    setSaveStatus('unsaved')
  }

  const handleSave = async () => {
    setSaveStatus('saving')
    try {
      if (project?.id) {
        await paperAPI.updatePaper(project.id, {
          title: paperTitle,
          sections: sections
        })
      }
      setSaveStatus('saved')
      setLastSaved(new Date())
    } catch (e) {
      setSaveStatus('unsaved')
      message.error('保存失败')
    }
  }

  const handleGenerateOutline = async () => {
    if (!paperTitle) {
      message.warning('请先设置论文标题')
      return
    }
    setGeneratingOutline(true)
    try {
      const response = await fetch(`http://localhost:8000/api/papers/${currentPaperId}/outline/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-api-key' },
        body: JSON.stringify({ topic: paperTitle })
      })
      const result = await response.json()
      if (result.success) {
        message.success('大纲已生成！')
      } else {
        throw new Error(result.error)
      }
    } catch (e) {
      message.error('生成大纲失败')
    } finally {
      setGeneratingOutline(false)
    }
  }

  const handleGenerateContent = async () => {
    if (!selectedSection) {
      message.warning('请先选择要生成的章节')
      return
    }
    setGeneratingContent(true)
    try {
      const response = await fetch(`http://localhost:8000/api/papers/${currentPaperId}/sections/${selectedSection}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-api-key' },
        body: JSON.stringify({ prompt: `为"${selectedSection}"章节生成内容` })
      })
      const result = await response.json()
      if (result.success) {
        const content = result.data?.content || ''
        setSectionContent(content)
        updateSection(selectedSection, content)
        message.success('内容已生成！')
      } else {
        throw new Error(result.error)
      }
    } catch (e) {
      message.error('生成内容失败')
    } finally {
      setGeneratingContent(false)
    }
  }

  const currentSectionTitle = sections.find(s => s.id === selectedSection)?.title || selectedSection
  const totalWords = sections.reduce((acc, s) => acc + (s.content?.length || 0), 0)
  const currentWords = sectionContent.length

  // 保存状态图标
  const getSaveStatusIcon = () => {
    if (saveStatus === 'saving') return <LoadingOutlined className="text-blue-500" />
    if (saveStatus === 'saved') return <CheckCircleOutlined className="text-green-500" />
    return <ClockCircleOutlined className="text-orange-500" />
  }

  return (
    <div className={`h-full flex flex-col ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      {/* 顶部工具栏 */}
      <Card size="small" className="mb-3 !rounded-lg" bodyStyle={{ padding: '12px 16px' }}>
        <div className="flex justify-between items-center">
          <Space size="middle">
            <Input
              value={paperTitle}
              onChange={(e) => {
                setPaperTitle(e.target.value)
                setSaveStatus('unsaved')
              }}
              placeholder="论文标题"
              className="!w-56"
              variant="borderless"
              disabled={generatingContent || generatingOutline}
            />
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saveStatus === 'saving'}
              disabled={generatingContent || generatingOutline}
            >
              保存
            </Button>
          </Space>

          <Space size="middle">
            <Tooltip title="生成大纲（AI分析论文结构）">
              <Button
                icon={<ThunderboltOutlined />}
                onClick={handleGenerateOutline}
                loading={generatingOutline}
                disabled={generatingContent}
              >
                生成大纲
              </Button>
            </Tooltip>
            <Tooltip title="AI续写当前章节（Ctrl+Enter）">
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={handleGenerateContent}
                loading={generatingContent}
                disabled={generatingOutline}
              >
                AI续写
              </Button>
            </Tooltip>
            <Button
              icon={<SearchOutlined />}
              onClick={() => navigate('/literature')}
            >
              文献搜索
            </Button>
          </Space>

          <Space size="small">
            {/* 快捷键提示 */}
            <Tooltip title={
              <div>
                <div className="font-bold mb-1">快捷键</div>
                {SHORTCUTS.map(s => (
                  <div key={s.key} className="text-xs">{s.key} - {s.action}</div>
                ))}
              </div>
            }>
              <Button icon={<KeyOutlined />} type="text" className="text-gray-400" />
            </Tooltip>
            <Space size="small" className="text-gray-400 text-sm">
              {getSaveStatusIcon()}
              <span>{saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '已保存' : '未保存'}</span>
              {lastSaved && <span className="text-xs">| {lastSaved.toLocaleTimeString()}</span>}
            </Space>
            <Tooltip title={isFullscreen ? '退出全屏' : '全屏模式'}>
              <Button
                icon={isFullscreen ? <CompressOutlined /> : <FullscreenOutlined />}
                onClick={() => setIsFullscreen(!isFullscreen)}
              />
            </Tooltip>
          </Space>
        </div>
      </Card>

      {/* 主内容区 - 三栏布局 */}
      <div className="flex-1 flex gap-3 min-h-0">
        {/* 左侧大纲 */}
        <Card
          className="w-64 flex-shrink-0 !rounded-lg"
          title={
            <Space>
              <FileTextOutlined />
              <span>论文大纲</span>
            </Space>
          }
          extra={
            <Button type="text" size="small" icon={<PlusOutlined />} onClick={handleAddSection}>
              添加
            </Button>
          }
          bodyStyle={{ padding: 0, overflow: 'auto' }}
        >
          <div className="p-2">
            <Tree
              treeData={outlineData}
              selectedKeys={[selectedSection]}
              onSelect={handleOutlineSelect}
              defaultExpandAll
              blockNode
              showIcon
              className="outline-tree"
            />
          </div>
          <Divider className="my-0" />
          <div className="p-2">
            <Space>
              <Button type="text" size="small" icon={<DeleteOutlined />} danger onClick={() => handleDeleteSection(selectedSection)}>
                删除
              </Button>
            </Space>
          </div>
        </Card>

        {/* 中间写作区 */}
        <Card
          className="flex-1 flex flex-col min-w-0 !rounded-lg"
          title={
            <Space>
              <EditOutlined />
              <span>{currentSectionTitle}</span>
              <Tag color="blue" className="ml-2">{currentWords} 字</Tag>
            </Space>
          }
          extra={
            <Badge status="processing" text={<Text type="secondary" className="text-xs">自动保存</Text>} />
          }
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
        >
          <TextArea
            className="flex-1 !min-h-0 !border-0 !rounded-none"
            placeholder="开始写作... 或点击上方「AI续写」让AI帮您生成内容"
            style={{
              resize: 'none',
              fontSize: '15px',
              lineHeight: '1.8',
              padding: '16px 20px',
            }}
            value={sectionContent}
            onChange={(e) => handleContentChange(e.target.value)}
          />

          {/* 底部状态栏 */}
          <div className="flex justify-between items-center px-4 py-2 border-t border-gray-100 bg-gray-50 text-xs text-gray-400">
            <Space>
              <span>总字数: {totalWords}</span>
              <Divider type="vertical" />
              <span>当前: {currentWords} 字</span>
            </Space>
            <Space>
              <span>更新: {new Date().toLocaleTimeString()}</span>
            </Space>
          </div>
        </Card>

        {/* 右侧引用面板 */}
        <Card
          className="w-64 flex-shrink-0 !rounded-lg"
          title={
            <Space>
              <BookOutlined />
              <span>引用管理</span>
            </Space>
          }
          extra={
            <Button type="text" size="small" icon={<SearchOutlined />} onClick={() => navigate('/literature')}>
              搜索
            </Button>
          }
          bodyStyle={{ padding: 0 }}
        >
          <div className="p-3">
            <Empty
              description="暂无引用"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              className="py-6"
            />
          </div>
          <Divider className="my-0" />
          <div className="p-2">
            <Button block icon={<PlusOutlined />} className="mb-2">
              添加引用
            </Button>
            <Button block icon={<CloudUploadOutlined />} type="dashed">
              导入文献
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default WritingPage
