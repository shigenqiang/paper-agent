import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Tree, Input, Divider, Tag, Tooltip, message, Modal, Progress, Badge, Empty, Spin, Avatar, notification, List, Select, Upload, Segmented, App, Alert } from 'antd'
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
  AimOutlined,
  CopyOutlined,
  FileAddOutlined,
  InboxOutlined,
  RightOutlined,
  MenuOutlined,
} from '@ant-design/icons'
import { useProjectStore } from '../store/projectStore'
import { useLiteratureStore } from '../store/literatureStore'
import { useWritingStore } from '../store/writingStore'
import { paperAPI, literatureAPI } from '../services/api'
import { useLocation } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { DEFAULT_SECTIONS } from '../constants/paper'
import { UploadPaperModal } from '../components/writing'

const { Title, Text } = Typography
const { TextArea } = Input

// 快捷键提示
const SHORTCUTS = [
  { key: 'Ctrl + S', action: '保存' },
  { key: 'Ctrl + Enter', action: '修正格式' },
]

const WritingPage = () => {
  const location = useLocation()
  const { project, updateSection, addSection, deleteSection, setProject, setTitle, addCitation, removeCitation } = useProjectStore()
  const {
    selectedSection, setSelectedSection,
    sectionContent, setSectionContent,
    paperTitle, setPaperTitle,
    citeStyle, setCiteStyle,
    editorMode, setEditorMode,
    showFullPreview, setShowFullPreview,
    showFullEdit, setShowFullEdit,
  } = useWritingStore()
  const [papers, setPapers] = useState([])
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [generatingContent, setGeneratingContent] = useState(false)
  const [saveStatus, setSaveStatus] = useState('saved')
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
  const [fullEditContent, setFullEditContent] = useState({})
  const [unifiedContent, setUnifiedContent] = useState('')
  const [messageApi, contextHolder] = message.useMessage()

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
      messageApi.warning('请输入论文标题')
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
        messageApi.success('论文创建成功')
      }
    } catch (e) {
      messageApi.error('创建论文失败')
    }
  }

  // 上传论文文件
  const handleUploadPaper = async () => {
    if (!uploadingFile) {
      messageApi.warning('请选择要上传的文件')
      return
    }
    try {
      const formData = new FormData()
      formData.append('file', uploadingFile)
      console.log('开始上传文件:', uploadingFile.name, uploadingFile.size)
      const response = await paperAPI.uploadPaper(formData)
      console.log('上传响应:', response)
      if (response.success && response.data) {
        const paperData = response.data
        if (paperData.content && (!paperData.sections || paperData.sections.length === 0)) {
          paperData.sections = [{
            id: '1',
            title: paperData.title || '全文',
            content: paperData.content,
            parentId: null
          }]
        } else if (paperData.content && paperData.sections && paperData.sections.length > 0) {
          const sections = paperData.sections
          const content = paperData.content
          const sectionTitles = sections.map(s => s.title).filter(Boolean)
          if (sectionTitles.length > 0) {
            const parts = content.split(/#{2,3}\s+/).filter(p => p.trim())
            if (parts.length >= sectionTitles.length) {
              sections.forEach((section, idx) => {
                section.content = parts[idx] || ''
              })
            } else {
              sections[0].content = content
            }
          }
          paperData.sections = sections
        }
        setPapers(prev => [paperData, ...prev])
        setProject(paperData)
        setIsUploadModalOpen(false)
        setUploadingFile(null)
        messageApi.success('论文上传成功')
      } else {
        messageApi.error('上传失败: ' + (response.error || '未知错误'))
      }
    } catch (e) {
      console.error('上传错误:', e)
      messageApi.error('上传论文失败: ' + (e.message || '网络错误'))
    }
  }

  // 从导航状态获取论文ID并加载论文
  useEffect(() => {
    const paperId = location.state?.paperId
    if (paperId) {
      loadPaper(paperId)
    }
  }, [location.state, papers])

  // 当store中的project变化时，同步到组件状态
  useEffect(() => {
    if (project?.title) {
      setPaperTitle(project.title)
    }
    if (project?.sections?.length > 0) {
      // 同步当前选中章节的内容
      if (selectedSection) {
        const section = project.sections.find(s => s.id === selectedSection)
        if (section) {
          setSectionContent(section.content || '')
          // 同时同步全文模式内容
          const merged = project.sections.map(s => `## ${s.title}\n\n${s.content || ''}`).join('\n\n')
          setUnifiedContent(merged)
          return
        }
      }
      // 如果没有有效选中章节，选第一个
      setSelectedSection(project.sections[0].id)
      setSectionContent(project.sections[0].content || '')
    }
  }, [project, selectedSection])

  // 当切换到全文模式时，同步内容
  useEffect(() => {
    if (editorMode === 'unified' && project?.sections?.length > 0) {
      const merged = project.sections.map(s => `## ${s.title}\n\n${s.content || ''}`).join('\n\n')
      setUnifiedContent(merged)
    }
  }, [editorMode, project])

  // 自动保存
  useEffect(() => {
    if (saveStatus === 'unsaved') {
      autoSaveTimer.current = setTimeout(() => {
        handleSave()
      }, 30000)
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
        messageApi.success('已保存')
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
      children: sections
        .filter(s => s.id.includes('-') && s.id.startsWith(root.id + '-'))
        .map(s => ({ title: s.title, key: s.id, isLeaf: true }))
    }))
  }, [sections])

  const handleOutlineSelect = (selectedKeys) => {
    if (selectedKeys.length > 0) {
      const key = selectedKeys[0]
      const section = sections.find(s => s.id === key)
      console.log('点击章节:', key, section?.title, 'content长度:', section?.content?.length || 0)
      setSelectedSection(key)
      setSectionContent(section?.content || '')
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
    messageApi.success('已添加新章节')
  }

  const handleDeleteSection = (sectionId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个章节吗？',
      onOk() {
        deleteSection(sectionId)
        const remaining = sections.filter(s => s.id !== sectionId)
        if (remaining.length > 0) {
          setSelectedSection(remaining[0].id)
          setSectionContent(remaining[0].content || '')
        }
        messageApi.success('章节已删除')
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
      messageApi.error('保存失败')
    }
  }

  const handleGenerateOutline = async () => {
    if (!paperTitle) {
      messageApi.warning('请先设置论文标题')
      return
    }
    if (!project?.id) {
      messageApi.warning('请先创建或选择论文')
      return
    }
    setGeneratingOutline(true)
    try {
      const result = await paperAPI.generateOutline(project.id, paperTitle)
      if (result.success && result.data) {
        let newSections = []
        const outlineData = result.data.outline || result.data
        // Handle array format
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
          })
        } else if (outlineData && typeof outlineData === 'object') {
          // Handle dict format from OutlineAgent: {chapters: [...], structure: {...}}
          const chapters = outlineData.chapters || []
          chapters.forEach((chapter, idx) => {
            newSections.push({
              id: String(idx + 1),
              title: chapter.name || chapter.title || `章节${idx + 1}`,
              parentId: null,
              content: ''
            })
          })
        }
        if (newSections.length > 0) {
          setProject({ ...project, sections: newSections })
          setSelectedSection(newSections[0].id)
          setSectionContent('')
        }
        messageApi.success('大纲已生成！')
      } else {
        messageApi.error(result.error || '生成大纲失败')
      }
    } catch (e) {
      messageApi.error('生成大纲失败: ' + (e.message || '网络错误'))
    } finally {
      setGeneratingOutline(false)
    }
  }

  const handleGenerateContent = async () => {
    if (!project?.id) {
      messageApi.warning('请先创建或选择论文')
      return
    }

    let targetSection = selectedSection
    const currentSections = project?.sections || []

    if (!targetSection || !currentSections.find(s => s.id === targetSection)) {
      if (!currentSections.find(s => s.id === '1')) {
        addSection({ id: '1', title: '第1章 引言', parentId: null, content: '' })
      }
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
      messageApi.info('已创建章节：1.1 研究背景')
    }

    setGeneratingContent(true)
    try {
      const result = await paperAPI.formatContent(project.id, targetSection, sectionContent)
      if (result && result.success && result.data) {
        const content = result.data.content || ''
        setSectionContent(content)
        updateSection(targetSection, content)
        messageApi.success('格式已修正！')
      } else if (result && result.error) {
        messageApi.error('修正格式失败: ' + result.error)
      } else {
        messageApi.error('修正格式失败')
      }
    } catch (e) {
      console.error('修正格式错误:', e)
      messageApi.error('修正格式失败: ' + (e.message || '请检查网络或API配置'))
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
    messageApi.success(`已引用: ${record.title}`)
  }

  const handleRemoveCitation = (id) => {
    removeCitation(id)
    messageApi.success('引用已移除')
  }

  const handleCopyCitation = async (record) => {
    try {
      const result = await literatureAPI.getCitation(record.id, citeStyle)
      if (result.success && result.data?.citation) {
        navigator.clipboard.writeText(result.data.citation)
        messageApi.success('引用格式已复制')
      }
    } catch (e) {
      const fallback = `${record.authors}. (${record.year || 'n.d.'}). ${record.title}. ${record.journal || ''}`.trim()
      navigator.clipboard.writeText(fallback)
      messageApi.success('引用已复制')
    }
  }

  const currentSectionTitle = sections.find(s => s.id === selectedSection)?.title || selectedSection
  const totalWords = sections.reduce((acc, s) => acc + (s.content?.length || 0), 0)
  const currentWords = sectionContent.length

  // 未选择论文时的界面
  if (!project?.id) {
    return (
      <>
        {contextHolder}
        <div className="h-full flex items-center justify-center bg-gray-50">
          <Card className="text-center !rounded-xl shadow-lg w-[480px]">
            <div className="py-10 px-6">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <FileTextOutlined className="text-4xl text-white" />
              </div>
              <Title level={4} className="!text-gray-700 !mb-3">开始您的论文写作</Title>
              <Text type="secondary" className="block mb-8 text-sm">
                选择已有论文或创建新论文，开启智能写作之旅
              </Text>
              <Space direction="vertical" size="middle" className="w-full">
                <Select
                  placeholder="选择论文..."
                  className="!w-full"
                  size="large"
                  onChange={(paperId) => {
                    const paper = papers.find(p => p.id === paperId)
                    if (paper) {
                      setProject(paper)
                      setPaperTitle(paper.title || '未命名论文')
                      // 切换论文时重置章节选择
                      if (paper.sections && paper.sections.length > 0) {
                        setSelectedSection(paper.sections[0].id)
                        setSectionContent(paper.sections[0].content || '')
                      } else {
                        setSelectedSection('')
                        setSectionContent('')
                      }
                    }
                  }}
                  options={papers.map(p => ({ label: p.title || '未命名', value: p.id }))}
                />
                <Button type="primary" icon={<FileAddOutlined />} onClick={() => setIsCreateModalOpen(true)} block size="large">
                  新建论文
                </Button>
                <Button icon={<CloudUploadOutlined />} onClick={() => setIsUploadModalOpen(true)} block size="large">
                  上传论文
                </Button>
              </Space>
            </div>
          </Card>

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

          <UploadPaperModal
            open={isUploadModalOpen}
            uploadingFile={uploadingFile}
            setUploadingFile={setUploadingFile}
            onUpload={handleUploadPaper}
          />
        </div>
      </>
    )
  }

  return (
    <>
      {contextHolder}
      <div className={`h-full flex flex-col bg-gray-100 ${isFullscreen ? 'fixed inset-0 z-50 bg-white' : ''}`}>
        {/* 顶部工具栏 - 重新设计 */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between">
            {/* 左侧：论文选择 + 标题 */}
            <Space size="middle" className="flex-shrink-0">
              <Select
                value={project?.id}
                onChange={(paperId) => {
                  const paper = papers.find(p => p.id === paperId)
                  if (paper) {
                    setProject(paper)
                    setPaperTitle(paper.title || '未命名论文')
                    // 切换论文时重置章节选择
                    if (paper.sections && paper.sections.length > 0) {
                      setSelectedSection(paper.sections[0].id)
                      setSectionContent(paper.sections[0].content || '')
                    } else {
                      setSelectedSection('')
                      setSectionContent('')
                    }
                  }
                }}
                className="!w-48"
                options={papers.map(p => ({ label: p.title || '未命名', value: p.id }))}
              />
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
              <Tag color={saveStatus === 'saved' ? 'success' : saveStatus === 'saving' ? 'processing' : 'warning'}>
                {saveStatus === 'saved' ? '已保存' : saveStatus === 'saving' ? '保存中...' : '未保存'}
              </Tag>
            </Space>

            {/* 中间：核心操作按钮 */}
            <Space size="middle" className="flex-shrink-0">
              <Tooltip title="保存 (Ctrl+S)">
                <Button
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={saveStatus === 'saving'}
                  disabled={generatingContent || generatingOutline}
                >
                  保存
                </Button>
              </Tooltip>
              <Tooltip title="上传论文文件">
                <Button
                  icon={<CloudUploadOutlined />}
                  onClick={() => setIsUploadModalOpen(true)}
                >
                  上传
                </Button>
              </Tooltip>
              <Tooltip title="AI修正格式 (Ctrl+Enter)">
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  onClick={handleGenerateContent}
                  loading={generatingContent}
                  className="!bg-gradient-to-r from-blue-500 to-purple-600 !border-0"
                >
                  修正格式
                </Button>
              </Tooltip>
            </Space>

            {/* 右侧：视图切换 + 状态 */}
            <Space size="middle" className="flex-shrink-0">
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
              <Tooltip title={isFullscreen ? '退出全屏' : '全屏模式'}>
                <Button
                  icon={isFullscreen ? <CompressOutlined /> : <FullscreenOutlined />}
                  onClick={() => setIsFullscreen(!isFullscreen)}
                />
              </Tooltip>
            </Space>
          </div>
        </div>

        {/* 主内容区 - 左右两栏 + 底部引用 */}
        <div className="flex-1 flex flex-col min-h-0 p-4 overflow-hidden">
          {/* 上方：大纲 + 写作区 */}
          <div className="flex-1 flex gap-4 min-h-0">
            {/* 左侧大纲 - 卡片式设计 */}
            <Card
              className="!rounded-xl shadow-sm flex-shrink-0 w-60 flex flex-col"
              styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}}
            >
              <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
                <Space>
                  <FileTextOutlined className="text-blue-500" />
                  <Text strong className="text-sm">论文大纲</Text>
                </Space>
              </div>
              <div className="flex-1 overflow-auto p-2">
                <Tree
                  treeData={outlineData}
                  selectedKeys={[selectedSection]}
                  onSelect={(keys, info) => {
                    console.log('Tree onSelect fired, keys:', keys, 'nodeTitle:', info?.node?.title)
                    if (keys.length > 0) {
                      const key = String(keys[0])
                      const section = project?.sections?.find(s => s.id === key)
                      console.log('点击章节:', key, section?.title, 'content长度:', section?.content?.length || 0)
                      setSelectedSection(key)
                      setSectionContent(section?.content || '')
                    }
                  }}
                  defaultExpandAll
                  blockNode
                  selectable
                  showLine
                  className="outline-tree"
                  style={{ fontSize: '13px', color: '#333' }}
                  titleRender={(nodeData) => (
                    <span style={{ color: '#333', fontSize: '13px', fontWeight: nodeData.isLeaf ? 'normal' : 500 }}>
                      {nodeData.title}
                    </span>
                  )}
                />
              </div>
              <div className="px-3 py-2 border-t border-gray-100 bg-gray-50 flex justify-between">
                <Button type="text" size="small" icon={<PlusOutlined />} onClick={handleAddSection}>
                  添加
                </Button>
                <Button type="text" size="small" icon={<DeleteOutlined />} danger onClick={() => handleDeleteSection(selectedSection)}>
                  删除
                </Button>
              </div>
            </Card>

            {/* 中间写作区 - 主编辑区 */}
            <Card
              className="flex-1 !rounded-xl shadow-sm flex flex-col min-w-0"
              styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' } }}
            >
              {/* 标题栏 */}
              <div className="px-4 py-3 border-b border-gray-100 bg-white flex items-center justify-between">
                <Space>
                  <EditOutlined className="text-blue-500" />
                  <Text strong>{currentSectionTitle}</Text>
                  <Tag color="blue" className="text-xs">{currentWords} 字</Tag>
                </Space>
                <Space size="small">
                  <span className="text-xs text-gray-400">总字数: {totalWords}</span>
                </Space>
              </div>

              {/* 编辑/预览区域 */}
              <div className="flex-1 flex min-h-0">
                {/* 左侧编辑区 */}
                {editorMode !== 'preview' && (
                  <div
                    ref={leftScrollRef}
                    className={`flex-1 flex flex-col min-w-0 ${editorMode === 'split' || editorMode === 'unified' ? 'border-r border-gray-200' : ''} overflow-auto bg-white`}
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
                        className="flex-1 !border-0 !rounded-none !resize-none !bg-white"
                        placeholder="全文编辑模式..."
                        style={{
                          fontSize: '15px',
                          lineHeight: '1.8',
                          padding: '20px 24px',
                        }}
                        value={unifiedContent}
                        onChange={(e) => setUnifiedContent(e.target.value)}
                      />
                    ) : (
                      <TextArea
                        className="flex-1 !border-0 !rounded-none !resize-none !bg-white"
                        placeholder="开始写作... 或点击上方「修正格式」让AI帮您生成内容"
                        style={{
                          fontSize: '15px',
                          lineHeight: '1.8',
                          padding: '20px 24px',
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
                    className="flex-1 overflow-auto bg-gray-50"
                    style={{ padding: '20px 24px' }}
                    onScroll={(e) => {
                      if (isSyncingScroll) return
                      setIsSyncingScroll(true)
                      if (leftScrollRef.current) {
                        leftScrollRef.current.scrollTop = e.target.scrollTop
                      }
                      setTimeout(() => setIsSyncingScroll(false), 50)
                    }}
                  >
                    <div className="markdown-body bg-white p-6 rounded-lg shadow-sm">
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
            </Card>
          </div>

          {/* 底部：引用管理 - 横条卡片 */}
          <Card
            className="!rounded-xl shadow-sm mt-4 flex-shrink-0"
            styles={{ body: { padding: 0 }}}
          >
            <div className="flex items-center h-10">
              <div className="flex items-center gap-2 px-4 py-2 border-r border-gray-100">
                <BookOutlined className="text-purple-500" />
                <Text strong className="text-sm">引用管理</Text>
                <Select
                  size="small"
                  value={citeStyle}
                  onChange={setCiteStyle}
                  className="!w-24"
                  options={[
                    { label: 'APA', value: 'APA' },
                    { label: 'GB/T', value: 'GB/T' },
                    { label: 'MLA', value: 'MLA' },
                  ]}
                />
              </div>
              <div className="flex-1 overflow-auto px-4 py-2">
                {(project?.citations || []).length === 0 ? (
                  <Text type="secondary" className="text-xs">暂无引用，点击右侧按钮添加</Text>
                ) : (
                  <div className="flex gap-2 items-center">
                    {(project?.citations || []).map((cite) => (
                      <div key={cite.id} className="flex-shrink-0 px-3 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 flex items-center gap-1">
                        <span className="font-medium truncate max-w-[200px]">{cite.title}</span>
                        <Tooltip title="复制引用"><Button type="text" size="small" icon={<CopyOutlined />} onClick={() => handleCopyCitation(cite)} className="!text-xs !p-0" /></Tooltip>
                        <Tooltip title="删除引用"><Button type="text" size="small" icon={<DeleteOutlined />} onClick={() => handleRemoveCitation(cite.id)} className="!text-xs !p-0 !text-red-500" /></Tooltip>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex-shrink-0 px-2">
                <Button type="primary" size="small" icon={<BookOutlined />} onClick={() => setShowCiteModal(true)}>
                  添加引用
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* 引用弹窗 */}
        <Modal
          title={
            <Space>
              <BookOutlined className="text-purple-500" />
              <span>添加引用</span>
            </Space>
          }
          open={showCiteModal}
          onCancel={() => setShowCiteModal(false)}
          footer={null}
          width={600}
        >
          <div className="py-4">
            <Input placeholder="搜索文献..." prefix={<FileTextOutlined />} className="mb-4" />
            <List
              size="small"
              dataSource={[]}
              renderItem={(item) => (
                <List.Item
                  className="cursor-pointer hover:bg-blue-50"
                  onClick={() => { handleAddCitation(item); setShowCiteModal(false) }}
                >
                  <List.Item.Meta
                    title={item.title}
                    description={`${item.authors} (${item.year})`}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无文献，请在文献管理中添加' }}
            />
          </div>
        </Modal>

        <UploadPaperModal
          open={isUploadModalOpen}
          uploadingFile={uploadingFile}
          setUploadingFile={setUploadingFile}
          onUpload={handleUploadPaper}
        />
      </div>
    </>
  )
}

export default WritingPage