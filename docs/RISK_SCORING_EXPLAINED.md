# Risk Scoring System - Detailed Explanation

## Overview

The CodePulse AI risk scoring system provides a comprehensive assessment of the risk associated with code changes and database schema modifications. The score ranges from **0 to 10**, with higher scores indicating greater risk.

## How Risk Scores Are Calculated

### For Code Changes

The risk score is calculated using four main components:

#### 1. Technical Risk (0-4 points)
**What it measures:** Code complexity, dependency count, and change size.

**Factors considered:**
- **Dependency Count:** Total number of direct and indirect dependencies
  - >20 dependencies: +2.0 points (very high complexity)
  - 10-20 dependencies: +1.5 points (high complexity)
  - 5-10 dependencies: +1.0 point (moderate complexity)
  - <5 dependencies: +0.5 points (low complexity)

- **Cyclomatic Complexity:** Code complexity metric
  - >15: +1.5 points (very hard to test and maintain)
  - 10-15: +1.0 point (increases testing difficulty)
  - 5-10: +0.5 points (acceptable but should be monitored)

- **Lines Changed:** Size of the change
  - >100 lines: +0.5 points (higher bug risk)
  - 50-100 lines: +0.3 points (requires careful review)

**Why it matters:** Higher complexity increases the likelihood of bugs and makes changes harder to review and test.

#### 2. Domain Risk (0-3 points)
**What it measures:** Business impact based on file criticality, affected critical modules, and database interactions.

**Factors considered:**
- **File Criticality:** Whether the file contains critical banking keywords
  - Contains keywords (payment, transaction, fraud, etc.): +0.5 points

- **Critical Modules Affected:** Number of critical modules in the dependency chain
  - ≥3 critical modules: +2.0 points (high business impact)
  - 2 critical modules: +1.5 points (requires coordination)
  - 1 critical module: +1.0 point (moderate impact)

- **Database Interactions:** Direct database access
  - Database layer interaction: +0.5 points
  - >5 tables accessed: +1.0 point (high data consistency risk)
  - 2-5 tables: +0.5 points (moderate risk)
  - 1-2 tables: +0.3 points (lower risk)

**Why it matters:** Banking systems require extra caution for financial data integrity. Changes to critical modules can impact multiple sensitive systems.

#### 3. AI Analysis Risk (0-2 points)
**What it measures:** Potential issues identified by AI analysis that may not be obvious from code structure.

**Factors considered:**
- **Number of Risks Identified:**
  - ≥4 risks: +1.5 points (comprehensive review required)
  - 2-3 risks: +1.0 point (careful review recommended)
  - 1 risk: +0.5 points (standard review process)

- **Regulatory Concerns:**
  - Regulatory issues detected: +0.5 points (legal/compliance review needed)

**Why it matters:** AI can identify security concerns, compliance risks, and potential issues that static analysis might miss.

#### 4. Temporal Risk (Multiplier: 1.0-2.0x)
**What it measures:** Risk based on when the change is being deployed.

**Factors considered:**
- **Friday Afternoon (after 2 PM):** ×1.3 (limited rollback time)
- **Month-End (day 28+):** ×1.2 (critical for financial reporting)
- **Quarter-End (March/June/September/December, day 28+):** ×1.5 (highest risk period)

**Why it matters:** Banking systems are particularly sensitive during reporting periods. Deploying during these times increases risk if issues occur.

**Final Calculation:**
```
Base Score = Technical Risk + Domain Risk + AI Analysis Risk
Final Score = Base Score × Temporal Multiplier (capped at 10.0)
```

### For Schema Changes

The risk score uses four components specific to database schema modifications:

#### 1. Table Criticality Risk (0-3 points)
**What it measures:** Importance of the table and its interconnectedness.

**Factors considered:**
- **Table Type:**
  - Critical tables (transactions, payments, accounts, etc.): 2.5 base points
  - Standard tables: 1.5 base points

- **Interconnectedness:**
  - >5 relationships: +0.5 points (high cascade risk)
  - 2-5 relationships: +0.3 points (moderate cascade risk)

**Why it matters:** Critical tables handle sensitive financial operations. Highly interconnected tables can cause cascading failures.

#### 2. Code Impact Risk (0-3 points)
**What it measures:** How many code files and usages are affected by the schema change.

**Factors considered:**
- **Affected Files:**
  - >10 files: 3.0 points (extensive testing required)
  - 5-10 files: 2.0 points (thorough testing recommended)
  - 2-5 files: 1.5 points (standard testing process)
  - 1 file: 1.0 point (minimal testing needed)
  - 0 files: 0 points (database migration testing only)

- **Total Usages:**
  - Column-specific change with >20 usages: +0.5 points (high breaking change risk)

**Why it matters:** More affected code means higher risk of breaking changes. Schema changes can break existing queries and application logic.

#### 3. Database Relationship Risk (0-2 points)
**What it measures:** How interconnected the table is with other tables.

**Factors considered:**
- **Reverse Relationships (tables that depend on this):**
  - >5 dependent tables: 2.0 points (high cascade risk)
  - 2-5 dependent tables: 1.5 points (moderate cascade risk)
  - 1 dependent table: 1.0 point (low cascade risk)
  - 0 dependent tables: 0 points (isolated change)

- **Forward Relationships (tables this depends on):**
  - >3 dependencies: +0.5 points (data integrity risk)

**Why it matters:** Tables with many dependencies have higher risk of cascading failures. Changes can break dependent tables and affect data integrity.

#### 4. AI Analysis Risk (0-2 points)
Same as code changes - uses AI to identify potential issues.

**Final Calculation:**
```
Base Score = Table Criticality + Code Impact + DB Relationships + AI Analysis
Final Score = Base Score × 1.25 (scaled to 0-10)
```

## Risk Level Classification

| Score Range | Level | Color | Meaning |
|------------|-------|-------|---------|
| 0.0 - 3.5 | LOW | 🟢 Green | Low risk, standard review process |
| 3.5 - 5.5 | MEDIUM | 🟡 Yellow | Moderate risk, careful review recommended |
| 5.5 - 7.5 | HIGH | 🟠 Orange | High risk, thorough review and testing required |
| 7.5 - 10.0 | CRITICAL | 🔴 Red | Critical risk, comprehensive review and approval needed |

## How to View Detailed Explanations

In the frontend dashboard:

1. **Expand the Analysis Card** - Click "Show Details" on any analysis card
2. **View Risk Score Section** - Scroll to the Risk Score component
3. **Expand Components** - Click on any risk component (Technical Risk, Domain Risk, etc.) to see:
   - **Description:** What this component measures
   - **Contributing Factors:** Specific metrics that contributed to the score
   - **Why This Score:** Detailed explanations for each contributing factor
   - **Score Breakdown:** The exact score and maximum possible

## How the System Can Be Improved

### 1. **Historical Data Integration**
- Track past incidents and failures
- Learn from previous high-risk changes that caused issues
- Adjust scoring based on team's historical risk patterns

### 2. **Team-Specific Customization**
- Allow teams to define their own critical keywords
- Customize risk thresholds based on team experience
- Adjust temporal risk based on team's deployment schedule

### 3. **Test Coverage Analysis**
- Factor in test coverage for affected code
- Higher test coverage = lower risk
- Missing tests for critical paths = higher risk

### 4. **Code Review History**
- Consider reviewer experience and past review quality
- Factor in review turnaround time
- Account for number of reviewers required

### 5. **Deployment Environment**
- Production vs. staging vs. development
- Blue-green deployment availability
- Rollback capability assessment

### 6. **Business Impact Scoring**
- Integrate with business metrics (revenue impact, user impact)
- Consider peak usage times
- Factor in customer-facing vs. internal systems

### 7. **Machine Learning Enhancement**
- Train models on historical incident data
- Continuously improve AI risk detection
- Learn from false positives/negatives

### 8. **Integration with CI/CD**
- Real-time risk assessment during PR creation
- Block high-risk changes from merging
- Require additional approvals for critical changes

### 9. **Dependency Health**
- Check health of external dependencies
- Factor in dependency update frequency
- Consider security vulnerabilities in dependencies

### 10. **Code Quality Metrics**
- Code smells detection
- Technical debt assessment
- Code duplication analysis

## Current Limitations

1. **Static Analysis Only:** Currently focuses on code structure, not runtime behavior
2. **No Historical Context:** Doesn't learn from past incidents
3. **Generic Banking Focus:** Optimized for banking but could be more domain-agnostic
4. **Limited Test Coverage:** Doesn't factor in test coverage or quality
5. **No Team Customization:** Same scoring for all teams regardless of experience

## Best Practices for Using Risk Scores

1. **Use as a Guide, Not a Gate:** Risk scores help prioritize reviews but shouldn't block all high-risk changes
2. **Review Explanations:** Always check the detailed explanations to understand why a score is high
3. **Consider Context:** A high score doesn't always mean "don't deploy" - consider business needs
4. **Continuous Improvement:** Use risk scores to identify areas for code quality improvement
5. **Team Discussion:** Use scores to facilitate team discussions about risk and mitigation strategies

## Example: Understanding a High Risk Score

**Scenario:** A change to `PaymentProcessor.java` gets a score of 7.8 (CRITICAL)

**Breakdown:**
- Technical Risk: 3.2/4 (15 dependencies, complexity 12, 80 lines changed)
- Domain Risk: 2.8/3 (critical file, 3 critical modules affected, 4 database tables)
- AI Analysis: 1.5/2 (3 risks identified, regulatory concerns)
- Temporal: 1.0x (standard deployment window)

**What this means:**
- The change affects many dependencies and has high complexity
- It touches critical payment processing logic
- AI identified potential security and compliance issues
- Requires comprehensive review, extensive testing, and possibly additional approvals

**Action Items:**
1. Review all affected dependencies
2. Conduct thorough security review
3. Test with realistic payment scenarios
4. Get compliance team approval
5. Plan rollback strategy
6. Consider deploying during low-traffic period

