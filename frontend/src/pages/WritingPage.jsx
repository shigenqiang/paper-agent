import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Tree, Input, Divider, Tag, Tooltip, message, Modal, Progress, Badge, Empty, Spin, Avatar, notification, List, Select, Upload, Segmented } from 'antd'
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
    ClockCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  CloudUploadOutlined,
  DragOutlined,
  AimOutlined,
  KeyOutlined,
  UndoOutlined,
  RedoOutlined,
  CopyOutlined,
  FileAddOutlined,
  FilePdfOutlined,
  FileMarkdownOutlined,
  InboxOutlined,
  EyeOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'
import { paperAPI, literatureAPI } from '../services/api'
import { useLocation, useNavigate } from 'react-router-dom'
import MarkdownEditor from '@uiw/react-md-editor'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

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
  { key: 'Ctrl + Enter', action: '修正格式' },
]

const WritingPage = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { project, updateSection, addSection, deleteSection, setProject, setTitle, literature, addCitation, removeCitation } = usePaperStore()
  const [papers, setPapers] = useState([])
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [selectedSection, setSelectedSection] = useState('1-1')
  const [sectionContent, setSectionContent] = useState('')
  const [paperTitle, setPaperTitle] = useState(project?.title || '未命名论文')
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [generatingContent, setGeneratingContent] = useState(false)
  const [saveStatus, setSaveStatus] = useState('saved') // saved, saving, unsaved
  const [lastSaved, setLastSaved] = useState(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploadingFile, setUploadingFile] = useState(null)
  const [newPaperTitle, setNewPaperTitle] = useState('')
  const autoSaveTimer = useRef(null)
  const leftScrollRef = useRef(null)
  const rightScrollRef = useRef(null)
  const [isSyncingScroll, setIsSyncingScroll] = useState(false)
  const [showCiteModal, setShowCiteModal] = useState(false)
  const [citeStyle, setCiteStyle] = useState('APA')
  const [editorMode, setEditorMode] = useState('split') // 'edit' | 'preview' | 'split' | 'unified'
  const [showFullPreview, setShowFullPreview] = useState(false)
  const [showFullEdit, setShowFullEdit] = useState(false)
  const [fullEditContent, setFullEditContent] = useState({}) // { sectionId: content }
  const [unifiedContent, setUnifiedContent] = useState('') // 合并后的全文

  // 加载论文列表
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

  // 创建论文
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
        setProject(response.data)
        setIsCreateModalOpen(false)
        setNewPaperTitle('')
        message.success('论文创建成功')
      }
    } catch (e) {
      message.error('创建论文失败')
    }
  }

  // 处理文件选择
  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setUploadingFile(file)
    }
  }

  // 上传论文文件
  const handleUploadPaper = async () => {
    if (!uploadingFile) {
      message.warning('请选择要上传的文件')
      return
    }
    try {
      const formData = new FormData()
      formData.append('file', uploadingFile)
      console.log('开始上传文件:', uploadingFile.name, uploadingFile.size)
      const response = await paperAPI.uploadPaper(formData)
      console.log('上传响应:', response)
      if (response.success && response.data) {
        // 处理上传返回的数据：后端返回的content是完整文本，sections只有标题
        const paperData = response.data
        if (paperData.content && (!paperData.sections || paperData.sections.length === 0)) {
          // 如果有完整文本但sections为空，创建单个章节包含全部内容
          paperData.sections = [{
            id: '1',
            title: paperData.title || '全文',
            content: paperData.content,
            parentId: null
          }]
        } else if (paperData.content && paperData.sections && paperData.sections.length > 0) {
          // 如果有完整文本也有sections，尝试按章节分割内容
          const sections = paperData.sections
          const content = paperData.content
          // 简单按 ## 标题分割
          const sectionTitles = sections.map(s => s.title).filter(Boolean)
          if (sectionTitles.length > 0) {
            const parts = content.split(/#{2,3}\s+/).filter(p => p.trim())
            if (parts.length >= sectionTitles.length) {
              sections.forEach((section, idx) => {
                section.content = parts[idx] || ''
              })
            } else {
              // 分割失败，整个内容放第一个章节
              sections[0].content = content
            }
          }
          paperData.sections = sections
        }
        setPapers(prev => [paperData, ...prev])
        setProject(paperData)
        setIsUploadModalOpen(false)
        setUploadingFile(null)
        message.success('论文上传成功')
      } else {
        message.error('上传失败: ' + (response.error || '未知错误'))
      }
    } catch (e) {
      console.error('上传错误:', e)
      message.error('上传论文失败: ' + (e.message || '网络错误'))
    }
  }

  // 从导航状态获取论文ID并加载论文
  useEffect(() => {
    const paperId = location.state?.paperId
    if (paperId) {
      loadPaper(paperId)
    } else if (!project?.id && papers.length > 0) {
      // 没有选中论文时，不自动加载第一个
    }
  }, [location.state, papers])

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
    if (!project?.id) {
      message.warning('请先创建或选择论文')
      return
    }
    setGeneratingOutline(true)
    try {
      const result = await paperAPI.generateOutline(project.id, paperTitle)
      if (result.success && result.data) {
        let newSections = []
        const outlineData = result.data.outline || result.data
        if (Array.isArray(outlineData)) {
          outlineData.forEach(item => {
            newSections.push({
              id: String(item.id || item.key || newSections.length + 1),
              title: item.title || item.name || '',
              parentId: null,
              content: ''
            })
            if (item.children && item.children.length > 0) {
              const parentId = newSections[newSections.length - 1].id
              item.children.forEach((child, idx) => {
                newSections.push({
                  id: `${parentId}-${idx + 1}`,
                  title: child.title || child.name || '',
                  parentId: parentId,
                  content: ''
                })
              })
            }
            if (item.subsections && item.subsections.length > 0) {
              const parentId = newSections[newSections.length - 1].id
              item.subsections.forEach((child, idx) => {
                newSections.push({
                  id: `${parentId}-${idx + 1}`,
                  title: child.title || child.name || '',
                  parentId: parentId,
                  content: ''
                })
              })
            }
          })
        }
        if (newSections.length > 0) {
          setProject({ ...project, sections: newSections })
          setSelectedSection(newSections[0].id)
          setSectionContent('')
        }
        message.success('大纲已生成！')
      } else {
        message.error(result.error || '生成大纲失败')
      }
    } catch (e) {
      message.error('生成大纲失败: ' + (e.message || '网络错误'))
    } finally {
      setGeneratingOutline(false)
    }
  }

  const handleGenerateContent = async () => {
    if (!project?.id) {
      message.warning('请先创建或选择论文')
      return
    }

    // 确保有章节可以续写
    let targetSection = selectedSection
    const currentSections = project?.sections || []

    if (!targetSection || !currentSections.find(s => s.id === targetSection)) {
      // 检查是否需要添加父章节
      if (!currentSections.find(s => s.id === '1')) {
        addSection({ id: '1', title: '第1章 引言', parentId: null, content: '' })
      }
      // 添加第一个子章节
      const newSection = {
        id: '1-1',
        title: '1.1 研究背景',
        parentId: '1',
        content: ''
      }
      addSection(newSection)
      targetSection = '1-1'
      setSelectedSection(targetSection)
      setSectionContent('')
      message.info('已创建章节：1.1 研究背景')
    }

    setGeneratingContent(true)
    try {
      const currentTitle = currentSections.find(s => s.id === targetSection)?.title || '当前章节'
      const result = await paperAPI.formatContent(project.id, targetSection, sectionContent)
      if (result && result.success && result.data) {
        const content = result.data.content || ''
        setSectionContent(content)
        updateSection(targetSection, content)
        message.success('格式已修正！')
      } else if (result && result.error) {
        message.error('修正格式失败: ' + result.error)
      } else {
        message.error('修正格式失败')
      }
    } catch (e) {
      console.error('修正格式错误:', e)
      message.error('修正格式失败: ' + (e.message || '请检查网络或API配置'))
    } finally {
      setGeneratingContent(false)
    }
  }

  // 引用管理功能
  const handleAddCitation = (record) => {
    addCitation({
      id: record.id,
      title: record.title,
      authors: record.authors,
      year: record.year,
      journal: record.journal,
    })
    message.success(`已引用: ${record.title}`)
  }

  const handleRemoveCitation = (id) => {
    removeCitation(id)
    message.success('引用已移除')
  }

  const handleCopyCitation = async (record) => {
    try {
      const result = await literatureAPI.getCitation(record.id, citeStyle)
      if (result.success && result.data?.citation) {
        navigator.clipboard.writeText(result.data.citation)
        message.success('引用格式已复制')
      }
    } catch (e) {
      const fallback = `${record.authors}. (${record.year || 'n.d.'}). ${record.title}. ${record.journal || ''}`.trim()
      navigator.clipboard.writeText(fallback)
      message.success('引用已复制')
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

  // 未选择论文时的界面
  if (!project?.id) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card className="text-center !rounded-lg w-96">
          <div className="py-8">
            <FileTextOutlined className="text-5xl text-gray-300 mb-4" />
            <Title level={4} className="text-gray-500 mb-4">请选择或创建论文</Title>
            <Text type="secondary" className="block mb-6">
              您还没有选择任何论文，请从列表中选择或创建新论文
            </Text>
            <Space>
              <Select
                placeholder="选择论文"
                className="!w-48"
                onChange={(paperId) => {
                  const paper = papers.find(p => p.id === paperId)
                  if (paper) {
                    setProject(paper)
                    setPaperTitle(paper.title || '未命名论文')
                  }
                }}
                options={papers.map(p => ({ label: p.title || '未命名', value: p.id }))}
              />
              <Button type="primary" icon={<FileAddOutlined />} onClick={() => setIsCreateModalOpen(true)}>
                新建论文
              </Button>
              <Button icon={<CloudUploadOutlined />} onClick={() => setIsUploadModalOpen(true)}>
                上传论文
              </Button>
            </Space>
          </div>
        </Card>

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

  return (
    <div className={`h-full flex flex-col ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      {/* 顶部工具栏 */}
      <Card size="small" className="mb-3 !rounded-lg" styles={{ body: { padding: '8px 16px' }}>
        <div className="flex justify-between items-center gap-4">
          {/* 左侧：论文选择 + 操作 */}
          <Space size="middle">
            <Select
              value={project?.id}
              onChange={(paperId) => {
                const paper = papers.find(p => p.id === paperId)
                if (paper) {
                  setProject(paper)
                  setPaperTitle(paper.title || '未命名论文')
                }
              }}
              className="!w-44"
              options={papers.map(p => ({ label: p.title || '未命名', value: p.id }))}
            />
            <Input
              value={paperTitle}
              onChange={(e) => {
                setPaperTitle(e.target.value)
                setSaveStatus('unsaved')
              }}
              placeholder="论文标题"
              className="!w-48"
              variant="borderless"
              disabled={generatingContent || generatingOutline}
            />
            <Space size="small">
              <Tooltip title={saveStatus === 'saved' ? '已保存' : saveStatus === 'saving' ? '保存中...' : '保存'}>
                <Button
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saveStatus === 'saving'}
                  disabled={generatingContent || generatingOutline}
                />
              </Tooltip>
              <Tooltip title="上传论文">
                <Button
                  icon={<CloudUploadOutlined />}
                  onClick={() => setIsUploadModalOpen(true)}
                />
              </Tooltip>
            </Space>
          </Space>

          {/* 中间：AI + 编辑模式 */}
          <Space size="middle">
            <Tooltip title="修正格式（Ctrl+Enter）">
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={handleGenerateContent}
                loading={generatingContent}
              >
                修正格式
              </Button>
            </Tooltip>
            <Segmented
              value={editorMode}
              onChange={(mode) => {
                if (mode === 'unified') {
                  const merged = sections.map(s => `## ${s.title}\n\n${s.content || ''}`).join('\n\n')
                  setUnifiedContent(merged)
                }
                setEditorMode(mode)
              }}
              options={[
                { label: '编辑', value: 'edit' },
                { label: '预览', value: 'preview' },
                { label: '双栏', value: 'split' },
                { label: '全文', value: 'unified' },
              ]}
            />
          </Space>

          {/* 右侧：全局编辑 + 状态 + 全屏 */}
          <Space size="middle">
            <Tooltip title="全局编辑（编辑所有章节）">
              <Button
                icon={<EditOutlined />}
                onClick={() => {
                  const contentMap = {}
                  sections.forEach(s => { contentMap[s.id] = s.content || '' })
                  setFullEditContent(contentMap)
                  setShowFullEdit(true)
                }}
              />
            </Tooltip>
            <Tag color={saveStatus === 'saved' ? 'success' : saveStatus === 'saving' ? 'processing' : 'default'}>
              {saveStatus === 'saved' ? '✓ 已保存' : saveStatus === 'saving' ? '保存中...' : '未保存'}
            </Tag>
            <Tooltip title={isFullscreen ? '退出全屏' : '全屏模式'}>
              <Button
                icon={isFullscreen ? <CompressOutlined /> : <FullscreenOutlined />}
                onClick={() => setIsFullscreen(!isFullscreen)}
                type="text"
              />
            </Tooltip>
          </Space>
        </div>
      </Card>

      {/* 主内容区 - 上下布局 */}
      <div className="flex-1 flex flex-col gap-3 min-h-0">
        {/* 上部：左侧大纲 + 中间写作区 */}
        <div className="flex-1 flex gap-3 min-h-0" style={{ minHeight: '1000px' }}>
          {/* 左侧大纲 */}
          <Card
            className="w-56 flex-shrink-0 !rounded-lg"
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
            styles={{ body: { padding: 0, overflow: 'auto' }}
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
                <Button type="text" size="small" icon={<RightOutlined />} onClick={() => {
                  const currentIndex = sections.findIndex(s => s.id === selectedSection)
                  if (currentIndex < sections.length - 1) {
                    const nextSection = sections[currentIndex + 1]
                    setSelectedSection(nextSection.id)
                    setSectionContent(nextSection.content || '')
                  } else {
                    message.info('已到达最后一章')
                  }
                }}>
                  下一章
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
            styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}
          >
            <div className="flex-1 flex min-h-0">
              {/* 左侧编辑区 */}
              {editorMode !== 'preview' && (
                <div
                  ref={leftScrollRef}
                  className={`flex-1 flex flex-col min-w-0 ${editorMode === 'split' || editorMode === 'unified' ? 'border-r border-gray-200' : ''} overflow-auto`}
                  onScroll={(e) => {
                    if (isSyncingScroll) return
                    setIsSyncingScroll(true)
                    if (rightScrollRef.current) {
                      rightScrollRef.current.scrollTop = e.target.scrollTop
                    }
                    setTimeout(() => setIsSyncingScroll(false), 50)
                  }}
                >
                  {editorMode === 'unified' ? (
                    <TextArea
                      className="flex-1 !border-0 !rounded-none !resize-none"
                      placeholder="全文编辑模式..."
                      style={{
                        fontSize: '15px',
                        lineHeight: '1.8',
                        padding: '16px 20px',
                      }}
                      value={unifiedContent}
                      onChange={(e) => setUnifiedContent(e.target.value)}
                    />
                  ) : (
                    <TextArea
                      className="flex-1 !border-0 !rounded-none !resize-none"
                      placeholder="开始写作... 或点击上方「修正格式」让AI帮您生成内容"
                      style={{
                        fontSize: '15px',
                        lineHeight: '1.8',
                        padding: '16px 20px',
                      }}
                      value={sectionContent}
                      onChange={(e) => handleContentChange(e.target.value)}
                    />
                  )}
                </div>
              )}
              {/* 右侧预览区 */}
              {editorMode !== 'edit' && (
                <div
                  ref={rightScrollRef}
                  className="flex-1 overflow-auto bg-white"
                  style={{ padding: '16px 20px' }}
                  onScroll={(e) => {
                    if (isSyncingScroll) return
                    setIsSyncingScroll(true)
                    if (leftScrollRef.current) {
                      leftScrollRef.current.scrollTop = e.target.scrollTop
                    }
                    setTimeout(() => setIsSyncingScroll(false), 50)
                  }}
                >
                  <div className="markdown-body">
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {editorMode === 'unified' ? unifiedContent : sectionContent}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>

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
        </div>

        {/* 下部：引用管理 */}
        <Card
          className="!rounded-lg"
          title={
            <Space>
              <BookOutlined />
              <span>引用管理</span>
            </Space>
          }
          styles={{ body: { padding: 0 }}
        >
          <div className="flex items-center gap-4 px-4 py-3">
            <Select
              size="small"
              value={citeStyle}
              onChange={setCiteStyle}
              options={[
                { label: 'APA', value: 'APA' },
                { label: 'MLA', value: 'MLA' },
                { label: 'IEEE', value: 'IEEE' },
                { label: 'GB/T 7714', value: 'GB/T 7714' },
              ]}
              className="w-28"
            />
            <div className="flex-1">
              {project?.citations?.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {project.citations.map((cite) => (
                    <Tag
                      key={cite.id}
                      closable
                      onClose={() => handleRemoveCitation(cite.id)}
                      className="py-1"
                    >
                      {cite.title} ({cite.year || 'n.d.'})
                    </Tag>
                  ))}
                </div>
              ) : (
                <Text type="secondary">暂无引用</Text>
              )}
            </div>
            <Button
              size="small"
              icon={<PlusOutlined />}
              onClick={() => setShowCiteModal(true)}
            >
              添加引用
            </Button>
          </div>
        </Card>
      </div>

      {/* 添加引用弹窗 */}
      <Modal
        title="添加引用"
        open={showCiteModal}
        onCancel={() => setShowCiteModal(false)}
        footer={null}
        width={500}
      >
        <Text type="secondary" className="mb-3 block">选择文献库中的论文进行引用：</Text>
        {literature.length === 0 ? (
          <Empty description="暂无可用文献" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={literature}
            className="max-h-80 overflow-auto"
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => { handleAddCitation(item); setShowCiteModal(false) }}
                  >
                    引用
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={<Text strong className="text-sm">{item.title}</Text>}
                  description={
                    <Text type="secondary" className="text-xs" ellipsis>{item.authors}</Text>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

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

      {/* 上传论文弹窗 */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined className="text-blue-500" />
            <span>上传论文</span>
          </Space>
        }
        open={isUploadModalOpen}
        onCancel={() => {
          setIsUploadModalOpen(false)
          setUploadingFile(null)
        }}
        footer={null}
        width={480}
      >
        <div className="py-4">
          <Upload.Dragger
            accept=".pdf,.md,.txt,.docx"
            showUploadList={false}
            beforeUpload={(file) => {
              setUploadingFile(file)
              return false // 阻止自动上传
            }}
            className="mb-4"
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p className="ant-upload-hint">
              支持 PDF、Markdown (.md)、TXT、DOCX 格式
            </p>
          </Upload.Dragger>

          {uploadingFile && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  {uploadingFile.name.endsWith('.pdf') ? (
                    <FilePdfOutlined style={{ fontSize: 20, color: '#e84a25' }} />
                  ) : uploadingFile.name.endsWith('.md') ? (
                    <FileMarkdownOutlined style={{ fontSize: 20, color: '#3b82f6' }} />
                  ) : (
                    <FileTextOutlined style={{ fontSize: 20, color: '#666' }} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <Text strong ellipsis className="block">{uploadingFile.name}</Text>
                  <Text type="secondary" className="text-xs">
                    {(uploadingFile.size / 1024).toFixed(1)} KB
                  </Text>
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <Button
                  type="primary"
                  icon={<CloudUploadOutlined />}
                  onClick={handleUploadPaper}
                  block
                  size="large"
                >
                  上传论文
                </Button>
                <Button
                  onClick={() => {
                    setIsUploadModalOpen(false)
                    setUploadingFile(null)
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* 全局预览弹窗 */}
      <Modal
        title={
          <Space>
            <EyeOutlined className="text-blue-500" />
            <span>全局预览 - {paperTitle}</span>
          </Space>
        }
        open={showFullPreview}
        onCancel={() => setShowFullPreview(false)}
        footer={[
          <Button key="close" onClick={() => setShowFullPreview(false)}>
            关闭
          </Button>,
          <Button
            key="copy"
            icon={<CopyOutlined />}
            onClick={() => {
              const allContent = sections.map(s => `# ${s.title}\n\n${s.content || ''}`).join('\n\n---\n\n')
              navigator.clipboard.writeText(allContent)
              message.success('已复制全文到剪贴板')
            }}
          >
            复制全文
          </Button>,
        ]}
        width="90vw"
        style={{ top: 20 }}
        styles={{ body: { maxHeight: 'calc(100vh - 200px)', overflow: 'auto' }}
      >
        <div className="bg-gray-50 p-4 rounded-lg">
          {sections.map((section) => (
            <div key={section.id} className="mb-6 bg-white p-6 rounded-lg shadow-sm">
              <h2 className="text-xl font-bold mb-4 text-blue-600">{section.title}</h2>
              <div className="markdown-body">
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {section.content || '*（此章节暂无内容）*'}
                </ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      </Modal>

      {/* 全局编辑弹窗 - 左右分栏：编辑 + 预览 */}
      <Modal
        title={
          <Space>
            <EditOutlined className="text-blue-500" />
            <span>全局编辑 - {paperTitle}</span>
          </Space>
        }
        open={showFullEdit}
        onCancel={() => setShowFullEdit(false)}
        footer={[
          <Button key="cancel" onClick={() => setShowFullEdit(false)}>
            取消
          </Button>,
          <Button
            key="save"
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => {
              Object.entries(fullEditContent).forEach(([sectionId, content]) => {
                updateSection(sectionId, content)
              })
              setSaveStatus('unsaved')
              setShowFullEdit(false)
              message.success('已保存所有章节')
            }}
          >
            保存全部
          </Button>,
        ]}
        width="95vw"
        style={{ top: 10 }}
        styles={{ body: { maxHeight: 'calc(100vh - 180px)', overflow: 'hidden', padding: 0 }}
      >
        <div className="flex h-full" style={{ minHeight: 'calc(100vh - 250px)' }}>
          {/* 左侧：所有章节编辑区 */}
          <div className="flex-1 overflow-auto border-r border-gray-200 p-4" style={{ backgroundColor: '#fafafa' }}>
            <div className="space-y-4">
              {sections.map((section) => (
                <Card key={section.id} size="small" title={section.title} className="!rounded-lg" styles={{ body: { padding: 0 }}>
                  <Input.TextArea
                    value={fullEditContent[section.id] || ''}
                    onChange={(e) => setFullEditContent(prev => ({
                      ...prev,
                      [section.id]: e.target.value
                    }))}
                    placeholder={`请输入 ${section.title} 的内容...`}
                    autoSize={{ minRows: 3, maxRows: 10 }}
                    style={{ fontSize: '14px', lineHeight: '1.8', border: 'none' }}
                  />
                </Card>
              ))}
            </div>
          </div>
          {/* 右侧：全局预览区 */}
          <div className="flex-1 overflow-auto bg-white p-6">
            <div className="space-y-6">
              {sections.map((section) => (
                <div key={section.id} className="mb-6">
                  <h2 className="text-xl font-bold mb-3 text-blue-600 border-b border-gray-200 pb-2">{section.title}</h2>
                  <div className="markdown-body">
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {fullEditContent[section.id] || '*（此章节暂无内容）*'}
                    </ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default WritingPage
