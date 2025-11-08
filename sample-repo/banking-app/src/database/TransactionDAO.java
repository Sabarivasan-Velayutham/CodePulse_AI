package com.bank.database;

import com.bank.payment.Payment;
import com.bank.fraud.FraudAlert;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.time.LocalDateTime;

/**
 * Data Access Object for transactions
 * Manages all database operations for payments
 * CRITICAL: Schema changes here affect entire application
 */
public class TransactionDAO {
    
    private DatabaseConnection dbConnection;
    
    public TransactionDAO() {
        this.dbConnection = new DatabaseConnection();
    }
    
    /**
     * Save payment transaction to database
     * Schema: transactions table
     */
    public void save(Payment payment) {
        String sql = "INSERT INTO transactions (" +
                     "transaction_id, customer_id, account_id, " +
                     "amount, fee, type, status, " +
                     "processed_at, device_id, ip_address, " +
                     "geo_location, requires_manual_review) " +
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, payment.getTransactionId());
            stmt.setString(2, payment.getCustomerId());
            stmt.setString(3, payment.getAccountId());
            stmt.setDouble(4, payment.getAmount());
            stmt.setDouble(5, payment.getFee());
            stmt.setString(6, payment.getType());
            stmt.setString(7, payment.getStatus());
            stmt.setTimestamp(8, Timestamp.valueOf(payment.getProcessedAt()));
            stmt.setString(9, payment.getDeviceId());
            stmt.setString(10, payment.getIpAddress());
            stmt.setString(11, payment.getGeoLocation());
            stmt.setBoolean(12, payment.requiresManualReview());
            
            int rowsAffected = stmt.executeUpdate();
            System.out.println("💾 Transaction saved: " + payment.getTransactionId());
            
        } catch (SQLException e) {
            System.err.println("❌ Error saving transaction: " + e.getMessage());
            throw new DatabaseException("Failed to save transaction", e);
        }
    }
    
    /**
     * Find transaction by ID
     */
    public Payment findByTransactionId(String transactionId) {
        String sql = "SELECT * FROM transactions WHERE transaction_id = ?";
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, transactionId);
            ResultSet rs = stmt.executeQuery();
            
            if (rs.next()) {
                return mapResultSetToPayment(rs);
            }
            
            return null;
            
        } catch (SQLException e) {
            throw new DatabaseException("Failed to find transaction", e);
        }
    }
    
    /**
     * Find all transactions for an account
     * PERFORMANCE NOTE: This could return millions of rows
     */
    public List<Payment> findByAccountId(String accountId) {
        String sql = "SELECT * FROM transactions " +
                     "WHERE account_id = ? " +
                     "ORDER BY processed_at DESC " +
                     "LIMIT 1000"; // Pagination needed
        
        List<Payment> transactions = new ArrayList<>();
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, accountId);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                transactions.add(mapResultSetToPayment(rs));
            }
            
            return transactions;
            
        } catch (SQLException e) {
            throw new DatabaseException("Failed to find transactions", e);
        }
    }
    
    /**
     * Find recent transactions for fraud detection
     */
    public List<Payment> findRecentByCustomer(String customerId, int hours) {
        String sql = "SELECT * FROM transactions " +
                     "WHERE customer_id = ? " +
                     "AND processed_at > NOW() - INTERVAL ? HOUR " +
                     "ORDER BY processed_at DESC";
        
        List<Payment> transactions = new ArrayList<>();
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, customerId);
            stmt.setInt(2, hours);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                transactions.add(mapResultSetToPayment(rs));
            }
            
            return transactions;
            
        } catch (SQLException e) {
            throw new DatabaseException("Failed to find recent transactions", e);
        }
    }
    
    /**
     * Save fraud alert
     */
    public void saveFraudAlert(FraudAlert alert) {
        String sql = "INSERT INTO fraud_alerts (" +
                     "customer_id, payment_id, rule_code, " +
                     "reason, severity, alert_timestamp, investigated) " +
                     "VALUES (?, ?, ?, ?, ?, ?, false)";
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, alert.getCustomerId());
            stmt.setString(2, alert.getPaymentId());
            stmt.setString(3, alert.getRuleCode());
            stmt.setString(4, alert.getReason());
            stmt.setString(5, alert.getSeverity());
            stmt.setTimestamp(6, Timestamp.valueOf(alert.getTimestamp()));
            
            stmt.executeUpdate();
            System.out.println("🚨 Fraud alert saved: " + alert.getRuleCode());
            
        } catch (SQLException e) {
            throw new DatabaseException("Failed to save fraud alert", e);
        }
    }
    
    /**
     * Get daily transaction summary for reporting
     */
    public TransactionSummary getDailySummary(LocalDateTime date) {
        String sql = "SELECT " +
                     "COUNT(*) as total_count, " +
                     "SUM(amount) as total_amount, " +
                     "SUM(fee) as total_fees, " +
                     "AVG(amount) as avg_amount " +
                     "FROM transactions " +
                     "WHERE DATE(processed_at) = DATE(?)";
        
        try (Connection conn = dbConnection.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setTimestamp(1, Timestamp.valueOf(date));
            ResultSet rs = stmt.executeQuery();
            
            if (rs.next()) {
                TransactionSummary summary = new TransactionSummary();
                summary.setTotalCount(rs.getInt("total_count"));
                summary.setTotalAmount(rs.getDouble("total_amount"));
                summary.setTotalFees(rs.getDouble("total_fees"));
                summary.setAverageAmount(rs.getDouble("avg_amount"));
                return summary;
            }
            
            return null;
            
        } catch (SQLException e) {
            throw new DatabaseException("Failed to get daily summary", e);
        }
    }
    
    private Payment mapResultSetToPayment(ResultSet rs) throws SQLException {
        Payment payment = new Payment();
        payment.setTransactionId(rs.getString("transaction_id"));
        payment.setCustomerId(rs.getString("customer_id"));
        payment.setAccountId(rs.getString("account_id"));
        payment.setAmount(rs.getDouble("amount"));
        payment.setFee(rs.getDouble("fee"));
        payment.setType(rs.getString("type"));
        payment.setStatus(rs.getString("status"));
        payment.setProcessedAt(rs.getTimestamp("processed_at").toLocalDateTime());
        payment.setDeviceId(rs.getString("device_id"));
        payment.setIpAddress(rs.getString("ip_address"));
        payment.setGeoLocation(rs.getString("geo_location"));
        payment.setRequiresManualReview(rs.getBoolean("requires_manual_review"));
return payment;
}
}