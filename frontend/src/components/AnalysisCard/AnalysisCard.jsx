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
        if (analysis.type === "schema_change") {
          // For schema changes, get table/collection dependency graph
          const tableName = analysis.schema_change?.table_name;
          const databaseName = analysis.database;
          const databaseType = analysis.database_type;
          const analysisId = analysis.id; // Pass analysis ID to get complete relationships
          if (tableName) {
            const data = await apiService.getTableDependencyGraph(tableName, databaseName, databaseType, analysisId);
            setGraphData(data);
          }
        } else if (analysis.type === "api_contract_change") {
          // For API contract changes, show API consumer graph
          const analysisId = analysis.id;
          if (analysisId) {
            const data = await apiService.getApiContractGraph(analysisId);
            setGraphData(data);
          } else {
            setGraphData(null);
          }
        } else if (analysis.file_path) {
          // For code changes, get file dependency graph
          const fileName = analysis.file_path.split("/").pop();
          const data = await apiService.getDependencyGraph(fileName);
          setGraphData(data);
        }
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

  const cleanSummaryText = (text) => {
    if (!text || typeof text !== 'string') return text;
    
    // Remove markdown code blocks
    let cleaned = text.trim();
    
    // Remove "json " prefix if present (e.g., "json { "summary": ...")
    cleaned = cleaned.replace(/^json\s+/i, '');
    
    // Remove ```json ... ``` or ``` ... ```
    if (cleaned.includes('```')) {
      // Find and remove code blocks
      cleaned = cleaned.replace(/```json\s*/gi, '').replace(/```\s*/g, '');
      // Remove trailing ```
      cleaned = cleaned.replace(/```\s*$/g, '').trim();
    }
    
    // If it looks like raw JSON, try to extract summary
    if (cleaned.startsWith('{') && cleaned.includes('"summary"')) {
      try {
        const parsed = JSON.parse(cleaned);
        return parsed.summary || cleaned;
      } catch (e) {
        // If parsing fails, try to extract summary manually with better regex
        // Handle both "summary": "text" and "summary": "text with \"escaped\" quotes"
        const summaryMatch = cleaned.match(/"summary"\s*:\s*"((?:[^"\\]|\\.)*)"/);
        if (summaryMatch) {
          // Unescape JSON string
          let summary = summaryMatch[1]
            .replace(/\\"/g, '"')
            .replace(/\\n/g, '\n')
            .replace(/\\t/g, '\t')
            .replace(/\\\\/g, '\\');
          return summary;
        }
        // Try to find summary value even if it spans multiple lines
        const multilineMatch = cleaned.match(/"summary"\s*:\s*"([\s\S]*?)"/);
        if (multilineMatch) {
          return multilineMatch[1].trim();
        }
      }
    }
    
    // Fix "ET" -> "GET" and "GGGET" -> "GET" encoding issues
    cleaned = cleaned.replace(/\bG+ET\b/g, 'GET');  // GGET, GGGET, etc. -> GET
    cleaned = cleaned.replace(/\bET\s+/g, 'GET ').replace(/\bET\//g, 'GET/');
    
    return cleaned;
  };

  const formatChangeDetails = (details) => {
    if (!details) return null;
    
    // If details is already a string, return it
    if (typeof details === 'string') {
      return details;
    }
    
    // If details is an object, format it
    if (typeof details === 'object') {
      const parts = [];
      
      if (details.reason) {
        parts.push(details.reason);
      }
      
      if (details.modifications && Array.isArray(details.modifications)) {
        parts.push(...details.modifications);
      } else if (details.modifications && typeof details.modifications === 'string') {
        parts.push(details.modifications);
      }
      
      // If we have before/after info, add it
      if (details.before && details.after) {
        const beforeParams = details.before.parameters || {};
        const afterParams = details.after.parameters || {};
        const paramChanges = [];
        
        // Check for parameter changes
        Object.keys(afterParams).forEach(param => {
          if (!beforeParams[param]) {
            paramChanges.push(`Added parameter: ${param}`);
          }
        });
        
        Object.keys(beforeParams).forEach(param => {
          if (!afterParams[param]) {
            paramChanges.push(`Removed parameter: ${param}`);
          } else if (beforeParams[param]?.type !== afterParams[param]?.type) {
            paramChanges.push(`Parameter ${param} type changed: ${beforeParams[param]?.type} → ${afterParams[param]?.type}`);
          }
        });
        
        if (paramChanges.length > 0) {
          parts.push(...paramChanges);
        }
      }
      
      return parts.length > 0 ? parts.join('; ') : 'Change details available';
    }
    
    return null;
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
                {analysis.type === "schema_change" 
                  ? `🗄️ ${analysis.schema_change?.table_name || "Schema Change"}`
                  : analysis.type === "api_contract_change"
                  ? `🔌 ${analysis.file_path?.split("/").pop() || "API Contract Change"}`
                  : analysis.file_path?.split("/").pop() || "Unknown File"}
              </Typography>
            </div>
            <div className="timestamp">
              <AccessTimeIcon fontSize="small" />
              <Typography variant="caption">
                {formatTimestamp(analysis.timestamp)}
              </Typography>
            </div>
            {analysis.commit_sha && analysis.commit_sha !== "manual" && (
              <div className="commit-info" style={{ marginTop: '0.5rem' }}>
                <Typography variant="caption" color="textSecondary" style={{ display: 'block' }}>
                  <strong>Commit:</strong> {analysis.commit_sha.length > 8 ? analysis.commit_sha.substring(0, 8) : analysis.commit_sha}
                </Typography>
                {analysis.commit_message && (
                  <Typography variant="caption" color="textSecondary" style={{ display: 'block', fontStyle: 'italic' }}>
                    {analysis.commit_message}
                  </Typography>
                )}
              </div>
            )}
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
          {analysis.type === "api_contract_change" ? (
            <>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  API Changes
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.total_changes || analysis.api_changes?.length || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Breaking Changes
                </Typography>
                <Typography variant="h6" style={{ color: '#dc3545' }}>
                  {analysis.summary?.breaking_changes || 
                   (analysis.api_changes?.filter(c => c.change_type === 'BREAKING').length || 0)}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Affected Consumers
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.total_consumers || 
                   Object.values(analysis.consumers || {}).reduce((sum, cons) => sum + cons.length, 0)}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Affected Endpoints
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.affected_endpoints || 
                   new Set(analysis.api_changes?.map(c => c.endpoint) || []).size}
                </Typography>
              </div>
            </>
          ) : analysis.type === "schema_change" ? (
            <>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Affected Code Files
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.code_files_affected || analysis.code_dependencies?.length || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  {analysis.database_type === "mongodb" ? "Related Collections" : "Related Tables"}
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.tables_affected || analysis.affected_tables?.length || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Total Usages
                </Typography>
                <Typography variant="h6">
                  {analysis.summary?.total_usages || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Database Connections
                </Typography>
                <Typography variant="h6">
                  {(analysis.database_relationships?.forward?.length || 0) + (analysis.database_relationships?.reverse?.length || 0)}
                </Typography>
              </div>
            </>
          ) : (
            <>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Direct Dependencies
                </Typography>
                <Typography variant="h6">
                  {analysis.dependencies?.count?.direct || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Indirect Dependencies
                </Typography>
                <Typography variant="h6">
                  {analysis.dependencies?.count?.indirect || 0}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Reverse Dependencies
                </Typography>
                <Typography variant="h6">
                  {(analysis.dependencies?.count?.reverse_direct || 0) + (analysis.dependencies?.count?.reverse_indirect || 0)}
                </Typography>
              </div>
              <div className="stat-item">
                <Typography variant="caption" color="textSecondary">
                  Affected Modules
                </Typography>
                <Typography variant="h6">
                  {analysis.affected_modules?.length || 0}
                </Typography>
              </div>
            </>
          )}
        </Box>

        {/* AI Summary */}
        <Box mt={2} className="ai-summary">
          <Typography variant="body2" color="textSecondary">
            🤖 AI Insights:
          </Typography>
          <Typography variant="body1">
            {cleanSummaryText(analysis.ai_insights.summary)}
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

          {/* Risks with Recommendations */}
          <Box mb={2}>
            <Typography variant="h6" gutterBottom>
              ⚠️ Identified Risks & Recommendations
            </Typography>
            {analysis.ai_insights.risks && analysis.ai_insights.risks.length > 0 && (
              <Box>
                {analysis.ai_insights.risks.map((risk, index) => {
                  // Get corresponding recommendation (by index)
                  const recommendation = analysis.ai_insights.recommendations && 
                    analysis.ai_insights.recommendations[index] 
                    ? analysis.ai_insights.recommendations[index] 
                    : null;
                  
                  // Handle both string and object formats for risk
                  let riskTitle = '';
                  let technicalContext = '';
                  let businessImpact = '';
                  let cascadingEffects = '';
                  
                  if (typeof risk === 'string') {
                    riskTitle = risk;
                  } else if (typeof risk === 'object' && risk !== null) {
                    riskTitle = risk.risk || risk.risk_description || risk.title || 'Risk';
                    technicalContext = risk.technical_context || risk.technical || '';
                    businessImpact = risk.business_impact || risk.business || '';
                    cascadingEffects = risk.cascading_effects || risk.cascading || '';
                  }
                  
                  // Handle recommendation format
                  let recommendationText = '';
                  if (recommendation) {
                    if (typeof recommendation === 'string') {
                      recommendationText = recommendation;
                    } else if (typeof recommendation === 'object' && recommendation !== null) {
                      recommendationText = recommendation.recommendation || recommendation.action || 
                        recommendation.suggestion || recommendation.text || '';
                    }
                  }
                  
                  return (
                    <Box key={index} mb={3} p={2} sx={{ border: '1px solid #e0e0e0', borderRadius: 1, backgroundColor: '#fafafa' }}>
                      <Typography variant="subtitle1" gutterBottom style={{ fontWeight: 'bold', color: '#d32f2f' }}>
                        Risk {index + 1}: {riskTitle}
                      </Typography>
                      
                      {technicalContext && (
                        <Box mt={1} mb={1}>
                          <Typography variant="body2" component="div">
                            <strong style={{ color: '#1976d2' }}>Technical:</strong>
                            <Typography variant="body2" component="span" style={{ marginLeft: '0.5rem' }}>
                              {technicalContext}
                            </Typography>
                          </Typography>
                        </Box>
                      )}
                      
                      {businessImpact && (
                        <Box mt={1} mb={1}>
                          <Typography variant="body2" component="div">
                            <strong style={{ color: '#1976d2' }}>Business Impact:</strong>
                            <Typography variant="body2" component="span" style={{ marginLeft: '0.5rem' }}>
                              {businessImpact}
                            </Typography>
                          </Typography>
                        </Box>
                      )}
                      
                      {cascadingEffects && (
                        <Box mt={1} mb={1}>
                          <Typography variant="body2" component="div">
                            <strong style={{ color: '#1976d2' }}>Cascading Effects:</strong>
                            <Typography variant="body2" component="span" style={{ marginLeft: '0.5rem' }}>
                              {cascadingEffects}
                            </Typography>
                          </Typography>
                        </Box>
                      )}
                      
                      {recommendationText && (
                        <Box mt={2} p={1.5} sx={{ backgroundColor: '#e8f5e9', borderRadius: 1, borderLeft: '3px solid #4caf50' }}>
                          <Typography variant="body2" component="div">
                            <strong style={{ color: '#2e7d32' }}>💡 Recommendation:</strong>
                            <Typography variant="body2" component="span" style={{ marginLeft: '0.5rem' }}>
                              {recommendationText}
                            </Typography>
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </Box>
            )}
          </Box>

          <Box mt={3}>
            <RiskScore riskScore={analysis.risk_score} />
          </Box>

          {/* Schema Change Details */}
          {analysis.type === "schema_change" && (() => {
            const isMongoDB = analysis.database_type === "mongodb";
            const entityLabel = isMongoDB ? "Collection" : "Table";
            const fieldLabel = isMongoDB ? "Field/Index" : "Column";
            const relatedLabel = isMongoDB ? "Related Collections" : "Related Tables";
            
            return (
              <>
                <Box mb={2}>
                  <Typography variant="h6" gutterBottom>
                    🗄️ Schema Change Details
                  </Typography>
                  <Typography variant="body2">
                    <strong>{entityLabel}:</strong> {analysis.schema_change?.table_name}
                  </Typography>
                  {analysis.schema_change?.column_name && (
                    <Typography variant="body2">
                      <strong>{fieldLabel}:</strong> {analysis.schema_change.column_name}
                    </Typography>
                  )}
                  {analysis.database_relationships && (
                    <>
                      {analysis.database_relationships.forward?.length > 0 && (
                        <Typography variant="body2" style={{ marginTop: "0.5rem" }}>
                          <strong>References:</strong> {analysis.database_relationships.forward.map(r => r.target_table || r.target_collection || r.table_name).filter(Boolean).join(", ")}
                        </Typography>
                      )}
                      {analysis.database_relationships.reverse?.length > 0 && (
                        <Typography variant="body2">
                          <strong>Referenced By:</strong> {analysis.database_relationships.reverse.map(r => r.source_table || r.source_collection || r.table_name).filter(Boolean).join(", ")}
                        </Typography>
                      )}
                    </>
                  )}
                </Box>

                {/* Affected Code Files */}
                {analysis.code_dependencies && analysis.code_dependencies.length > 0 && (
                  <Box mb={2}>
                    <Typography variant="h6" gutterBottom>
                      📝 Affected Code Files ({analysis.code_dependencies.length})
                    </Typography>
                    <ul className="risk-list">
                      {analysis.code_dependencies.map((dep, index) => (
                        <li key={index}>
                          <Typography variant="body2">
                            {dep.file_path} ({dep.usage_count} usages)
                          </Typography>
                        </li>
                      ))}
                    </ul>
                  </Box>
                )}

                {/* Related Tables/Collections */}
                {analysis.affected_tables && analysis.affected_tables.length > 0 && (
                  <Box mb={2}>
                    <Typography variant="h6" gutterBottom>
                      🔗 {isMongoDB ? "Related Collections" : "Related Tables"} ({analysis.affected_tables.length})
                    </Typography>
                    <div className="module-chips">
                      {analysis.affected_tables.map((table, index) => (
                        <Chip
                          key={index}
                          label={table}
                          size="small"
                          variant="outlined"
                          style={{ margin: "0.25rem" }}
                        />
                      ))}
                    </div>
                  </Box>
                )}
              </>
            );
          })()}

          {/* API Contract Change Details */}
          {analysis.type === "api_contract_change" && (
            <>
              {/* API Changes */}
              {analysis.api_changes && analysis.api_changes.length > 0 && (
                <Box mb={3}>
                  <Typography variant="h6" gutterBottom>
                    🔌 API Contract Changes ({analysis.api_changes.length})
                  </Typography>
                  {analysis.api_changes.map((change, index) => (
                    <Box key={index} mb={2} p={2} sx={{ 
                      border: '1px solid #e0e0e0', 
                      borderRadius: 1, 
                      backgroundColor: change.change_type === 'BREAKING' ? '#ffebee' : '#f5f5f5'
                    }}>
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        <Chip 
                          label={change.method || 'N/A'} 
                          size="small" 
                          color="primary"
                          variant="outlined"
                        />
                        <Typography variant="subtitle1" style={{ fontWeight: 'bold' }}>
                          {change.endpoint || 'N/A'}
                        </Typography>
                        <Chip 
                          label={change.change_type || 'UNKNOWN'} 
                          size="small" 
                          color={change.change_type === 'BREAKING' ? 'error' : 
                                 change.change_type === 'MODIFIED' ? 'warning' : 'success'}
                          style={{ marginLeft: 'auto' }}
                        />
                      </Box>
                      {change.details && formatChangeDetails(change.details) && (
                        <Typography variant="body2" color="textSecondary" style={{ marginTop: '0.5rem' }}>
                          {formatChangeDetails(change.details)}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Box>
              )}

              {/* API Consumers */}
              {analysis.consumers && Object.keys(analysis.consumers).length > 0 && (
                <Box mb={3}>
                  <Typography variant="h6" gutterBottom>
                    👥 Affected Consumers ({Object.values(analysis.consumers).reduce((sum, cons) => sum + cons.length, 0)})
                  </Typography>
                  {Object.entries(analysis.consumers).map(([apiKey, consumerList]) => {
                    if (!consumerList || consumerList.length === 0) return null;
                    
                    // Group consumers by repository
                    const byRepo = {};
                    consumerList.forEach(consumer => {
                      const repo = consumer.source_repo || consumer.repository || 'unknown';
                      if (!byRepo[repo]) {
                        byRepo[repo] = [];
                      }
                      byRepo[repo].push(consumer);
                    });
                    
                    return (
                      <Box key={apiKey} mb={2} p={2} sx={{ border: '1px solid #e0e0e0', borderRadius: 1 }}>
                        <Typography variant="subtitle2" gutterBottom style={{ fontWeight: 'bold', color: '#1976d2' }}>
                          {apiKey}
                        </Typography>
                        {Object.entries(byRepo).map(([repo, repoConsumers]) => (
                          <Box key={repo} mt={1.5} mb={1}>
                            <Typography variant="body2" style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
                              📦 Repository: {repo} ({repoConsumers.length} file{repoConsumers.length !== 1 ? 's' : ''})
                            </Typography>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                              {repoConsumers.map((consumer, idx) => (
                                <li key={idx} style={{ marginBottom: '0.5rem' }}>
                                  <Typography variant="body2">
                                    <strong>File:</strong> {consumer.file_path || 'N/A'}
                                    {consumer.line_number > 0 && (
                                      <span style={{ color: '#666', marginLeft: '0.5rem' }}>
                                        (Line {consumer.line_number})
                                      </span>
                                    )}
                                    {consumer.html_url && (
                                      <a 
                                        href={consumer.html_url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        style={{ marginLeft: '0.5rem', color: '#1976d2' }}
                                      >
                                        🔗 View on GitHub
                                      </a>
                                    )}
                                  </Typography>
                                  {consumer.context && (
                                    <Typography variant="caption" color="textSecondary" style={{ 
                                      display: 'block', 
                                      marginLeft: '1rem',
                                      fontFamily: 'monospace',
                                      backgroundColor: '#f5f5f5',
                                      padding: '0.25rem 0.5rem',
                                      borderRadius: '3px',
                                      marginTop: '0.25rem'
                                    }}>
                                      {consumer.context}
                                    </Typography>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </Box>
                        ))}
                      </Box>
                    );
                  })}
                </Box>
              )}

              {/* Summary */}
              {analysis.summary && (
                <Box mb={2} p={2} sx={{ backgroundColor: '#e3f2fd', borderRadius: 1 }}>
                  <Typography variant="h6" gutterBottom>
                    📊 Analysis Summary
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Total Changes:</strong> {analysis.summary.total_changes || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Breaking Changes:</strong> 
                        <span style={{ color: '#dc3545', marginLeft: '0.5rem' }}>
                          {analysis.summary.breaking_changes || 0}
                        </span>
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Total Consumers:</strong> {analysis.summary.total_consumers || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Affected Endpoints:</strong> {analysis.summary.affected_endpoints || 0}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </>
          )}

          {/* Affected Modules (for code changes) */}
          {analysis.type !== "schema_change" && analysis.type !== "api_contract_change" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                📦 Affected Modules ({analysis.affected_modules?.length || 0})
              </Typography>
              {analysis.affected_modules && analysis.affected_modules.length > 0 ? (
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
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No affected modules
                </Typography>
              )}
            </Box>
          )}

          {/* Dependency Graph (for both code and schema changes) */}
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
                fileName={analysis.type === "schema_change" 
                  ? analysis.schema_change?.table_name || "Table"
                  : analysis.file_path?.split("/").pop() || "File"}
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
