import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加API密钥认证
    const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
    config.headers['X-API-Key'] = apiKey
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
}

// AI助手API
export const aiAPI = {
  // 发送消息
  sendMessage: (paperId, message) =>
    apiClient.post(`/papers/${paperId}/chat`, { message }),

  // 流式响应 (返回EventSource) - 注意: EventSource不支持自定义headers，API key通过query传递
  streamMessage: (paperId, message) => {
    const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
    return new EventSource(`${API_BASE_URL}/papers/${paperId}/chat/stream?message=${encodeURIComponent(message)}&api_key=${encodeURIComponent(apiKey)}`)
  },
}

// 用户设置API
export const settingsAPI = {
  // 获取设置
  getSettings: () => apiClient.get('/settings'),

  // 更新设置
  updateSettings: (settings) => apiClient.put('/settings', settings),
}

export default {
  paperAPI,
  literatureAPI,
  aiAPI,
  settingsAPI,
}