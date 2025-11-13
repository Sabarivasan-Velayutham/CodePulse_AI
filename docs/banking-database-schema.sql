-- ============================================================
-- Banking Database Schema with Interconnected Tables
-- ============================================================
-- This schema creates a realistic banking database with:
-- - Foreign key relationships between tables
-- - Views that depend on tables
-- - Triggers that reference tables
-- - Complex interdependencies
-- ============================================================

-- Connect to database
\c banking_db

-- ============================================================
-- 1. CUSTOMERS TABLE (Parent table)
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    kyc_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. ACCOUNTS TABLE (References customers)
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL, -- CHECKING, SAVINGS, CREDIT
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_status ON accounts(status);

-- ============================================================
-- 3. TRANSACTIONS TABLE (References accounts, customers)
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    type VARCHAR(20) NOT NULL, -- DEPOSIT, WITHDRAWAL, TRANSFER, PAYMENT
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED, CANCELLED
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(100),
    ip_address VARCHAR(45),
    geo_location VARCHAR(100),
    requires_manual_review BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE RESTRICT
);

CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_processed_at ON transactions(processed_at);

-- ============================================================
-- 4. FRAUD_ALERTS TABLE (References transactions, customers)
-- ============================================================
CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    payment_id VARCHAR(50), -- Alternative reference
    rule_code VARCHAR(50) NOT NULL,
    reason TEXT,
    severity VARCHAR(20) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    alert_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    investigated BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
);

CREATE INDEX idx_fraud_alerts_customer ON fraud_alerts(customer_id);
CREATE INDEX idx_fraud_alerts_transaction ON fraud_alerts(transaction_id);
CREATE INDEX idx_fraud_alerts_severity ON fraud_alerts(severity);

-- ============================================================
-- 5. ACCOUNT_BALANCES TABLE (References accounts, transactions)
-- ============================================================
CREATE TABLE IF NOT EXISTS account_balances (
    balance_id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    balance_before DECIMAL(15, 2) NOT NULL,
    balance_after DECIMAL(15, 2) NOT NULL,
    change_amount DECIMAL(15, 2) NOT NULL,
    balance_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
);

CREATE INDEX idx_account_balances_account ON account_balances(account_id);
CREATE INDEX idx_account_balances_date ON account_balances(balance_date);

-- ============================================================
-- 6. TRANSFER_RECORDS TABLE (References transactions, accounts)
-- ============================================================
CREATE TABLE IF NOT EXISTS transfer_records (
    transfer_id VARCHAR(50) PRIMARY KEY,
    from_account_id VARCHAR(50) NOT NULL,
    to_account_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transfer_fee DECIMAL(10, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'PENDING',
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (from_account_id) REFERENCES accounts(account_id) ON DELETE RESTRICT,
    FOREIGN KEY (to_account_id) REFERENCES accounts(account_id) ON DELETE RESTRICT,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE RESTRICT
);

CREATE INDEX idx_transfer_records_from ON transfer_records(from_account_id);
CREATE INDEX idx_transfer_records_to ON transfer_records(to_account_id);
CREATE INDEX idx_transfer_records_transaction ON transfer_records(transaction_id);

-- ============================================================
-- 7. VIEWS (Depend on multiple tables)
-- ============================================================

-- View: Customer Transaction Summary
CREATE OR REPLACE VIEW customer_transaction_summary AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    COUNT(t.transaction_id) AS total_transactions,
    SUM(t.amount) AS total_amount,
    SUM(t.fee) AS total_fees,
    AVG(t.amount) AS avg_transaction_amount,
    MAX(t.processed_at) AS last_transaction_date
FROM customers c
LEFT JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name;

-- View: Account Activity Summary
CREATE OR REPLACE VIEW account_activity_summary AS
SELECT 
    a.account_id,
    a.customer_id,
    a.account_type,
    a.balance,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(CASE WHEN t.type = 'DEPOSIT' THEN t.amount ELSE 0 END) AS total_deposits,
    SUM(CASE WHEN t.type = 'WITHDRAWAL' THEN t.amount ELSE 0 END) AS total_withdrawals,
    COUNT(f.alert_id) AS fraud_alert_count
FROM accounts a
LEFT JOIN transactions t ON a.account_id = t.account_id
LEFT JOIN fraud_alerts f ON a.customer_id = f.customer_id
GROUP BY a.account_id, a.customer_id, a.account_type, a.balance;

-- View: High-Risk Customers
CREATE OR REPLACE VIEW high_risk_customers AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    COUNT(DISTINCT f.alert_id) AS fraud_alert_count,
    MAX(f.severity) AS highest_severity,
    COUNT(DISTINCT t.transaction_id) AS transaction_count,
    SUM(t.amount) AS total_transaction_amount
FROM customers c
INNER JOIN fraud_alerts f ON c.customer_id = f.customer_id
LEFT JOIN transactions t ON c.customer_id = t.customer_id
WHERE f.severity IN ('HIGH', 'CRITICAL')
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING COUNT(DISTINCT f.alert_id) >= 2;

-- ============================================================
-- 8. TRIGGERS (Reference tables)
-- ============================================================

-- Trigger: Update account balance when transaction is completed
CREATE OR REPLACE FUNCTION update_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status != 'COMPLETED' THEN
        -- Update account balance
        UPDATE accounts 
        SET balance = balance + NEW.amount - NEW.fee
        WHERE account_id = NEW.account_id;
        
        -- Record balance change
        INSERT INTO account_balances (
            account_id, 
            transaction_id, 
            balance_before, 
            balance_after, 
            change_amount
        )
        SELECT 
            account_id,
            NEW.transaction_id,
            balance - NEW.amount + NEW.fee,
            balance,
            NEW.amount - NEW.fee
        FROM accounts
        WHERE account_id = NEW.account_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_account_balance
AFTER UPDATE ON transactions
FOR EACH ROW
WHEN (NEW.status = 'COMPLETED' AND OLD.status != 'COMPLETED')
EXECUTE FUNCTION update_account_balance();

-- Trigger: Update customer updated_at timestamp
CREATE OR REPLACE FUNCTION update_customer_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_timestamp
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_customer_timestamp();

-- ============================================================
-- 9. FUNCTIONS (Reference tables)
-- ============================================================

-- Function: Get customer total balance across all accounts
CREATE OR REPLACE FUNCTION get_customer_total_balance(p_customer_id VARCHAR)
RETURNS DECIMAL(15, 2) AS $$
DECLARE
    total_balance DECIMAL(15, 2);
BEGIN
    SELECT COALESCE(SUM(balance), 0.00)
    INTO total_balance
    FROM accounts
    WHERE customer_id = p_customer_id
    AND status = 'ACTIVE';
    
    RETURN total_balance;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 10. SUMMARY OF RELATIONSHIPS
-- ============================================================
-- 
-- Table Dependencies:
-- 1. accounts -> customers (FK: customer_id)
-- 2. transactions -> customers (FK: customer_id)
-- 3. transactions -> accounts (FK: account_id)
-- 4. fraud_alerts -> customers (FK: customer_id)
-- 5. fraud_alerts -> transactions (FK: transaction_id)
-- 6. account_balances -> accounts (FK: account_id)
-- 7. account_balances -> transactions (FK: transaction_id)
-- 8. transfer_records -> accounts (FK: from_account_id, to_account_id)
-- 9. transfer_records -> transactions (FK: transaction_id)
--
-- Views Dependencies:
-- 1. customer_transaction_summary -> customers, transactions
-- 2. account_activity_summary -> accounts, transactions, fraud_alerts
-- 3. high_risk_customers -> customers, fraud_alerts, transactions
--
-- Trigger Dependencies:
-- 1. trigger_update_account_balance -> transactions, accounts, account_balances
-- 2. trigger_update_customer_timestamp -> customers
--
-- Function Dependencies:
-- 1. get_customer_total_balance -> accounts
--
-- ============================================================

-- Insert sample data for testing
INSERT INTO customers (customer_id, first_name, last_name, email, kyc_status) VALUES
('CUST001', 'John', 'Doe', 'john.doe@example.com', 'VERIFIED'),
('CUST002', 'Jane', 'Smith', 'jane.smith@example.com', 'VERIFIED')
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO accounts (account_id, customer_id, account_type, balance) VALUES
('ACC001', 'CUST001', 'CHECKING', 5000.00),
('ACC002', 'CUST001', 'SAVINGS', 10000.00),
('ACC003', 'CUST002', 'CHECKING', 2500.00)
ON CONFLICT (account_id) DO NOTHING;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check all foreign key relationships
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, kcu.column_name;

-- Check all views and their dependencies
SELECT 
    table_name AS view_name,
    view_definition
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

