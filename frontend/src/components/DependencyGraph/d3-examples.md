# D3.js Graph Examples for Reference


# STEP 1: Visit D3.js Gallery
# Open browser: https://d3-graph-gallery.com/network.html

# STEP 2: Bookmark these specific examples:
# 1. Basic Network Graph
https://d3-graph-gallery.com/graph/network_basic.html

# 2. Force-Directed Graph
https://d3-graph-gallery.com/graph/network_interactive.html

# 3. Network with Color
https://d3-graph-gallery.com/graph/network_color.html

# STEP 3: Download example code
# Create a notes file for reference


## Basic Force Graph
Source: https://d3-graph-gallery.com/graph/network_basic.html

Key concepts:
- d3.forceSimulation() - Creates physics simulation
- d3.forceLink() - Links between nodes
- d3.forceManyBody() - Repulsion between nodes
- d3.forceCenter() - Centers the graph

## Implementation notes:
- Nodes = code modules
- Links = dependencies
- Color code by risk level
- Size by importance

## Example data format:
```json
{
  "nodes": [
    {"id": "PaymentProcessor", "risk": "high"},
    {"id": "FraudDetection", "risk": "critical"}
  ],
  "links": [
    {"source": "PaymentProcessor", "target": "FraudDetection", "type": "CALLS"}
  ]
}