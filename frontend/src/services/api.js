import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const DEFAULT_API_KEY = 'dev-api-key'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加API密钥认证
    const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
    // 确保headers对象存在
    if (!config.headers) {
      config.headers = {}
    }
    // 使用小写header名称，后端会忽略大小写
    config.headers['x-api-key'] = apiKey
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response } = error
    if (response?.status === 401) {
      // 处理未授权 - 清除本地存储的API密钥
      localStorage.removeItem('api_key')
      console.error('Unauthorized, please check your API key')
    }
    return Promise.reject(error)
  }
)

// 论文相关API
export const paperAPI = {
  // 创建新论文
  createPaper: (data) => apiClient.post('/papers', data),

  // 获取论文列表
  getPapers: (params) => apiClient.get('/papers', { params }),

  // 获取论文详情
  getPaper: (id) => apiClient.get(`/papers/${id}`),

  // 更新论文
  updatePaper: (id, data) => apiClient.put(`/papers/${id}`, data),

  // 删除论文
  deletePaper: (id) => apiClient.delete(`/papers/${id}`),

  // 获取论文大纲
  getOutline: (id) => apiClient.get(`/papers/${id}/outline`),

  // 生成大纲
  generateOutline: (id, topic) => apiClient.post(`/papers/${id}/outline/generate`, { topic }),

  // 生成内容
  generateContent: (id, sectionId, prompt) =>
    apiClient.post(`/papers/${id}/sections/${sectionId}/generate`, { prompt }),
}

// 文献相关API
export const literatureAPI = {
  // 搜索文献
  search: (query, params) => apiClient.post('/literature/search', { query, ...params }),

  // 获取文献详情
  getDetail: (id) => apiClient.get(`/literature/${id}`),

  // 添加到文献库
  addToLibrary: (paperId, literatureData) =>
    apiClient.post(`/papers/${paperId}/literature`, literatureData),

  // 获取引用格式
  getCitation: (id, style) => apiClient.get(`/literature/${id}/citation`, { params: { style } }),

  // 上传文献文件
  uploadFile: (formData) => apiClient.post('/literature/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  }),
}

// AI助手API
export const aiAPI = {
  // 发送消息（带上下文）
  sendMessage: (paperId, message, userId, sessionId) =>
    apiClient.post(`/papers/${paperId}/chat`, {
      message,
      user_id: userId,
      session_id: sessionId
    }),

  // 流式响应 (返回EventSource) - 注意: EventSource不支持自定义headers，API key通过query传递
  streamMessage: (paperId, message) => {
    const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
    return new EventSource(`${API_BASE_URL}/papers/${paperId}/chat/stream?message=${encodeURIComponent(message)}&api_key=${encodeURIComponent(apiKey)}`)
  },

  // 获取聊天历史
  getChatHistory: (paperId, userId, sessionId) =>
    apiClient.get(`/papers/${paperId}/chat/history`, {
      params: { user_id: userId, session_id: sessionId }
    }),
}

// 用户设置API
export const settingsAPI = {
  // 获取设置
  getSettings: () => apiClient.get('/settings'),

  // 更新设置
  updateSettings: (settings) => apiClient.put('/settings', settings),
}

// 学术资讯快报API
export const reportsAPI = {
  // 获取资讯列表
  getReports: (params) => apiClient.get('/reports', { params }),

  // 获取资讯详情
  getReport: (id) => apiClient.get(`/reports/${id}`),

  // 生成新资讯
  createReport: (data) => apiClient.post('/reports', data),

  // 更新资讯(如重新生成)
  updateReport: (id, data) => apiClient.put(`/reports/${id}`, data),

  // 删除资讯
  deleteReport: (id) => apiClient.delete(`/reports/${id}`),

  // 获取日报列表
  getDailyReports: (params) => apiClient.get('/reports/daily', { params }),

  // 获取周报列表
  getWeeklyReports: (params) => apiClient.get('/reports/weekly', { params }),

  // 获取月报列表
  getMonthlyReports: (params) => apiClient.get('/reports/monthly', { params }),
}

// 知识图谱API
export const knowledgeGraphAPI = {
  // 获取文献知识图谱
  getLiteratureGraph: () => apiClient.get('/knowledge-graph/literature'),

  // 生成知识图谱
  generateGraph: (literatureIds) => apiClient.post('/knowledge-graph/generate', { literatureIds }),

  // 获取实体关联
  getEntityRelations: (entityId) => apiClient.get(`/knowledge-graph/entity/${entityId}`),
}

export default {
  paperAPI,
  literatureAPI,
  aiAPI,
  settingsAPI,
  reportsAPI,
  knowledgeGraphAPI,
}