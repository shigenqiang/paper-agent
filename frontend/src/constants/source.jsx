/**
 * 文献来源配置
 * 解决SOURCE_CONFIG在3处重复定义的问题
 */
import {
  GlobalOutlined,
  ExperimentOutlined,
  RobotOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'

// 文献来源列表
export const SOURCE_CONFIG_LIST = [
  { key: 'arxiv', label: 'arXiv', desc: 'AI/ML/物理预印本', color: '#e84a25' },
  { key: 'pubmed', label: 'PubMed', desc: '生物医学文献', color: '#3e84c8' },
  { key: 'semantic_scholar', label: 'Semantic Scholar', desc: 'AI论文引用数据', color: '#5c7fdd' },
  { key: 'openalex', label: 'OpenAlex', desc: '跨学科覆盖', color: '#ff6b35' },
]

// 文献来源图标和颜色映射
export const SOURCE_CONFIG = {
  arxiv: {
    icon: <GlobalOutlined />,
    color: '#e84a25',
    label: 'arXiv'
  },
  pubmed: {
    icon: <ExperimentOutlined />,
    color: '#3e84c8',
    label: 'PubMed'
  },
  semantic: {
    icon: <RobotOutlined />,
    color: '#5c7fdd',
    label: 'Semantic'
  },
  semantic_scholar: {
    icon: <RobotOutlined />,
    color: '#5c7fdd',
    label: 'Semantic Scholar'
  },
  openalex: {
    icon: <DatabaseOutlined />,
    color: '#ff6b35',
    label: 'OpenAlex'
  },
}

// 获取来源配置
export const getSourceConfig = (sourceKey) => {
  return SOURCE_CONFIG[sourceKey] || {
    icon: null,
    color: '#d9d9d9',
    label: sourceKey || '未知来源'
  }
}

// 获取来源列表（用于设置面板）
export const getSourceList = () => SOURCE_CONFIG_LIST

// 验证来源是否有效
export const isValidSource = (sourceKey) => {
  return SOURCE_CONFIG_LIST.some(s => s.key === sourceKey)
}
