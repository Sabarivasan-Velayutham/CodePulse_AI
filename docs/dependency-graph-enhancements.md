# Dependency Graph Enhancements

## Summary
Enhanced the dependency graph visualization to show **both direct and indirect dependencies** (including reverse dependencies) with **code references and line numbers** in hover tooltips.

## Changes Made

### Backend Changes

#### 1. `backend/app/services/depends_wrapper.py`
- **Added reverse dependency detection**: Now finds files that depend ON the changed file (not just files the changed file depends on)
- Added `reverse_direct_dependencies` and `reverse_indirect_dependencies` to the analysis result

#### 2. `backend/app/utils/neo4j_client.py`
- **Enhanced `create_dependency()`**: Now stores `line_number` and `code_reference` in Neo4j relationships
- **Enhanced `get_dependencies()`**: 
  - Now queries BOTH forward and reverse dependencies
  - Returns line numbers and code references from relationships
  - Handles None values and arrays properly

#### 3. `backend/app/engine/orchestrator.py`
- **Enhanced `_store_in_neo4j()`**: 
  - Stores both direct AND indirect dependencies (forward and reverse)
  - Stores line numbers and code references
- **Enhanced `_compile_results()`**: 
  - Includes reverse dependencies in the result
  - Updates affected_modules to include reverse dependencies

#### 4. `backend/app/api/analysis.py`
- **Enhanced `get_dependency_graph()`**: 
  - Returns both forward and reverse dependencies
  - Includes line numbers and code references in links
  - Sets risk levels based on distance and direction
  - Properly handles link source/target for visualization

### Frontend Changes

#### 1. `frontend/src/components/DependencyGraph/DependencyGraph.jsx`
- **Enhanced tooltips**: 
  - Shows all connections (forward and reverse) when hovering over a node
  - Displays line numbers and code references
  - Shows direction indicators (→ for forward, ← for reverse)
  - Color-coded borders (red for reverse dependencies)
- **Visual improvements**:
  - Reverse dependencies shown with **dashed red lines**
  - Forward dependencies shown with **solid gray lines**
  - Thicker lines for direct dependencies (distance = 1)
- **Enhanced legend**: Shows both node types and link types (forward vs reverse)

#### 2. `frontend/src/components/AnalysisCard/AnalysisCard.jsx`
- **Added reverse dependencies count**: Shows total reverse dependencies in the stats section

#### 3. `frontend/src/components/DependencyGraph/DependencyGraph.css`
- **Enhanced tooltip styling**: Better formatting for code references

## How It Works

### Dependency Detection Flow

1. **Analysis Phase**:
   - DEPENDS tool analyzes the entire codebase
   - Finds all dependencies (forward and reverse)
   - Stores in Neo4j with line numbers and code references

2. **Graph Generation**:
   - Backend queries Neo4j for both forward and reverse dependencies
   - Returns nodes and links with metadata (line numbers, code references)
   - Frontend visualizes with different colors/styles for forward vs reverse

3. **Visualization**:
   - **Forward dependencies** (changed file → other files): Solid gray lines
   - **Reverse dependencies** (other files → changed file): Dashed red lines
   - Hover over any node to see:
     - All connected files
     - Dependency type (CALLS, IMPORTS, etc.)
     - Line numbers where the dependency occurs
     - Code references (snippet of the actual code)

## Example Graph Structure

For `AccountBalance.java` change:

```
AccountBalance.java (source node - blue)
    ↓ (solid gray line)
TransactionDAO.java (direct dependency)
    ↑ (dashed red line)
PaymentProcessor.java (reverse dependency - depends on AccountBalance)
    ↑ (dashed red line)
FraudDetection.java (indirect reverse - through PaymentProcessor)
```

## Hover Tooltip Example

When hovering over `AccountBalance.java`:
```
AccountBalance.java
● Risk: source

─────────────────────
Connections (3):
→ TransactionDAO.java (this depends on)
  Type: CALLS
  Line: 14

← PaymentProcessor.java (depends on this)
  Type: CALLS
  Line: 73
  accountBalance.getBalance(payment.getAccountId())

← OverdraftManager.java (depends on this)
  Type: CALLS
  Line: 45
```

## Benefits

1. **Complete Dependency View**: See both what the file depends on AND what depends on it
2. **Code Context**: Hover to see exactly where and how dependencies are used
3. **Better Impact Analysis**: Understand the full scope of changes
4. **Visual Clarity**: Different line styles make forward vs reverse dependencies clear

## Testing

After these changes:
1. Run a new analysis on any file (e.g., AccountBalance.java)
2. Expand the analysis card to see the dependency graph
3. Hover over nodes to see code references
4. Verify that reverse dependencies appear (dashed red lines pointing TO the changed file)

