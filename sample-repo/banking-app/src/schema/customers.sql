-- Customers table schema

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    account_created_date TIMESTAMP NOT NULL,
    is_premium_member BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    is_suspended BOOLEAN DEFAULT FALSE,
    average_transaction_amount DECIMAL(15, 2) DEFAULT 0.00,
    total_transaction_count INT DEFAULT 0,
    last_transaction_date TIMESTAMP,
    kyc_verified BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_is_blocked (is_blocked),
    INDEX idx_risk_level (risk_level)
);

-- Known devices for fraud detection
CREATE TABLE IF NOT EXISTS customer_devices (
    device_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    device_fingerprint TEXT,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    is_trusted BOOLEAN DEFAULT FALSE,
    
    INDEX idx_customer_id (customer_id)
);