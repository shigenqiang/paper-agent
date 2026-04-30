import React from 'react'
import { Modal, Upload, Button, Typography, Spin } from 'antd'
import { CloudUploadOutlined, InboxOutlined, FilePdfOutlined, FileMarkdownOutlined, FileTextOutlined } from '@ant-design/icons'

const { Text } = Typography

export const UploadPaperModal = ({ open, uploadingFile, setUploadingFile, onUpload }) => {
  return (
    <Modal
      title={
        <div>
          <CloudUploadOutlined className="text-blue-500 mr-2" />
          上传论文
        </div>
      }
      open={open}
      onCancel={() => {
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
            return false
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
                onClick={onUpload}
                block
                size="large"
              >
                开始上传
              </Button>
              <Button onClick={() => setUploadingFile(null)}>
                清除
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
