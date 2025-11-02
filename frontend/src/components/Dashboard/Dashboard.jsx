import React, { useState, useEffect } from 'react';
import { Container, Grid, Paper, Typography, CircularProgress } from '@mui/material';
import './Dashboard.css';

function Dashboard() {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    setLoading(true);
    try {
      // API call will be implemented later
      // For now, show empty state
      setAnalyses([]);
    } catch (error) {
      console.error('Error loading analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-container">
      <Container maxWidth="xl">
        <Grid container spacing={3}>
          {/* Welcome Section */}
          <Grid item xs={12}>
            <Paper elevation={3} className="dashboard-paper welcome-section">
              <Typography variant="h4" gutterBottom>
                Welcome to CodeFlow Catalyst
              </Typography>
              <Typography variant="body1" color="textSecondary">
                Real-time impact analysis for your code changes. 
                Commit code to see analysis results here.
              </Typography>
            </Paper>
          </Grid>

          {/* Statistics Cards */}
          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card">
              <div className="stat-icon">📊</div>
              <Typography variant="h6">Total Analyses</Typography>
              <Typography variant="h3">0</Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card">
              <div className="stat-icon">⚠️</div>
              <Typography variant="h6">Critical Risks</Typography>
              <Typography variant="h3">0</Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper elevation={3} className="dashboard-paper stat-card">
              <div className="stat-icon">✅</div>
              <Typography variant="h6">Safe Changes</Typography>
              <Typography variant="h3">0</Typography>
            </Paper>
          </Grid>

          {/* Recent Analyses Section */}
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
                </div>
              ) : (
                <div>
                  {/* Analysis list will be rendered here */}
                  <Typography>Analyses will appear here...</Typography>
                </div>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </div>
  );
}

export default Dashboard;