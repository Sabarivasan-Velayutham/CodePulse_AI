-- Transactions table schema
-- This is the main table for all payment transactions

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    account_id VARCHAR(36) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    fee DECIMAL(10, 2) DEFAULT 0.00,
    type VARCHAR(50) NOT NULL, -- DOMESTIC, INTERNATIONAL, ACH, WIRE
    status VARCHAR(50) NOT NULL, -- PENDING, COMPLETED, FAILED, REVERSED
    processed_at TIMESTAMP NOT NULL,
    device_id VARCHAR(100),
    ip_address VARCHAR(45),
    geo_location VARCHAR(100),
    requires_manual_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_customer_id (customer_id),
    INDEX idx_account_id (account_id),
    INDEX idx_processed_at (processed_at),
    INDEX idx_status (status)
);

-- Fraud alerts table
CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    payment_id VARCHAR(36),
    rule_code VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    alert_timestamp TIMESTAMP NOT NULL,
    investigated BOOLEAN DEFAULT FALSE,
    investigation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_customer_id (customer_id),
    INDEX idx_payment_id (payment_id),
    INDEX idx_alert_timestamp (alert_timestamp),
    INDEX idx_investigated (investigated)
);

-- Example: If you want to add a new column (CHANGE SCENARIO)
-- ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD';
-- ALTER TABLE transactions ADD COLUMN destination_country VARCHAR(2);
-- ALTER TABLE transactions ADD COLUMN risk_score DECIMAL(3, 2);