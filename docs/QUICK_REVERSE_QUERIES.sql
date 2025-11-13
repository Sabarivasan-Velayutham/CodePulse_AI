-- ============================================================
-- Quick Reverse SQL Queries
-- Use these to undo sample schema changes for repeated testing
-- ============================================================

\c banking_db

-- ============================================================
-- REVERSE QUERY 1: Remove Currency Column
-- ============================================================
-- Original: ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
-- Reverse:  Remove the currency column

ALTER TABLE transactions DROP COLUMN IF EXISTS currency;

-- Verify:
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'transactions' AND column_name = 'currency';
-- Should return 0 rows

-- ============================================================
-- REVERSE QUERY 2: Restore Fee Column
-- ============================================================
-- Original: ALTER TABLE transactions DROP COLUMN fee;
-- Reverse:  Add back the fee column with original definition

-- Check if fee column exists, if not, add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'fee'
    ) THEN
        ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
        RAISE NOTICE 'Fee column restored';
    ELSE
        RAISE NOTICE 'Fee column already exists';
    END IF;
END $$;

-- Verify:
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns 
-- WHERE table_name = 'transactions' AND column_name = 'fee';
-- Should show: fee | numeric | 0.00

-- ============================================================
-- REVERSE QUERY 3: Restore Amount Column Type
-- ============================================================
-- Original: ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(20, 4);
-- Reverse:  Restore to original type DECIMAL(15, 2)

-- Check current type and restore if needed
DO $$
DECLARE
    current_precision INTEGER;
    current_scale INTEGER;
BEGIN
    SELECT numeric_precision, numeric_scale 
    INTO current_precision, current_scale
    FROM information_schema.columns 
    WHERE table_name = 'transactions' AND column_name = 'amount';
    
    -- If type is not DECIMAL(15,2), restore it
    IF current_precision != 15 OR current_scale != 2 THEN
        ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2) USING amount::DECIMAL(15, 2);
        RAISE NOTICE 'Amount column type restored to DECIMAL(15, 2)';
    ELSE
        RAISE NOTICE 'Amount column already has correct type DECIMAL(15, 2)';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not restore amount type: %', SQLERRM;
END $$;

-- Verify:
-- SELECT column_name, data_type, numeric_precision, numeric_scale
-- FROM information_schema.columns 
-- WHERE table_name = 'transactions' AND column_name = 'amount';
-- Should show: amount | numeric | 15 | 2

-- ============================================================
-- REVERSE QUERY 4: Remove Overdraft Limit Column
-- ============================================================
-- Original: ALTER TABLE accounts ADD COLUMN overdraft_limit DECIMAL(15, 2) DEFAULT 0.00;
-- Reverse:  Remove the overdraft_limit column

ALTER TABLE accounts DROP COLUMN IF EXISTS overdraft_limit;

-- Verify:
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'accounts' AND column_name = 'overdraft_limit';
-- Should return 0 rows

-- ============================================================
-- COMPLETE RESET: Restore transactions table to original state
-- ============================================================

-- Run all reverse operations in one go
DO $$
BEGIN
    -- Remove test columns
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'transactions' AND column_name = 'currency') THEN
        ALTER TABLE transactions DROP COLUMN currency;
        RAISE NOTICE 'Removed currency column';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'transactions' AND column_name = 'test_col') THEN
        ALTER TABLE transactions DROP COLUMN test_col;
        RAISE NOTICE 'Removed test_col column';
    END IF;
    
    -- Restore fee column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'transactions' AND column_name = 'fee') THEN
        ALTER TABLE transactions ADD COLUMN fee DECIMAL(10, 2) DEFAULT 0.00;
        RAISE NOTICE 'Restored fee column';
    END IF;
    
    -- Restore amount column type
    DECLARE
        curr_prec INTEGER;
        curr_scale INTEGER;
    BEGIN
        SELECT numeric_precision, numeric_scale 
        INTO curr_prec, curr_scale
        FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'amount';
        
        IF curr_prec != 15 OR curr_scale != 2 THEN
            ALTER TABLE transactions ALTER COLUMN amount TYPE DECIMAL(15, 2) USING amount::DECIMAL(15, 2);
            RAISE NOTICE 'Restored amount column type to DECIMAL(15, 2)';
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Could not restore amount type: %', SQLERRM;
    END;
    
    RAISE NOTICE 'Transactions table reset complete';
END $$;

-- ============================================================
-- VERIFICATION: Check current schema state
-- ============================================================

SELECT 
    column_name,
    data_type,
    CASE 
        WHEN numeric_precision IS NOT NULL 
        THEN data_type || '(' || numeric_precision || ',' || numeric_scale || ')'
        WHEN character_maximum_length IS NOT NULL
        THEN data_type || '(' || character_maximum_length || ')'
        ELSE data_type
    END AS full_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions'
ORDER BY ordinal_position;

-- Expected columns (original schema):
-- transaction_id | VARCHAR(50)
-- customer_id    | VARCHAR(50)
-- account_id      | VARCHAR(50)
-- amount          | DECIMAL(15,2)
-- fee             | DECIMAL(10,2) DEFAULT 0.00
-- currency        | VARCHAR(3) DEFAULT 'USD' (if added)
-- type            | VARCHAR(20)
-- status          | VARCHAR(20) DEFAULT 'PENDING'
-- processed_at    | TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- device_id       | VARCHAR(100)
-- ip_address      | VARCHAR(45)
-- geo_location    | VARCHAR(100)
-- requires_manual_review | BOOLEAN DEFAULT false

