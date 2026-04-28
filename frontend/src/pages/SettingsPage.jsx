import React, { useState, useEffect } from 'react'
import { Card, Form, Switch, Select, Input, Button, Space, Typography, Divider, message, Tag, Row, Col, Alert, Tooltip } from 'antd'
import {
  SaveOutlined,
  PlusOutlined,
  CloseOutlined,
  GlobalOutlined,
  BgColorsOutlined,
  FontColorsOutlined,
  SyncOutlined,
  ApiOutlined,
  KeyOutlined,
  SafetyOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { settingsAPI } from '../services/api'

const { Title, Text } = Typography

// 默认学术关键词
const DEFAULT_KEYWORDS = [
  'machine learning',
  'deep learning',
  'natural language processing',
  'computer vision',
  'artificial intelligence'
]

// 关键词分类颜色
const KEYWORD_CATEGORIES = {
  ai: { color: '#722ed1', label: 'AI' },
  ml: { color: '#1890ff', label: 'ML' },
  nlp: { color: '#52c41a', label: 'NLP' },
  cv: { color: '#fa8c16', label: 'CV' },
}

const SettingsPage = () => {
  const [form] = Form.useForm()
  const [keywords, setKeywords] = useState(DEFAULT_KEYWORDS)
  const [inputKeyword, setInputKeyword] = useState('')
  const [loading, setLoading] = useState(false)

  // 加载设置
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await settingsAPI.getSettings()
      if (response.success && response.data) {
        const data = response.data
        if (data.keywords && data.keywords.length > 0) {
          setKeywords(data.keywords)
        }
        form.setFieldsValue({
          language: data.language || 'zh-CN',
          theme: data.theme || 'light',
          autoSave: data.autoSave !== false,
          autoSaveInterval: data.autoSaveInterval || 30,
          defaultCitationStyle: data.defaultCitationStyle || 'apa',
          defaultModel: data.defaultModel || 'gpt-4',
        })
      }
    } catch (e) {
      console.error('加载设置失败', e)
    }
  }

  const handleSave = async (values) => {
    setLoading(true)
    try {
      // 合并关键词和设置
      const settings = {
        ...values,
        keywords: keywords
      }
      await settingsAPI.updateSettings(settings)
      message.success('设置已保存')
    } catch (e) {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  // 添加关键词
  const handleAddKeyword = () => {
    const kw = inputKeyword.trim()
    if (kw && !keywords.includes(kw)) {
      setKeywords([...keywords, kw])
      setInputKeyword('')
    }
  }

  // 删除关键词
  const handleRemoveKeyword = (keyword) => {
    setKeywords(keywords.filter(k => k !== keyword))
  }

  // 按回车添加关键词
  const handleKeywordInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddKeyword()
    }
  }

  return (
    <div className="max-w-4xl space-y-4">
      {/* 基本设置 */}
      <Card
        title={
          <Space>
            <GlobalOutlined className="text-blue-500" />
            <span>基本设置</span>
          </Space>
        }
        className="!rounded-lg"
      >
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="界面语言" name="language" className="!mb-4">
              <Select
                options={[
                  { label: '简体中文', value: 'zh-CN' },
                  { label: 'English', value: 'en-US' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="主题模式" name="theme" className="!mb-4">
              <Select
                options={[
                  { label: '亮色模式', value: 'light' },
                  { label: '暗色模式', value: 'dark' },
                  { label: '护眼模式', value: 'paper' },
                ]}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="默认引用格式" name="defaultCitationStyle" className="!mb-4">
              <Select
                options={[
                  { label: 'APA', value: 'apa' },
                  { label: 'MLA', value: 'mla' },
                  { label: 'IEEE', value: 'ieee' },
                  { label: 'GB/T 7714', value: 'gbt' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="默认模型" name="defaultModel" className="!mb-4">
              <Select
                options={[
                  { label: 'GPT-4', value: 'gpt-4' },
                  { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
                  { label: 'Claude 3', value: 'claude-3' },
                  { label: 'DeepSeek', value: 'deepseek' },
                ]}
              />
            </Form.Item>
          </Col>
        </Row>
      </Card>

      {/* 学术资讯关键词 */}
      <Card
        title={
          <Space>
            <KeyOutlined className="text-orange-500" />
            <span>学术资讯关键词</span>
          </Space>
        }
        extra={
          <Tooltip title="系统将根据关键词从多个学术数据库搜索最新论文">
            <InfoCircleOutlined className="text-gray-400" />
          </Tooltip>
        }
        className="!rounded-lg"
      >
        <Alert
          message="关键词设置提示"
          description="设置您感兴趣的学术研究关键词，系统将根据这些关键词从 arXiv、PubMed、Semantic Scholar、OpenAlex 等数据库搜索最新论文并生成日报/周报/月报资讯。"
          type="info"
          showIcon
          icon={<KeyOutlined />}
          className="!mb-4"
        />

        <Text type="secondary" className="block mb-3">
          当前监测关键词（共 {keywords.length} 个）:
        </Text>

        <div className="flex flex-wrap gap-2 mb-4 p-4 bg-gray-50 rounded-lg min-h-[60px]">
          {keywords.length > 0 ? keywords.map(keyword => (
            <Tag
              key={keyword}
              closable
              onClose={() => handleRemoveKeyword(keyword)}
              className="px-3 py-1 text-sm"
              style={{ margin: 0 }}
              color="blue"
            >
              {keyword}
            </Tag>
          )) : (
            <Text type="secondary">暂无设置关键词</Text>
          )}
        </div>

        <Space.Compact className="w-full">
          <Input
            value={inputKeyword}
            onChange={e => setInputKeyword(e.target.value)}
            onKeyDown={handleKeywordInputKeyDown}
            placeholder="输入关键词后按回车添加"
            prefix={<KeyOutlined className="text-gray-400" />}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAddKeyword}
          >
            添加
          </Button>
        </Space.Compact>
      </Card>

      {/* AI模型配置 */}
      <Card
        title={
          <Space>
            <ApiOutlined className="text-purple-500" />
            <span>AI模型配置</span>
          </Space>
        }
        className="!rounded-lg"
      >
        <Row gutter={24}>
          <Col span={24}>
            <Form.Item label="API密钥" name="apiKey" className="!mb-4">
              <Input.Password placeholder="输入API密钥" prefix={<KeyOutlined />} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={24}>
          <Col span={24}>
            <Form.Item label="API代理地址（可选）" name="apiProxy" className="!mb-0">
              <Input placeholder="如: https://api.openai.com/v1" prefix={<ApiOutlined />} />
            </Form.Item>
          </Col>
        </Row>
      </Card>

      {/* 文献同步 */}
      <Card
        title={
          <Space>
            <SyncOutlined className="text-green-500" />
            <span>文献同步</span>
          </Space>
        }
        className="!rounded-lg"
      >
        <Form.Item label="Zotero同步" name="zoteroSync" className="!mb-0">
          <Space>
            <Switch />
            <Input
              placeholder="Zotero API Key"
              className="w-64"
              disabled
              prefix={<KeyOutlined />}
            />
            <Button disabled icon={<SyncOutlined />}>连接</Button>
          </Space>
        </Form.Item>
      </Card>

      {/* 保存按钮 */}
      <Card className="!rounded-lg !bg-gradient-to-r from-blue-50 to-purple-50">
        <Space className="w-full justify-end">
          <Button htmlType="button" onClick={() => form.resetFields()} size="large">
            重置
          </Button>
          <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading} size="large">
            保存设置
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default SettingsPage