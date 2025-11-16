import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { 
  Paper, 
  Typography, 
  CircularProgress, 
  Box, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import './DependencyGraph.css';

function DependencyGraph({ fileName, dependencies }) {
  const svgRef = useRef();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [nodeConnections, setNodeConnections] = useState([]);

  useEffect(() => {
    if (dependencies && dependencies.nodes && dependencies.links) {
      renderGraph(dependencies);
      setLoading(false);
    }
  }, [dependencies]);

  const renderGraph = (data) => {
    // Clear any existing SVG content
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 1200;  // Wider for better visibility
    const height = 800;  // Taller for better visibility
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append("g");
    
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    
    svg.call(zoom);

    const linkTypes = [
      "CALL", "USE", "IMPORT", "CREATE", "EXTEND", "IMPLEMENT",
      "CALLS", "IMPORTS", "READS", "WRITES", "DEPENDS_ON", "CONTAIN"
    ];
    // Define arrow markers for links
    svg.append("defs").selectAll("marker")
      .data(linkTypes)
      .join("marker")
      .attr("id", d => `arrow-${d}`)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // Color scale for nodes based on risk level
    const colorScale = {
      'source': '#667eea',
      'critical': '#dc3545',
      'high': '#fd7e14',
      'medium': '#ffc107',
      'low': '#28a745',
      'normal': '#6c757d'
    };

    // Create node map for quick lookup
    const nodeMap = new Map(data.nodes.map(n => [n.id, n]));
    
    // Convert link source/target from string to object reference
    const processedLinks = data.links.map(link => ({
      ...link,
      source: typeof link.source === 'string' ? nodeMap.get(link.source) : link.source,
      target: typeof link.target === 'string' ? nodeMap.get(link.target) : link.target
    })).filter(link => link.source && link.target); // Filter out invalid links

    // Create force simulation with better spacing
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(processedLinks)
        .id(d => d.id)
        .distance(150))  // Increased distance for better spacing
      .force("charge", d3.forceManyBody()
        .strength(-800))  // Stronger repulsion to prevent overlap
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50))  // Larger collision radius
      .alphaDecay(0.02)  // Slower decay for smoother animation
      .velocityDecay(0.4);  // More damping for stability

    // Create links
    const link = g.append("g")
      .selectAll("line")
      .data(processedLinks)
      .join("line")
      .attr("class", "link")
      .attr("stroke", d => d.direction === "reverse" ? "#ff6b6b" : "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", d => d.distance === 1 ? 3 : 2)
      .attr("stroke-dasharray", d => d.direction === "reverse" ? "5,5" : "none")
      .attr("marker-end", d => `url(#arrow-${d.type || 'CALLS'})`);

    // Create link labels
    const linkLabel = g.append("g")
      .selectAll("text")
      .data(processedLinks)
      .join("text")
      .attr("class", "link-label")
      .attr("font-size", 10)
      .attr("fill", "#333")
      .attr("font-weight", "bold")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 3)
      .attr("paint-order", "stroke")
      .attr("dy", -5)
      .attr("text-anchor", "middle")
      .text(d => d.type || "DEPENDS");

    // Create node groups
    const node = g.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .attr("class", "node")
      .call(drag(simulation));

    // Add circles to nodes with larger clickable area
    node.append("circle")
      .attr("r", 25)  // Larger radius for easier interaction
      .attr("fill", d => colorScale[d.risk || 'normal'])
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "grab")
      .style("pointer-events", "all");  // Ensure clickable
    
    // Add invisible larger circle for easier dragging
    node.append("circle")
      .attr("r", 35)  // Larger invisible area for dragging
      .attr("fill", "transparent")
      .style("cursor", "grab");

    // Add labels to nodes
    node.append("text")
      .attr("dy", 35)
      .attr("text-anchor", "middle")
      .attr("font-size", 12)
      .attr("font-weight", d => d.risk === 'source' ? 'bold' : 'normal')
      .text(d => {
        // Show short name (remove .java extension and path)
        const name = d.name.split('/').pop().replace('.java', '');
        return name.length > 15 ? name.substring(0, 12) + '...' : name;
      })
      .style("pointer-events", "none");

    // Node click handler - show popup with code details
    node.on("click", function(event, d) {
      event.stopPropagation();
      
      // Collect and group connections for this node
      const connectionMap = new Map();
      
      processedLinks.forEach(link => {
        const linkSource = link.source.id || link.source;
        const linkTarget = link.target.id || link.target;
        
        if (linkSource === d.id || linkTarget === d.id) {
          const otherNode = linkSource === d.id ? linkTarget : linkSource;
          const direction = linkSource === d.id ? 'forward' : 'reverse';
          
          // Clean up type (remove trailing 0 or numbers)
          let cleanType = (link.type || 'DEPENDS_ON').replace(/0+$/, '').replace(/^\d+/, '');
          if (!cleanType || cleanType === '0') cleanType = 'DEPENDS_ON';
          
          // Create unique key for grouping
          const key = `${otherNode}|${direction}|${cleanType}`;
          
          if (!connectionMap.has(key)) {
            connectionMap.set(key, {
              otherNode: otherNode,
              direction: direction,
              type: cleanType,
              lineNumbers: [],
              codeReferences: [],
              count: 0
            });
          }
          
          const conn = connectionMap.get(key);
          conn.count += 1;
          
          // Collect line numbers
          if (link.line_number) {
            const lineNum = Array.isArray(link.line_number) 
              ? link.line_number[0] 
              : link.line_number;
            if (lineNum && lineNum !== 0 && !conn.lineNumbers.includes(lineNum)) {
              conn.lineNumbers.push(lineNum);
            }
          }
          
          // Collect code references
          if (link.code_reference) {
            const codeRef = Array.isArray(link.code_reference) 
              ? link.code_reference[0] 
              : link.code_reference;
            if (codeRef && codeRef.trim() && !conn.codeReferences.includes(codeRef)) {
              conn.codeReferences.push(codeRef);
            }
          }
        }
      });

      // Convert map to array and sort by otherNode name
      const groupedConnections = Array.from(connectionMap.values())
        .sort((a, b) => a.otherNode.localeCompare(b.otherNode));

      setSelectedNode(d);
      setNodeConnections(groupedConnections);
      setDialogOpen(true);
    });

    // Hover effect for visual feedback
    node.on("mouseover", function(event, d) {
      // Highlight connected nodes
      const connectedNodes = new Set();
      
      processedLinks.forEach(link => {
        const linkSource = link.source.id || link.source;
        const linkTarget = link.target.id || link.target;
        
        if (linkSource === d.id) {
          connectedNodes.add(linkTarget);
        }
        if (linkTarget === d.id) {
          connectedNodes.add(linkSource);
        }
      });

      node.selectAll("circle")
        .attr("opacity", n => 
          n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3
        );

      link.attr("opacity", l => {
        const lSource = l.source.id || l.source;
        const lTarget = l.target.id || l.target;
        return lSource === d.id || lTarget === d.id ? 1 : 0.1;
      });
    })
    .on("mouseout", function() {
      node.selectAll("circle").attr("opacity", 1);
      link.attr("opacity", 1);
    });

    // Link hover - show code reference
    link.append("title")
      .text(d => {
        let text = `${d.type || 'DEPENDS_ON'}`;
        if (d.line_number) {
          text += `\nLine: ${d.line_number}`;
        }
        if (d.code_reference) {
          text += `\n${d.code_reference.substring(0, 100)}`;
        }
        return text;
      });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      linkLabel
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);

      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Enhanced drag behavior with better control
    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) {
          simulation.alphaTarget(0.3).restart();
        }
        // Fix the node position when dragging starts
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
        // Change cursor to grabbing
        d3.select(event.sourceEvent.target).style("cursor", "grabbing");
      }

      function dragged(event) {
        // Update fixed position during drag
        event.subject.fx = event.x;
        event.subject.fy = event.y;
        // Restart simulation to update positions
        simulation.alpha(0.3).restart();
      }

      function dragended(event) {
        if (!event.active) {
          simulation.alphaTarget(0);
        }
        // Keep the node at its dragged position (don't release)
        // This allows users to manually position nodes
        // Uncomment the next two lines if you want nodes to return to force layout after drag
        // event.subject.fx = null;
        // event.subject.fy = null;
        // Change cursor back
        d3.select(event.sourceEvent.target).style("cursor", "grab");
      }

      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }

    // Add legend
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${width - 180}, 20)`);

    const legendData = [
      { label: "Source File", color: colorScale.source, type: "node" },
      { label: "Critical", color: colorScale.critical, type: "node" },
      { label: "High Risk", color: colorScale.high, type: "node" },
      { label: "Medium Risk", color: colorScale.medium, type: "node" },
      { label: "Low Risk", color: colorScale.low, type: "node" },
      { label: "Normal", color: colorScale.normal, type: "node" },
      { label: "Forward Dep", color: "#999", type: "link", dash: "none" },
      { label: "Reverse Dep", color: "#ff6b6b", type: "link", dash: "5,5" }
    ];

    legendData.forEach((item, i) => {
      const legendRow = legend.append("g")
        .attr("transform", `translate(0, ${i * 25})`);

      if (item.type === "node") {
        legendRow.append("circle")
          .attr("r", 8)
          .attr("fill", item.color);
      } else {
        // Link legend
        const line = legendRow.append("line")
          .attr("x1", 0)
          .attr("y1", 0)
          .attr("x2", 16)
          .attr("y2", 0)
          .attr("stroke", item.color)
          .attr("stroke-width", 2)
          .attr("stroke-dasharray", item.dash || "none");
      }

      legendRow.append("text")
        .attr("x", item.type === "node" ? 15 : 20)
        .attr("y", 4)
        .attr("font-size", 11)
        .text(item.label);
    });
  };

  if (loading && !dependencies) {
    return (
      <Paper className="graph-container" elevation={3}>
        <Box textAlign="center" p={4}>
          <CircularProgress />
          <Typography mt={2}>Loading dependency graph...</Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper className="graph-container" elevation={3}>
        <Box textAlign="center" p={4}>
          <Typography color="error">Error loading graph: {error}</Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper className="graph-container" elevation={3}>
      <Box p={2}>
        <Typography variant="h6" gutterBottom>
          📊 Dependency Graph: {fileName}
        </Typography>
        <Typography variant="caption" color="textSecondary" gutterBottom>
          <strong>💡 Tips:</strong> 
          <br/>• <strong>Drag nodes</strong> to freely reposition them - nodes stay where you place them
          <br/>• <strong>Click nodes</strong> to view detailed code dependencies
          <br/>• <strong>Mouse wheel</strong> to zoom in/out
          <br/>• <strong>Pan</strong> by dragging the background
          <br/>
          <span style={{color: '#999'}}>Solid lines</span> = Forward dependencies | 
          <span style={{color: '#ff6b6b'}}>Dashed red</span> = Reverse dependencies
        </Typography>
      </Box>
      <div className="graph-wrapper">
        <svg ref={svgRef}></svg>
      </div>

      {/* Node Details Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {selectedNode?.name || 'Node Details'}
            </Typography>
            <Button onClick={() => setDialogOpen(false)} size="small">
              <CloseIcon />
            </Button>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedNode && (
            <Box>
              {/* Node Info */}
              <Box mb={2}>
                <Chip 
                  label={`Risk: ${selectedNode.risk || 'normal'}`}
                  color={
                    selectedNode.risk === 'critical' ? 'error' :
                    selectedNode.risk === 'high' ? 'warning' :
                    selectedNode.risk === 'medium' ? 'info' :
                    selectedNode.risk === 'low' ? 'success' : 'default'
                  }
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Chip 
                  label={selectedNode.risk === 'source' ? 'Source File' : 'Dependent Module'}
                  variant="outlined"
                  size="small"
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Connections List */}
              <Typography variant="subtitle1" gutterBottom>
                <strong>Code Dependencies ({nodeConnections.length} unique connections)</strong>
              </Typography>
              
              {/* Dependency Type Legend */}
              <Box mb={2} p={1.5} bgcolor="#f0f7ff" borderRadius={1}>
                <Typography variant="caption" fontWeight="bold" display="block" mb={0.5}>
                  Dependency Types:
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.5}>
                  <Chip label="CALL: Method/function call" size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                  <Chip label="IMPORT: Import statement" size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                  <Chip label="USE: Variable/field usage" size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                  <Chip label="CREATE: Object instantiation" size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                  <Chip label="CONTAIN: Contains/nested" size="small" sx={{ fontSize: '0.65rem', height: '18px' }} />
                </Box>
              </Box>
              
              {nodeConnections.length === 0 ? (
                <Typography variant="body2" color="textSecondary">
                  No dependencies found for this module.
                </Typography>
              ) : (
                <List>
                  {nodeConnections.map((conn, index) => {
                    const getTypeDescription = (type) => {
                      const descriptions = {
                        'CALL': 'Method/function call',
                        'IMPORT': 'Import statement',
                        'USE': 'Variable/field usage',
                        'CREATE': 'Object instantiation',
                        'CONTAIN': 'Contains/nested relationship',
                        'EXTEND': 'Class extension',
                        'IMPLEMENT': 'Interface implementation',
                        'DEPENDS_ON': 'General dependency'
                      };
                      return descriptions[type] || type;
                    };
                    
                    return (
                      <ListItem 
                        key={index}
                        sx={{
                          borderLeft: `3px solid ${conn.direction === 'reverse' ? '#ff6b6b' : '#999'}`,
                          mb: 1.5,
                          bgcolor: '#f9f9f9',
                          borderRadius: 1,
                          flexDirection: 'column',
                          alignItems: 'flex-start'
                        }}
                      >
                        <Box width="100%">
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <Typography variant="body2" fontWeight="bold">
                              {conn.direction === 'reverse' ? '←' : '→'} {conn.otherNode}
                            </Typography>
                            {/* <Chip 
                              label={conn.direction === 'reverse' ? 'Depends on this' : 'This depends on'}
                              size="small"
                              variant="outlined"
                              color={conn.direction === 'reverse' ? 'error' : 'default'}
                              sx={{ fontSize: '0.7rem', height: '20px' }}
                            /> */}
                            {conn.count > 1 && (
                              <Chip 
                                label={`${conn.count}x`}
                                size="small"
                                sx={{ fontSize: '0.65rem', height: '18px', bgcolor: '#e3f2fd' }}
                              />
                            )}
                          </Box>
                          
                          <Box ml={1}>
                            <Typography variant="caption" display="block" color="textSecondary" mb={0.5}>
                              <strong>Type:</strong> {conn.type} - {getTypeDescription(conn.type)}
                            </Typography>
                            
                            {conn.lineNumbers.length > 0 && (
                              <Typography variant="caption" display="block" color="textSecondary" mb={0.5}>
                                <strong>Line(s):</strong> {conn.lineNumbers.sort((a, b) => a - b).join(', ')}
                              </Typography>
                            )}
                            
                            {conn.codeReferences.length > 0 && (
                              <Box mt={1}>
                                {conn.codeReferences.slice(0, 2).map((codeRef, refIdx) => (
                                  <Box 
                                    key={refIdx}
                                    mt={refIdx > 0 ? 1 : 0}
                                    p={1} 
                                    bgcolor="#f5f5f5" 
                                    borderRadius={1}
                                    sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                                  >
                                    <Typography variant="caption" component="pre" sx={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                      {codeRef.length > 200 ? codeRef.substring(0, 200) + '...' : codeRef}
                                    </Typography>
                                  </Box>
                                ))}
                                {conn.codeReferences.length > 2 && (
                                  <Typography variant="caption" color="textSecondary" mt={0.5}>
                                    + {conn.codeReferences.length - 2} more code references
                                  </Typography>
                                )}
                              </Box>
                            )}
                            
                            {conn.lineNumbers.length === 0 && conn.codeReferences.length === 0 && (
                              <Typography variant="caption" color="textSecondary" fontStyle="italic">
                                No line numbers or code references available
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </ListItem>
                    );
                  })}
                </List>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default DependencyGraph;