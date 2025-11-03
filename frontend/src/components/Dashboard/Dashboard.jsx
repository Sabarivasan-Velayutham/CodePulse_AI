import React, { useState, useEffect } from 'react';
import RefreshIcon from '@mui/icons-material/Refresh';
import AnalysisCard from '../AnalysisCard/AnalysisCard';
import { apiService } from '../../services/api';
import './Dashboard.css';
import { 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  CircularProgress,
  Card,
  CardContent,
  Chip,
  Box,
  Collapse,
  IconButton,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CodeIcon from '@mui/icons-material/Code';

function Dashboard() {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    critical: 0,
    safe: 0
  });

  useEffect(() => {
    loadAnalyses();
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadAnalyses, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadAnalyses = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAllAnalyses();
      setAnalyses(data);
      calculateStats(data);
    } catch (error) {
      console.error('Error loading analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (analysesData) => {
    const critical = analysesData.filter(
      a => a.risk_score?.level === 'CRITICAL'
    ).length;
    
    const safe = analysesData.filter(
      a => a.risk_score?.level === 'LOW'
    ).length;

    setStats({
      total: analysesData.length,
      critical: critical,
      safe: safe
    });
  };

  return (
    <div className="dashboard-container">
      <Container maxWidth="xl">
        <Grid container spacing={3}>
          {/* Header */}
          <Grid item xs={12}>
            <Paper elevation={3} className="dashboard-paper welcome-section">
              <div className="welcome-header">
                <div>
                  <Typography variant="h4" gutterBottom>
                    Impact Analysis Dashboard
                  </Typography>
                  <Typography variant="body1">
                    Real-time code change analysis powered by AI
                  </Typography>
                </div>
                <Button
                  variant="contained"
                  startIcon={<RefreshIcon />}
                  onClick={loadAnalyses}
                  disabled={loading}
                >
                  Refresh
                </Button>
              </div>
            </Paper>
          </Grid>

          {/* Statistics Cards */}
          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card">
              <div className="stat-icon">📊</div>
              <Typography variant="h6">Total Analyses</Typography>
              <Typography variant="h3">{stats.total}</Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card critical">
              <div className="stat-icon">⚠️</div>
              <Typography variant="h6">Critical Risks</Typography>
              <Typography variant="h3">{stats.critical}</Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card safe">
              <div className="stat-icon">✅</div>
              <Typography variant="h6">Safe Changes</Typography>
              <Typography variant="h3">{stats.safe}</Typography>
            </Paper>
          </Grid>

          {/* Recent Analyses */}
          <Grid item xs={12}>
            <Paper elevation={3} className="dashboard-paper">
              <Typography variant="h5" gutterBottom>
                Recent Analyses
              </Typography>
              
              {loading ? (
                <div className="loading-container">
                  <CircularProgress />
                  <Typography>Loading analyses...</Typography>
                </div>
              ) : analyses.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📭</div>
                  <Typography variant="h6">No analyses yet</Typography>
                  <Typography variant="body2" color="textSecondary">
                    Commit code changes to GitHub to trigger analysis
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={loadAnalyses}
                    style={{ marginTop: '1rem' }}
                  >
                    Check Again
                  </Button>
                </div>
              ) : (
                <Grid container spacing={2}>
                  {analyses.map((analysis) => (
                    <Grid item xs={12} key={analysis.id}>
                      <AnalysisCard analysis={analysis} />
                    </Grid>
                  ))}
                </Grid>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </div>
  );
}

export default Dashboard;