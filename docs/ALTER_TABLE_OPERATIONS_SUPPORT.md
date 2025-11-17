# ALTER TABLE Operations Support

This document lists all the ALTER TABLE operations that are now supported by the schema change analysis system.

## Supported Operations

### Column Operations

#### 1. ADD COLUMN ✅
```sql
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
```
- **Change Type**: `ADD_COLUMN`
- **Risk Score**: 1.0 (Low-Medium)
- **Detection**: Regex + System Catalog (if SQL incomplete)

#### 2. DROP COLUMN ✅
```sql
ALTER TABLE transactions DROP COLUMN currency;
```
- **Change Type**: `DROP_COLUMN`
- **Risk Score**: 3.0 (Critical)
- **Detection**: PostgreSQL trigger `pg_event_trigger_dropped_objects()` + Regex

#### 3. MODIFY COLUMN TYPE ✅
```sql
-- PostgreSQL syntax
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);

-- MySQL syntax
ALTER TABLE transactions MODIFY COLUMN amount DECIMAL(20, 4);
```
- **Change Type**: `MODIFY_COLUMN`
- **Risk Score**: 2.5 (High)
- **Detection**: Regex pattern matching

#### 4. RENAME COLUMN ✅
```sql
ALTER TABLE transactions RENAME COLUMN old_name TO new_name;
```
- **Change Type**: `RENAME_COLUMN`
- **Risk Score**: 2.5 (High)
- **Detection**: Regex pattern matching

#### 5. SET DEFAULT ✅
```sql
ALTER TABLE transactions ALTER COLUMN amount SET DEFAULT 0.00;
```
- **Change Type**: `SET_DEFAULT`
- **Risk Score**: 1.2 (Low-Medium)
- **Detection**: Regex pattern matching

#### 6. DROP DEFAULT ✅
```sql
ALTER TABLE transactions ALTER COLUMN amount DROP DEFAULT;
```
- **Change Type**: `DROP_DEFAULT`
- **Risk Score**: 1.5 (Medium)
- **Detection**: Regex pattern matching

#### 7. SET NOT NULL ✅
```sql
ALTER TABLE transactions ALTER COLUMN amount SET NOT NULL;
```
- **Change Type**: `SET_NOT_NULL`
- **Risk Score**: 2.2 (High)
- **Detection**: Regex pattern matching
- **Note**: May fail if existing rows have NULL values

#### 8. DROP NOT NULL ✅
```sql
ALTER TABLE transactions ALTER COLUMN amount DROP NOT NULL;
```
- **Change Type**: `DROP_NOT_NULL`
- **Risk Score**: 1.8 (Medium-High)
- **Detection**: Regex pattern matching

### Constraint Operations

#### 9. ADD CONSTRAINT ✅
```sql
-- Primary Key
ALTER TABLE transactions ADD CONSTRAINT pk_transactions PRIMARY KEY (id);

-- Foreign Key
ALTER TABLE transactions ADD CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(id);

-- Unique
ALTER TABLE transactions ADD CONSTRAINT uk_transaction_code UNIQUE (transaction_code);

-- Check
ALTER TABLE transactions ADD CONSTRAINT chk_amount CHECK (amount > 0);
```
- **Change Type**: `ADD_CONSTRAINT`
- **Risk Score**: 2.0 (Medium-High)
- **Detection**: Regex pattern matching + constraint type detection
- **Note**: May fail if existing data violates the constraint

#### 10. DROP CONSTRAINT ✅
```sql
ALTER TABLE transactions DROP CONSTRAINT fk_account;
```
- **Change Type**: `DROP_CONSTRAINT`
- **Risk Score**: 2.8 (Very High)
- **Detection**: Regex pattern matching
- **Note**: High risk - removes data integrity constraints

### Table Operations

#### 11. RENAME TABLE ✅
```sql
ALTER TABLE transactions RENAME TO payment_transactions;
```
- **Change Type**: `RENAME_TABLE`
- **Risk Score**: 2.8 (Very High)
- **Detection**: Regex pattern matching
- **Note**: Breaking change - all code references need updating

#### 12. DROP TABLE ✅
```sql
DROP TABLE transactions;
```
- **Change Type**: `DROP_TABLE`
- **Risk Score**: 3.0 (Critical)
- **Detection**: Regex pattern matching
- **Note**: Highest risk - permanent data loss

### Index Operations

#### 13. ADD INDEX ✅
```sql
CREATE INDEX idx_transaction_date ON transactions(transaction_date);
CREATE UNIQUE INDEX idx_transaction_code ON transactions(transaction_code);
```
- **Change Type**: `ADD_INDEX`
- **Risk Score**: 0.8 (Low)
- **Detection**: Regex pattern matching
- **Note**: Low risk - performance improvement

#### 14. DROP INDEX ✅
```sql
DROP INDEX idx_transaction_date;
DROP INDEX IF EXISTS idx_transaction_date;
```
- **Change Type**: `DROP_INDEX`
- **Risk Score**: 1.5 (Medium-High)
- **Detection**: Regex pattern matching
- **Note**: Performance impact - queries may slow down

## Risk Score Summary

| Operation | Risk Score | Level |
|-----------|-----------|-------|
| DROP_TABLE | 3.0 | CRITICAL |
| DROP_COLUMN | 3.0 | CRITICAL |
| DROP_CONSTRAINT | 2.8 | CRITICAL |
| RENAME_TABLE | 2.8 | CRITICAL |
| MODIFY_COLUMN | 2.5 | HIGH |
| RENAME_COLUMN | 2.5 | HIGH |
| SET_NOT_NULL | 2.2 | HIGH |
| ADD_CONSTRAINT | 2.0 | MEDIUM |
| ALTER_TABLE (generic) | 2.0 | MEDIUM |
| DROP_NOT_NULL | 1.8 | MEDIUM |
| DROP_INDEX | 1.5 | MEDIUM |
| DROP_DEFAULT | 1.5 | MEDIUM |
| SET_DEFAULT | 1.2 | LOW |
| ADD_COLUMN | 1.0 | LOW |
| ADD_INDEX | 0.8 | LOW |

## Detection Methods

### 1. Direct SQL Parsing (Primary)
- Uses regex patterns to extract operation details from complete SQL statements
- Most accurate method when full SQL is available

### 2. PostgreSQL Trigger Enhancement
- For `DROP COLUMN`: Uses `pg_event_trigger_dropped_objects()` to get exact column name
- Reconstructs complete SQL from trigger payload

### 3. System Catalog Query (Fallback)
- For incomplete SQL (e.g., `ALTER TABLE public.transactions...`)
- Queries PostgreSQL system catalogs (`pg_attribute`, `pg_class`) to detect `ADD_COLUMN`
- Only used when `DROP` keyword is not present in SQL

### 4. Generic ALTER_TABLE (Last Resort)
- If no specific operation can be detected, falls back to generic `ALTER_TABLE`
- Risk score: 2.0 (Medium)
- Still performs dependency analysis and impact assessment

## Testing

To test all operations, use the following SQL commands:

```sql
-- Column Operations
ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
ALTER TABLE transactions DROP COLUMN currency;
ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);
ALTER TABLE transactions RENAME COLUMN old_name TO new_name;
ALTER TABLE transactions ALTER COLUMN amount SET DEFAULT 0.00;
ALTER TABLE transactions ALTER COLUMN amount DROP DEFAULT;
ALTER TABLE transactions ALTER COLUMN amount SET NOT NULL;
ALTER TABLE transactions ALTER COLUMN amount DROP NOT NULL;

-- Constraint Operations
ALTER TABLE transactions ADD CONSTRAINT pk_transactions PRIMARY KEY (id);
ALTER TABLE transactions DROP CONSTRAINT pk_transactions;

-- Table Operations
ALTER TABLE transactions RENAME TO payment_transactions;
DROP TABLE transactions;

-- Index Operations
CREATE INDEX idx_transaction_date ON transactions(transaction_date);
DROP INDEX idx_transaction_date;
```

## Frontend Display

All operation types are displayed in the frontend with:
- **Change Type**: Exact operation (e.g., `DROP_COLUMN`, `SET_DEFAULT`)
- **Table Name**: Affected table
- **Column/Constraint/Index Name**: Affected object (if applicable)
- **Old/New Values**: Previous and new values (for MODIFY, RENAME operations)
- **Risk Score**: Color-coded risk level
- **Dependency Graph**: Shows code and database relationships

## Notes

1. **Incomplete SQL**: When PostgreSQL triggers send incomplete SQL (e.g., `ALTER TABLE public.transactions...`), the system uses multiple fallback methods to detect the exact operation.

2. **Constraint Types**: For `ADD_CONSTRAINT`, the system automatically detects the constraint type (PRIMARY_KEY, FOREIGN_KEY, UNIQUE, CHECK) from the SQL statement.

3. **Index Detection**: For `DROP INDEX`, the system attempts to extract the table name from the SQL if an `ON` clause is present.

4. **Risk Scoring**: Risk scores are based on:
   - Data loss potential
   - Breaking change potential
   - Data integrity impact
   - Performance impact
   - Code impact (number of affected files)

5. **Backward Compatibility**: All existing functionality remains unchanged. New operations are additive enhancements.

