/**
 * LiteratureForm - 添加文献表单组件
 */
import React from 'react'
import { Modal, Form, Input, Space, Button } from 'antd'

/**
 * LiteratureForm组件
 * @param {boolean} open - 是否打开
 * @param {function} onClose - 关闭回调
 * @param {function} onSubmit - 提交表单回调
 */
export function LiteratureForm({
  open,
  onClose,
  onSubmit,
}) {
  const [form] = Form.useForm()

  const handleFinish = (values) => {
    onSubmit(values)
    form.resetFields()
  }

  const handleClose = () => {
    form.resetFields()
    onClose()
  }

  return (
    <Modal
      title="添加文献"
      open={open}
      onCancel={handleClose}
      footer={null}
      width={500}
    >
      <Form form={form} onFinish={handleFinish} layout="vertical">
        <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入论文标题' }]}>
          <Input placeholder="请输入论文标题" />
        </Form.Item>
        <Form.Item label="作者" name="authors" rules={[{ required: true, message: '请输入作者' }]}>
          <Input placeholder="请输入作者，多个作者用逗号分隔" />
        </Form.Item>
        <Space className="w-full" size="large">
          <Form.Item label="年份" name="year" className="flex-1">
            <Input type="number" placeholder="年份" />
          </Form.Item>
          <Form.Item label="期刊" name="journal" className="flex-1">
            <Input placeholder="期刊名称" />
          </Form.Item>
        </Space>
        <Form.Item label="DOI" name="doi">
          <Input placeholder="论文DOI (可选)" />
        </Form.Item>
        <Form.Item className="!mb-0">
          <Space className="w-full justify-end">
            <Button onClick={handleClose}>取消</Button>
            <Button type="primary" htmlType="submit">添加</Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default LiteratureForm