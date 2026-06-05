const BASE = '/api/rw'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Projects
  listProjects: () => request('/projects'),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),

  // Papers
  listPapers: (projectId) => request(`/projects/${projectId}/papers`),
  getPaper: (id) => request(`/papers/${id}`),
  uploadPaper: (projectId, formData) =>
    fetch(`${BASE}/projects/${projectId}/papers/upload`, { method: 'POST', body: formData }).then(r => r.json()),
  uploadPapersBatch: (projectId, formData) =>
    fetch(`${BASE}/projects/${projectId}/papers/upload/batch`, { method: 'POST', body: formData }).then(r => r.json()),
  searchPapers: (projectId, query) =>
    request(`/projects/${projectId}/papers/search`, { method: 'POST', body: JSON.stringify({ query }) }),
  excludePaper: (id) => request(`/papers/${id}/exclude`, { method: 'POST' }),
  includePaper: (id) => request(`/papers/${id}/include`, { method: 'POST' }),

  // Parse
  parsePaper: (id) => request(`/papers/${id}/parse`, { method: 'POST' }),
  parseProject: (projectId) => request(`/projects/${projectId}/parse`, { method: 'POST' }),
  generateCard: (id) => request(`/papers/${id}/card`, { method: 'POST' }),
  generateEvidence: (projectId) => request(`/projects/${projectId}/evidence`, { method: 'POST' }),

  // Knowledge Graph
  buildGraph: (projectId) => request(`/projects/${projectId}/kg/build`, { method: 'POST' }),
  getGraph: (projectId) => request(`/projects/${projectId}/kg`),

  // QA
  askQuestion: (projectId, data) =>
    request(`/projects/${projectId}/qa`, { method: 'POST', body: JSON.stringify(data) }),

  // Reports
  generateLiteratureReview: (projectId, scope) =>
    request(`/projects/${projectId}/reports/literature-review`, { method: 'POST', body: JSON.stringify({ scope }) }),
  generateInnovationReport: (projectId, scope) =>
    request(`/projects/${projectId}/reports/innovation`, { method: 'POST', body: JSON.stringify({ scope }) }),
  listReports: (projectId) => request(`/projects/${projectId}/reports`),
  exportReportMarkdown: (reportId) => request(`/reports/${reportId}/export/markdown`),
}
