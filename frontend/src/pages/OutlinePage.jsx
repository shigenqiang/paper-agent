import React, { useState } from 'react'
import { Card, Button, Space, Typography, Tree, Input, Tag, Tooltip, message, Modal, Empty, Spin } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  DeleteOutlined,
  RobotOutlined,
  LeftOutlined,
} from '@ant-design/icons'
import { useProjectStore } from '../store/projectStore'
import { useWritingStore } from '../store/writingStore'
import { paperAPI } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { DEFAULT_SECTIONS } from '../constants/paper'

const { Title, Text } = Typography

const OutlinePage = () => {
  const navigate = useNavigate()
  const { project, setProject, addSection, deleteSection } = useProjectStore()
  const { selectedSection, setSelectedSection, sectionContent, setSectionContent } = useWritingStore()
  const [paperTitle, setPaperTitle] = useState(project?.title || '新论文')
  const [generating, setGenerating] = useState(false)

  // 生成大纲
  const handleGenerateOutline = async () => {
    if (!paperTitle.trim()) {
      message.warning('请输入论文标题')
      return
    }
    setGenerating(true)
    try {
      const paperId = project?.id
      if (!paperId) {
        message.error('请先在写作页面创建或选择论文')
        setGenerating(false)
        return
      }
      const result = await paperAPI.generateOutline(paperId, paperTitle)
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
          message.success('大纲已生成！')
        } else {
          message.warning('未生成有效大纲，请重试')
        }
      } else {
        message.error('生成失败')
      }
    } catch (error) {
      message.error('生成失败: ' + error.message)
    } finally {
      setGenerating(false)
    }
  }

  // 使用默认模板
  const handleUseDefaultTemplate = () => {
    setProject({ ...project, sections: DEFAULT_SECTIONS })
    setSelectedSection('1')
    message.success('已使用默认模板')
  }

  // 添加章节
  const handleAddSection = () => {
    const newId = Date.now().toString()
    addSection({
      id: newId,
      title: '新章节',
      parentId: null,
      content: ''
    })
    setSelectedSection(newId)
  }

  // 删除章节
  const handleDeleteSection = (id) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个章节吗？',
      okText: '删除',
      okType: 'danger',
      onOk() {
        deleteSection(id)
        if (selectedSection === id) {
          setSelectedSection(null)
          setSectionContent('')
        }
        message.success('章节已删除')
      }
    })
  }

  // 跳转到写作页面
  const handleGoToWriting = () => {
    if (project?.sections?.length > 0) {
      navigate('/writing')
    } else {
      message.warning('请先生成大纲或使用模板')
    }
  }

  // 构建树形数据
  const treeData = (project?.sections || []).reduce((acc, section) => {
    if (!section.parentId) {
      acc.push({
        key: section.id,
        title: section.title,
        children: (project.sections || [])
          .filter(s => s.parentId === section.id)
          .map(s => ({
            key: s.id,
            title: s.title,
          }))
      })
    }
    return acc
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Title level={3} className="!mb-0">
          <Space>
            <ThunderboltOutlined />
            <span>AI生成大纲</span>
          </Space>
        </Title>
        <Space>
          <Button icon={<LeftOutlined />} onClick={() => navigate('/writing')}>
            返回写作
          </Button>
        </Space>
      </div>

      <Card>
        <div className="space-y-4">
          <div>
            <Text strong className="block mb-2">论文标题</Text>
            <Input
              placeholder="请输入论文标题，AI将据此生成大纲"
              value={paperTitle}
              onChange={(e) => setPaperTitle(e.target.value)}
              size="large"
            />
          </div>

          <Space>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleGenerateOutline}
              loading={generating}
              disabled={!paperTitle.trim()}
            >
              {generating ? '生成中...' : 'AI生成大纲'}
            </Button>
            <Button icon={<FileTextOutlined />} onClick={handleUseDefaultTemplate}>
              使用默认模板
            </Button>
          </Space>
        </div>
      </Card>

      {(project?.sections?.length > 0 || generating) && (
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <span>大纲预览</span>
              {project?.sections?.length > 0 && (
                <Tag color="blue">{project.sections.length} 个章节</Tag>
              )}
            </Space>
          }
          extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={handleAddSection}>
                添加章节
              </Button>
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={handleGoToWriting}
                disabled={!project?.sections?.length}
              >
                开始写作
              </Button>
            </Space>
          }
        >
          {generating ? (
            <div className="text-center py-12">
              <Spin tip="AI正在生成大纲..." />
            </div>
          ) : treeData.length > 0 ? (
            <Tree
              treeData={treeData}
              selectedKeys={selectedSection ? [selectedSection] : []}
              onSelect={(keys) => {
                if (keys.length > 0) {
                  setSelectedSection(keys[0])
                  const section = project?.sections?.find(s => s.id === keys[0])
                  setSectionContent(section?.content || '')
                }
              }}
              titleRender={(item) => (
                <div className="flex items-center justify-between w-full pr-4">
                  <Text>{item.title}</Text>
                  <Space size="small">
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteSection(item.key)
                        }}
                      />
                    </Tooltip>
                  </Space>
                </div>
              )}
            />
          ) : (
            <Empty description="暂无大纲，请使用上方按钮生成或选择模板" />
          )}
        </Card>
      )}

      {/* 大纲说明 */}
      <Card size="small" className="!bg-gray-50">
        <Text type="secondary" className="text-sm">
          <strong>提示：</strong>生成大纲后可以手动编辑调整章节结构，点击"开始写作"将跳转至写作页面继续编辑内容。
        </Text>
      </Card>
    </div>
  )
}

export default OutlinePage
