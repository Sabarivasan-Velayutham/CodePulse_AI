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
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      return { status: 'error' };
    }
  },
  
  // Get analysis by ID
  getAnalysis: async (analysisId) => {
    try {
      const response = await api.get(`/api/v1/analysis/${analysisId}`);
      return response.data;
    } catch (error) {
      console.error('Get analysis failed:', error);
      throw error;
    }
  },
  
  // Get all analyses
  getAllAnalyses: async () => {
    try {
      const response = await api.get('/api/v1/analyses');
      return response.data;
    } catch (error) {
      console.error('Get all analyses failed:', error);
      return []; // Return empty array instead of throwing
    }
  },
  
  // Trigger manual analysis
  triggerAnalysis: async (data) => {
    try {
      const response = await api.post('/api/v1/analyze', data);
      return response.data;
    } catch (error) {
      console.error('Trigger analysis failed:', error);
      throw error;
    }
  },
  
  // Get dependency graph for code files
  getDependencyGraph: async (fileName) => {
    try {
      const response = await api.get(`/api/v1/graph/${fileName}`);
      return response.data;
    } catch (error) {
      console.error('Get dependency graph failed:', error);
      return { nodes: [], links: [] }; // Return empty graph
    }
  },
  
  // Get dependency graph for database tables (schema changes)
  getTableDependencyGraph: async (tableName) => {
    try {
      const response = await api.get(`/api/v1/schema/graph/${tableName}`);
      return response.data;
    } catch (error) {
      console.error('Get table dependency graph failed:', error);
      return { nodes: [], links: [] }; // Return empty graph
    }
  },
};

export default api;