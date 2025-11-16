import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear tokens and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  signup: (data) =>
    api.post('/auth/signup', data),

  getCurrentUser: () =>
    api.get('/auth/me'),
};

// Assessments API
export const assessmentsAPI = {
  list: (organizationId) =>
    api.get(`/assessments`, { params: { organization_id: organizationId } }),

  get: (id) =>
    api.get(`/assessments/${id}`),

  create: (data) =>
    api.post('/assessments', data),

  update: (id, data) =>
    api.put(`/assessments/${id}`, data),

  delete: (id) =>
    api.delete(`/assessments/${id}`),
};

// Evidence API
export const evidenceAPI = {
  list: (assessmentId) =>
    api.get(`/evidence`, { params: { assessment_id: assessmentId } }),

  upload: (data, file) => {
    const formData = new FormData();
    formData.append('file', file);
    Object.keys(data).forEach(key => {
      formData.append(key, data[key]);
    });
    return api.post('/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (id) =>
    api.delete(`/evidence/${id}`),
};

// Controls API
export const controlsAPI = {
  list: () =>
    api.get('/controls'),

  analyze: (controlId, data) =>
    api.post(`/analyze/${controlId}`, data),

  getFindings: (assessmentId) =>
    api.get(`/findings`, { params: { assessment_id: assessmentId } }),
};

// Dashboard API
export const dashboardAPI = {
  getSummary: (organizationId) =>
    api.get(`/dashboard/summary/${organizationId}`),

  getCompliance: (assessmentId) =>
    api.get(`/dashboard/compliance/${assessmentId}`),

  getActivity: (organizationId, limit = 50) =>
    api.get(`/dashboard/activity/${organizationId}`, { params: { limit } }),

  getRiskMetrics: (assessmentId) =>
    api.get(`/dashboard/risk/${assessmentId}`),

  getEvidenceStats: (assessmentId) =>
    api.get(`/dashboard/evidence/${assessmentId}`),
};

// SPRS API
export const sprsAPI = {
  calculate: (assessmentId) =>
    api.post(`/sprs/calculate/${assessmentId}`),

  getHistory: (assessmentId) =>
    api.get(`/sprs/history/${assessmentId}`),

  getTrend: (assessmentId) =>
    api.get(`/sprs/trend/${assessmentId}`),
};

export default api;
