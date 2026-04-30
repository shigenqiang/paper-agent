/**
 * UploadModal - 文献文件上传组件
 */
import React from 'react'
import { Modal, Upload, Typography, Spin } from 'antd'
import { FilePdfOutlined } from '@ant-design/icons'

const { Text } = Typography
const { Dragger } = Upload

/**
 * UploadModal组件
 * @param {boolean} open - 是否打开
 * @param {function} onClose - 关闭回调
 * @param {function} onUpload - 上传文件回调
 * @param {boolean} uploading - 上传中状态
 */
export function UploadModal({
  open,
  onClose,
  onUpload,
  uploading = false,
}) {
  const beforeUpload = (file) => {
    const isPdf = file.type === 'application/pdf'
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    const isText = file.type.startsWith('text/')
    if (!isPdf && !isDocx && !isText) {
      return false
    }
    const isLt50M = file.size / 1024 / 1024 < 50
    if (!isLt50M) {
      return false
    }
    onUpload(file)
    return false
  }

  return (
    <Modal
      title="上传文献文件"
      open={open}
      onCancel={onClose}
      footer={null}
      width={500}
    >
      <div className="py-4">
        <div className="text-center">
          {uploading ? (
            <Spin tip="正在上传并提取元数据...">
              <div style={{ minHeight: 200 }} />
            </Spin>
          ) : (
            <>
              <Dragger
                accept=".pdf,.doc,.docx,.txt"
                showUploadList={false}
                beforeUpload={beforeUpload}
                disabled={uploading}
              >
                <p className="ant-upload-drag-icon">
                  <FilePdfOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                <p className="ant-upload-hint">
                  支持 PDF、Word (.doc/.docx) 或文本文件<br />
                  系统将自动识别文献元数据（标题、作者、年份等）
                </p>
              </Dragger>
              <div className="mt-4 text-xs text-gray-400">
                <Text type="secondary">上传后AI将自动提取文件中的元数据信息</Text>
              </div>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default UploadModal