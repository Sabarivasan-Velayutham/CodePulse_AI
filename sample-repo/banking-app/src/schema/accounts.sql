-- Accounts table schema

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    account_type VARCHAR(50) NOT NULL, -- CHECKING, SAVINGS, BUSINESS
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    overdraft_enabled BOOLEAN DEFAULT FALSE,
    overdraft_limit DECIMAL(15, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, CLOSED, FROZEN
    opened_date DATE NOT NULL,
    closed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_customer_id (customer_id),
    INDEX idx_account_number (account_number),
    INDEX idx_status (status),
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Account balance history for auditing
CREATE TABLE IF NOT EXISTS balance_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    old_balance DECIMAL(15, 2) NOT NULL,
    new_balance DECIMAL(15, 2) NOT NULL,
    transaction_id VARCHAR(36),
    change_type VARCHAR(50), -- DEBIT, CREDIT
    timestamp TIMESTAMP NOT NULL,
    
    INDEX idx_account_id (account_id),
    INDEX idx_transaction_id (transaction_id)
);