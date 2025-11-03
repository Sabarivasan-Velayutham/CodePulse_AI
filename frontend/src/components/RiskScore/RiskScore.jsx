import React from 'react';
import { Box, Typography, LinearProgress, Chip } from '@mui/material';
import './RiskScore.css';

function RiskScore({ riskScore }) {
  const { score, level, color, breakdown } = riskScore;

  const getRiskIcon = (level) => {
    const icons = {
      'CRITICAL': '🔴',
      'HIGH': '🟠',
      'MEDIUM': '🟡',
      'LOW': '🟢'
    };
    return icons[level] || '⚪';
  };

  const getProgressColor = (score) => {
    if (score >= 7.5) return 'error';
    if (score >= 5.5) return 'warning';
    if (score >= 3.5) return 'info';
    return 'success';
  };

  return (
    <Box className="risk-score-container">
      {/* Main Score Display */}
      <Box className="risk-score-main">
        <div className="risk-icon">{getRiskIcon(level)}</div>
        <div className="risk-details">
          <Typography variant="h3" className="risk-score-value">
            {score}/10
          </Typography>
          <Chip
            label={level}
            style={{
              backgroundColor: color,
              color: 'white',
              fontWeight: 'bold'
            }}
          />
        </div>
      </Box>

      {/* Progress Bar */}
      <Box mt={2}>
        <LinearProgress
          variant="determinate"
          value={score * 10}
          color={getProgressColor(score)}
          style={{ height: 10, borderRadius: 5 }}
        />
      </Box>

      {/* Score Breakdown */}
      <Box mt={3}>
        <Typography variant="h6" gutterBottom>
          Risk Breakdown
        </Typography>
        <div className="breakdown-grid">
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              Technical Risk
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown.technical}/4
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              Domain Risk
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown.domain}/3
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              AI Analysis
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown.ai_analysis}/2
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              Temporal
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown.temporal_multiplier}x
            </Typography>
          </div>
        </div>
      </Box>

      {/* Risk Scale Reference */}
      <Box mt={3} className="risk-scale">
        <Typography variant="caption" color="textSecondary" gutterBottom>
          Risk Scale
        </Typography>
        <div className="scale-bar">
          <div className="scale-section low">
            <span>0-3.5</span>
            <span>LOW</span>
          </div>
          <div className="scale-section medium">
            <span>3.5-5.5</span>
            <span>MEDIUM</span>
          </div>
          <div className="scale-section high">
            <span>5.5-7.5</span>
            <span>HIGH</span>
          </div>
          <div className="scale-section critical">
            <span>7.5-10</span>
            <span>CRITICAL</span>
          </div>
        </div>
        <div className="scale-marker" style={{ left: `${score * 10}%` }}>
          <div className="marker-arrow">▼</div>
          <div className="marker-label">{score}</div>
        </div>
      </Box>
    </Box>
  );
}

export default RiskScore;