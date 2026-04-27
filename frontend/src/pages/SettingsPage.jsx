import React from 'react'
import { Card, Form, Switch, Select, Input, Button, Space, Typography, Divider, message } from 'antd'
import { SaveOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

const SettingsPage = () => {
  const [form] = Form.useForm()

  const handleSave = (values) => {
    console.log('Settings saved:', values)
    message.success('设置已保存')
  }

  return (
    <div className="max-w-3xl">
      <Card title="基本设置">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            language: 'zh-CN',
            theme: 'light',
            autoSave: true,
            autoSaveInterval: 30,
            defaultCitationStyle: 'apa',
          }}
          onFinish={handleSave}
        >
          <Form.Item label="界面语言" name="language">
            <Select
              options={[
                { label: '简体中文', value: 'zh-CN' },
                { label: 'English', value: 'en-US' },
              ]}
            />
          </Form.Item>

          <Form.Item label="主题模式" name="theme">
            <Select
              options={[
                { label: '亮色模式', value: 'light' },
                { label: '暗色模式', value: 'dark' },
                { label: '护眼模式', value: 'paper' },
              ]}
            />
          </Form.Item>

          <Form.Item label="默认引用格式" name="defaultCitationStyle">
            <Select
              options={[
                { label: 'APA', value: 'apa' },
                { label: 'MLA', value: 'mla' },
                { label: 'IEEE', value: 'ieee' },
                { label: 'GB/T 7714', value: 'gbt' },
              ]}
            />
          </Form.Item>

          <Divider />

          <Title level={5}>自动保存</Title>

          <Form.Item label="启用自动保存" name="autoSave" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item label="保存间隔（秒）" name="autoSaveInterval">
            <Select
              options={[
                { label: '10秒', value: 10 },
                { label: '30秒', value: 30 },
                { label: '60秒', value: 60 },
                { label: '5分钟', value: 300 },
              ]}
            />
          </Form.Item>

          <Divider />

          <Title level={5}>AI模型设置</Title>

          <Form.Item label="默认模型" name="defaultModel">
            <Select
              options={[
                { label: 'GPT-4', value: 'gpt-4' },
                { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
                { label: 'Claude 3', value: 'claude-3' },
                { label: 'DeepSeek', value: 'deepseek' },
              ]}
            />
          </Form.Item>

          <Form.Item label="API密钥" name="apiKey">
            <Input.Password placeholder="输入API密钥" />
          </Form.Item>

          <Form.Item label="API代理地址（可选）" name="apiProxy">
            <Input placeholder="如: https://api.openai.com/v1" />
          </Form.Item>

          <Divider />

          <Title level={5}>文献同步</Title>

          <Form.Item label="Zotero同步" name="zoteroSync">
            <Space>
              <Switch />
              <Input
                placeholder="Zotero API Key"
                className="w-64"
                disabled
              />
              <Button disabled>连接</Button>
            </Space>
          </Form.Item>

          <Form.Item className="!mb-0">
            <Space>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                保存设置
              </Button>
              <Button htmlType="button" onClick={() => form.resetFields()}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default SettingsPage