import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API endpoints
export const apiService = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
  
  // Get analysis by ID
  getAnalysis: async (analysisId) => {
    const response = await api.get(`/api/v1/analysis/${analysisId}`);
    return response.data;
  },
  
  // Get all analyses
  getAllAnalyses: async () => {
    const response = await api.get('/api/v1/analyses');
    return response.data;
  },
  
  // Trigger manual analysis
  triggerAnalysis: async (data) => {
    const response = await api.post('/api/v1/analyze', data);
    return response.data;
  },
  
  // Get dependency graph
  getDependencyGraph: async (fileName) => {
    const response = await api.get(`/api/v1/graph/${fileName}`);
    return response.data;
  },
};

export default api;