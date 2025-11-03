import React, { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Collapse,
  IconButton,
  Grid,
  Divider,
  CircularProgress,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CodeIcon from "@mui/icons-material/Code";
import "./AnalysisCard.css";
import DependencyGraph from "../DependencyGraph/DependencyGraph";
import RiskScore from "../RiskScore/RiskScore";
import { apiService } from "../../services/api";

function AnalysisCard({ analysis }) {
  const [expanded, setExpanded] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [loadingGraph, setLoadingGraph] = useState(false);

  const handleExpand = async () => {
    const newExpanded = !expanded;
    setExpanded(newExpanded);

    // Load graph data when expanding
    if (newExpanded && !graphData) {
      setLoadingGraph(true);
      try {
        const fileName = analysis.file_path.split("/").pop();
        const data = await apiService.getDependencyGraph(fileName);
        setGraphData(data);
      } catch (error) {
        console.error("Error loading graph:", error);
      } finally {
        setLoadingGraph(false);
      }
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      CRITICAL: "#dc3545",
      HIGH: "#fd7e14",
      MEDIUM: "#ffc107",
      LOW: "#28a745",
    };
    return colors[level] || "#6c757d";
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <Card className="analysis-card">
      <CardContent>
        {/* Header */}
        <div className="analysis-header">
          <div className="analysis-info">
            <div className="file-path">
              <CodeIcon fontSize="small" />
              <Typography variant="h6" component="span">
                {analysis.file_path.split("/").pop()}
              </Typography>
            </div>
            <div className="timestamp">
              <AccessTimeIcon fontSize="small" />
              <Typography variant="caption">
                {formatTimestamp(analysis.timestamp)}
              </Typography>
            </div>
          </div>

          <div className="risk-badge">
            <Chip
              label={`${analysis.risk_score.score}/10`}
              style={{
                backgroundColor: getRiskColor(analysis.risk_score.level),
                color: "white",
                fontWeight: "bold",
                fontSize: "1.1rem",
                padding: "0.5rem",
              }}
            />
            <Typography
              variant="caption"
              style={{ color: getRiskColor(analysis.risk_score.level) }}
            >
              {analysis.risk_score.level}
            </Typography>
          </div>
        </div>

        {/* Quick Stats */}
        <Box className="quick-stats" mt={2}>
          <div className="stat-item">
            <Typography variant="caption" color="textSecondary">
              Direct Dependencies
            </Typography>
            <Typography variant="h6">
              {analysis.dependencies.count.direct}
            </Typography>
          </div>
          <div className="stat-item">
            <Typography variant="caption" color="textSecondary">
              Indirect Dependencies
            </Typography>
            <Typography variant="h6">
              {analysis.dependencies.count.indirect}
            </Typography>
          </div>
          <div className="stat-item">
            <Typography variant="caption" color="textSecondary">
              Affected Modules
            </Typography>
            <Typography variant="h6">
              {analysis.affected_modules.length}
            </Typography>
          </div>
        </Box>

        {/* AI Summary */}
        <Box mt={2} className="ai-summary">
          <Typography variant="body2" color="textSecondary">
            🤖 AI Insights:
          </Typography>
          <Typography variant="body1">
            {analysis.ai_insights.summary}
          </Typography>
        </Box>

        {/* Expand Button */}
        <Box textAlign="center" mt={2}>
          <IconButton onClick={handleExpand} aria-label="show more">
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            <Typography variant="caption" ml={1}>
              {expanded ? "Show Less" : "Show Details"}
            </Typography>
          </IconButton>
        </Box>

        {/* Expanded Content */}
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Divider style={{ margin: "1rem 0" }} />

          {/* Risks */}
          <Box mb={2}>
            <Typography variant="h6" gutterBottom>
              ⚠️ Identified Risks
            </Typography>
            <ul className="risk-list">
              {analysis.ai_insights.risks.map((risk, index) => (
                <li key={index}>
                  <Typography variant="body2">{risk}</Typography>
                </li>
              ))}
            </ul>
          </Box>

          <Box mt={3}>
            <RiskScore riskScore={analysis.risk_score} />
          </Box>

          {/* Regulatory Concerns */}
          {analysis.ai_insights.regulatory_concerns && (
            <Box mb={2}>
              <Typography variant="h6" gutterBottom>
                📋 Regulatory Concerns
              </Typography>
              <Typography variant="body2">
                {analysis.ai_insights.regulatory_concerns}
              </Typography>
            </Box>
          )}

          {/* Recommendations */}
          {analysis.ai_insights.recommendations &&
            analysis.ai_insights.recommendations.length > 0 && (
              <Box mb={2}>
                <Typography variant="h6" gutterBottom>
                  💡 Recommendations
                </Typography>
                <ul className="recommendation-list">
                  {analysis.ai_insights.recommendations.map((rec, index) => (
                    <li key={index}>
                      <Typography variant="body2">{rec}</Typography>
                    </li>
                  ))}
                </ul>
              </Box>
            )}

          {/* Affected Modules */}
          <Box>
            <Typography variant="h6" gutterBottom>
              📦 Affected Modules ({analysis.affected_modules.length})
            </Typography>
            <div className="module-chips">
              {analysis.affected_modules.slice(0, 10).map((module, index) => (
                <Chip
                  key={index}
                  label={module}
                  size="small"
                  variant="outlined"
                  style={{ margin: "0.25rem" }}
                />
              ))}
              {analysis.affected_modules.length > 10 && (
                <Chip
                  label={`+${analysis.affected_modules.length - 10} more`}
                  size="small"
                  variant="outlined"
                  style={{ margin: "0.25rem" }}
                />
              )}
            </div>
          </Box>

          {/* Dependency Graph */}
          <Box mt={3}>
            {loadingGraph ? (
              <Box textAlign="center" p={2}>
                <CircularProgress size={24} />
                <Typography variant="caption" display="block" mt={1}>
                  Loading dependency graph...
                </Typography>
              </Box>
            ) : graphData ? (
              <DependencyGraph
                fileName={analysis.file_path.split("/").pop()}
                dependencies={graphData}
              />
            ) : (
              <Typography variant="body2" color="textSecondary" align="center">
                No graph data available
              </Typography>
            )}
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
}

export default AnalysisCard;
