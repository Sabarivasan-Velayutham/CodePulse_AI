import React, { useState } from 'react';
import { Box, Typography, LinearProgress, Chip, Collapse, IconButton, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import './RiskScore.css';

function RiskScore({ riskScore }) {
  const { score, level, color, breakdown, explanations, summary } = riskScore || {};
  const [expandedComponent, setExpandedComponent] = useState(null);

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
              {breakdown?.technical || 0}/{breakdown?.technical !== undefined ? '4' : breakdown?.table_criticality !== undefined ? '3' : '4'}
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              {breakdown?.domain !== undefined ? 'Domain Risk' : breakdown?.code_impact !== undefined ? 'Code Impact' : 'Domain Risk'}
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown?.domain || breakdown?.code_impact || 0}/{breakdown?.domain !== undefined ? '3' : breakdown?.code_impact !== undefined ? '3' : '3'}
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              {breakdown?.database_relationships !== undefined ? 'DB Relationships' : 'AI Analysis'}
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown?.database_relationships || breakdown?.ai_analysis || 0}/{breakdown?.database_relationships !== undefined ? '2' : '2'}
            </Typography>
          </div>
          <div className="breakdown-item">
            <Typography variant="caption" color="textSecondary">
              AI Analysis
            </Typography>
            <Typography variant="h6" color="primary">
              {breakdown?.ai_analysis || 0}/2
            </Typography>
          </div>
        </div>
      </Box>

      {/* Detailed Explanations */}
      {explanations && (
        <Box mt={3}>
          <Typography variant="h6" gutterBottom>
            📊 How This Score Was Calculated
          </Typography>
          
          {/* Technical Risk / Table Criticality */}
          {explanations.technical && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    Technical Risk: {breakdown?.technical || 0}/{explanations.technical.max_score || 4}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.technical} />
              </AccordionDetails>
            </Accordion>
          )}

          {explanations.table_criticality && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    Table Criticality: {breakdown?.table_criticality || 0}/{explanations.table_criticality.max_score || 3}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.table_criticality} />
              </AccordionDetails>
            </Accordion>
          )}

          {/* Domain Risk / Code Impact */}
          {explanations.domain && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    Domain Risk: {breakdown?.domain || 0}/{explanations.domain.max_score || 3}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.domain} />
              </AccordionDetails>
            </Accordion>
          )}

          {explanations.code_impact && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    Code Impact: {breakdown?.code_impact || 0}/{explanations.code_impact.max_score || 3}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.code_impact} />
              </AccordionDetails>
            </Accordion>
          )}

          {/* Database Relationships */}
          {explanations.database_relationships && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    Database Relationships: {breakdown?.database_relationships || 0}/{explanations.database_relationships.max_score || 2}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.database_relationships} />
              </AccordionDetails>
            </Accordion>
          )}

          {/* AI Analysis */}
          {explanations.ai_analysis && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" width="100%">
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    AI Analysis: {breakdown?.ai_analysis || 0}/{explanations.ai_analysis.max_score || 2}
                  </Typography>
                  <InfoIcon sx={{ color: 'text.secondary', ml: 1 }} />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <RiskComponentExplanation explanation={explanations.ai_analysis} />
              </AccordionDetails>
            </Accordion>
          )}

        </Box>
      )}

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

function RiskComponentExplanation({ explanation }) {
  if (!explanation) return null;

  return (
    <Box>
      {/* Description */}
      {explanation.description && (
        <Typography variant="body2" color="textSecondary" paragraph sx={{ fontStyle: 'italic' }}>
          {explanation.description}
        </Typography>
      )}

      {/* Contributing Factors */}
      {explanation.factors && explanation.factors.length > 0 && (
        <Box mt={2}>
          <Typography variant="subtitle2" gutterBottom>
            📋 Contributing Factors:
          </Typography>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {explanation.factors.map((factor, idx) => (
              <li key={idx}>
                <Typography variant="body2">{factor}</Typography>
              </li>
            ))}
          </ul>
        </Box>
      )}

      {/* Detailed Explanations */}
      {explanation.details && explanation.details.length > 0 && (
        <Box mt={2}>
          <Typography variant="subtitle2" gutterBottom>
            💡 Why This Score:
          </Typography>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {explanation.details.map((detail, idx) => (
              <li key={idx}>
                <Typography variant="body2">{detail}</Typography>
              </li>
            ))}
          </ul>
        </Box>
      )}

      {/* Score Display */}
      {explanation.score !== undefined && (
        <Box mt={2} p={1.5} sx={{ backgroundColor: '#e3f2fd', borderRadius: 1 }}>
          <Typography variant="body2">
            <strong>Score:</strong> {explanation.score.toFixed(1)} / {explanation.max_score || 4}
            {explanation.multiplier !== undefined && ` (Multiplier: ${explanation.multiplier.toFixed(2)}x)`}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default RiskScore;