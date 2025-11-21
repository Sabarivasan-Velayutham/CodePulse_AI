import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard/Dashboard';
import { apiService } from './services/api';
import AnalysisCard from './components/AnalysisCard/AnalysisCard';

function App() {
  const [isBackendHealthy, setIsBackendHealthy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkBackendHealth();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const health = await apiService.healthCheck();
      setIsBackendHealthy(health.status === 'ok');
    } catch (error) {
      console.error('Backend not available:', error);
      setIsBackendHealthy(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🚀 CodePulse AI</h1>
          <p>AI-Powered Impact Analysis for Banking Applications</p>
          <div className="status-indicator">
            {loading ? (
              <span>Checking status...</span>
            ) : (
              <span className={isBackendHealthy ? 'status-healthy' : 'status-error'}>
                {isBackendHealthy ? '✅ System Ready' : '❌ Backend Offline'}
              </span>
            )}
          </div>
        </div>
      </header>
      
      {isBackendHealthy ? (
        <Dashboard />
      ) : (
        <div className="error-message">
          <h2>Backend Service Unavailable</h2>
          <p>Please ensure the backend server is running on port 8000</p>
          <button onClick={checkBackendHealth}>Retry Connection</button>
        </div>
      )}
    </div>
  );
}

export default App;