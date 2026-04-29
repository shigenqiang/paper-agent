import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Button, Space, Typography, Tree, Input, Divider, Tag, Tooltip, message, Modal, Progress, Badge, Empty, Spin, Avatar, notification, List, Select } from 'antd'
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
} from '@ant-design/icons'
import { usePaperStore } from '../store/paperStore'
import { paperAPI, literatureAPI } from '../services/api'
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
  const [newPaperTitle, setNewPaperTitle] = useState('')
  const autoSaveTimer = useRef(null)
  const [showCiteModal, setShowCiteModal] = useState(false)
  const [citeStyle, setCiteStyle] = useState('APA')

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
      const prompt = `为"${currentTitle}"章节生成学术内容`
      const result = await paperAPI.generateContent(project.id, targetSection, prompt)
      if (result.success && result.data) {
        const content = result.data.content || ''
        setSectionContent(content)
        updateSection(targetSection, content)
        message.success('内容已生成！')
      } else {
        message.error(result.error || '生成内容失败')
      }
    } catch (e) {
      message.error('生成内容失败: ' + (e.message || '网络错误'))
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
      <Card size="small" className="mb-3 !rounded-lg" bodyStyle={{ padding: '12px 16px' }}>
        <div className="flex justify-between items-center">
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
            <Tooltip title="AI续写当前章节（Ctrl+Enter）">
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={handleGenerateContent}
                loading={generatingContent}
              >
                AI续写
              </Button>
            </Tooltip>
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
          bodyStyle={{ padding: 0 }}
        >
          <div className="flex justify-between items-center px-3 pt-3 pb-2">
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
          </div>
          <Divider className="my-0" />
          {project?.citations?.length > 0 ? (
            <div className="max-h-64 overflow-auto">
              <List
                size="small"
                dataSource={project.citations}
                renderItem={(cite) => (
                  <List.Item
                    className="px-3 py-2"
                    actions={[
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => handleCopyCitation(cite)}
                      />,
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleRemoveCitation(cite.id)}
                      />,
                    ]}
                  >
                    <List.Item.Meta
                      title={<Text strong className="text-xs">{cite.title}</Text>}
                      description={
                        <Space direction="vertical" size={0}>
                          <Text type="secondary" className="text-xs" ellipsis>{cite.authors}</Text>
                          <Tag color="blue" className="!m-0 !text-xs">{cite.year || 'n.d.'}</Tag>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>
          ) : (
            <div className="p-3">
              <Empty
                description="暂无引用"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                className="py-6"
              />
            </div>
          )}
          <Divider className="my-0" />
          <div className="p-2">
            <Button
              block
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
    </div>
  )
}

export default WritingPage
