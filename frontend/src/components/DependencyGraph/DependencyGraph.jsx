import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Paper, Typography, CircularProgress, Box } from '@mui/material';
import './DependencyGraph.css';

function DependencyGraph({ fileName, dependencies }) {
  const svgRef = useRef();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (dependencies && dependencies.nodes && dependencies.links) {
      renderGraph(dependencies);
      setLoading(false);
    }
  }, [dependencies]);

  const renderGraph = (data) => {
    // Clear any existing SVG content
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 800;
    const height = 600;
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

    // Define arrow markers for links
    svg.append("defs").selectAll("marker")
      .data(["CALLS", "IMPORTS", "READS", "WRITES"])
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

    // Create force simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links)
        .id(d => d.id)
        .distance(100))
      .force("charge", d3.forceManyBody()
        .strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    // Create links
    const link = g.append("g")
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("class", "link")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2)
      .attr("marker-end", d => `url(#arrow-${d.type || 'CALLS'})`);

    // Create link labels
    const linkLabel = g.append("g")
      .selectAll("text")
      .data(data.links)
      .join("text")
      .attr("class", "link-label")
      .attr("font-size", 10)
      .attr("fill", "#666")
      .text(d => d.type || "DEPENDS");

    // Create node groups
    const node = g.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .attr("class", "node")
      .call(drag(simulation));

    // Add circles to nodes
    node.append("circle")
      .attr("r", 20)
      .attr("fill", d => colorScale[d.risk || 'normal'])
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer");

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

    // Add tooltips
    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "d3-tooltip")
      .style("position", "absolute")
      .style("visibility", "hidden")
      .style("background-color", "white")
      .style("border", "1px solid #ddd")
      .style("border-radius", "4px")
      .style("padding", "10px")
      .style("box-shadow", "0 2px 8px rgba(0,0,0,0.2)")
      .style("font-size", "12px")
      .style("z-index", "1000");

    node.on("mouseover", function(event, d) {
      // Highlight connected nodes
      const connectedNodes = new Set();
      data.links.forEach(link => {
        if (link.source.id === d.id) connectedNodes.add(link.target.id);
        if (link.target.id === d.id) connectedNodes.add(link.source.id);
      });

      node.selectAll("circle")
        .attr("opacity", n => 
          n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.2
        );

      link.attr("opacity", l => 
        l.source.id === d.id || l.target.id === d.id ? 1 : 0.1
      );

      // Show tooltip
      tooltip
        .style("visibility", "visible")
        .html(`
          <strong>${d.name}</strong><br/>
          Risk: ${d.risk || 'normal'}<br/>
          ID: ${d.id}
        `);
    })
    .on("mousemove", function(event) {
      tooltip
        .style("top", (event.pageY - 10) + "px")
        .style("left", (event.pageX + 10) + "px");
    })
    .on("mouseout", function() {
      node.selectAll("circle").attr("opacity", 1);
      link.attr("opacity", 1);
      tooltip.style("visibility", "hidden");
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

    // Drag behavior
    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }

      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }

    // Add legend
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${width - 150}, 20)`);

    const legendData = [
      { label: "Source File", color: colorScale.source },
      { label: "Critical", color: colorScale.critical },
      { label: "High Risk", color: colorScale.high },
      { label: "Medium Risk", color: colorScale.medium },
      { label: "Low Risk", color: colorScale.low },
      { label: "Normal", color: colorScale.normal }
    ];

    legendData.forEach((item, i) => {
      const legendRow = legend.append("g")
        .attr("transform", `translate(0, ${i * 25})`);

      legendRow.append("circle")
        .attr("r", 8)
        .attr("fill", item.color);

      legendRow.append("text")
        .attr("x", 15)
        .attr("y", 4)
        .attr("font-size", 12)
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
          Drag nodes to rearrange. Hover for details. Zoom with mouse wheel.
        </Typography>
      </Box>
      <div className="graph-wrapper">
        <svg ref={svgRef}></svg>
      </div>
    </Paper>
  );
}

export default DependencyGraph;