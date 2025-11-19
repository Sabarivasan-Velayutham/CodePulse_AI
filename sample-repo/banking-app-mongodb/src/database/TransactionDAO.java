package com.bank.database;

import com.bank.payment.Payment;
import com.bank.fraud.FraudAlert;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Sorts;
import org.bson.Document;
import java.util.ArrayList;
import java.util.List;
import java.time.LocalDateTime;

/**
 * Data Access Object for transactions (MongoDB version)
 * Manages all database operations for payments
 * CRITICAL: Schema changes here affect entire application
 */
public class TransactionDAO {
    
    private MongoClient mongoClient;
    private MongoDatabase database;
    private MongoCollection<Document> transactionsCollection;
    private MongoCollection<Document> fraudAlertsCollection;
    
    public TransactionDAO() {
        this.mongoClient = MongoClients.create("mongodb://localhost:27017");
        this.database = mongoClient.getDatabase("banking_db");
        this.transactionsCollection = database.getCollection("transactions");
        this.fraudAlertsCollection = database.getCollection("fraud_alerts");
    }
    
    /**
     * Save payment transaction to database
     * Schema: transactions collection
     */
    public void save(Payment payment) {
        Document doc = new Document()
            .append("transaction_id", payment.getTransactionId())
            .append("customer_id", payment.getCustomerId())
            .append("account_id", payment.getAccountId())
            .append("amount", payment.getAmount())
            .append("fee", payment.getFee())
            .append("type", payment.getType())
            .append("status", payment.getStatus())
            .append("processed_at", payment.getProcessedAt())
            .append("device_id", payment.getDeviceId())
            .append("ip_address", payment.getIpAddress())
            .append("geo_location", payment.getGeoLocation())
            .append("requires_manual_review", payment.requiresManualReview());
        
        transactionsCollection.insertOne(doc);
        System.out.println("💾 Transaction saved: " + payment.getTransactionId());
    }
    
    /**
     * Find transaction by ID
     */
    public Payment findByTransactionId(String transactionId) {
        Document doc = transactionsCollection.find(
            Filters.eq("transaction_id", transactionId)
        ).first();
        
        if (doc != null) {
            return mapDocumentToPayment(doc);
        }
        
        return null;
    }
    
    /**
     * Find all transactions for an account
     * PERFORMANCE NOTE: This could return millions of documents
     */
    public List<Payment> findByAccountId(String accountId) {
        List<Payment> transactions = new ArrayList<>();
        
        transactionsCollection.find(
            Filters.eq("account_id", accountId)
        )
        .sort(Sorts.descending("processed_at"))
        .limit(1000) // Pagination needed
        .forEach(doc -> transactions.add(mapDocumentToPayment(doc)));
        
        return transactions;
    }
    
    /**
     * Find recent transactions for fraud detection
     */
    public List<Payment> findRecentByCustomer(String customerId, int hours) {
        List<Payment> transactions = new ArrayList<>();
        LocalDateTime cutoff = LocalDateTime.now().minusHours(hours);
        
        transactionsCollection.find(
            Filters.and(
                Filters.eq("customer_id", customerId),
                Filters.gte("processed_at", cutoff)
            )
        )
        .sort(Sorts.descending("processed_at"))
        .forEach(doc -> transactions.add(mapDocumentToPayment(doc)));
        
        return transactions;
    }
    
    /**
     * Save fraud alert
     */
    public void saveFraudAlert(FraudAlert alert) {
        Document doc = new Document()
            .append("customer_id", alert.getCustomerId())
            .append("payment_id", alert.getPaymentId())
            .append("rule_code", alert.getRuleCode())
            .append("reason", alert.getReason())
            .append("severity", alert.getSeverity())
            .append("alert_timestamp", alert.getTimestamp())
            .append("investigated", false);
        
        fraudAlertsCollection.insertOne(doc);
        System.out.println("🚨 Fraud alert saved: " + alert.getRuleCode());
    }
    
    /**
     * Get daily transaction summary for reporting
     */
    public TransactionSummary getDailySummary(LocalDateTime date) {
        // MongoDB aggregation pipeline for daily summary
        // This would use aggregation framework in production
        TransactionSummary summary = new TransactionSummary();
        // Implementation would use aggregation pipeline
        return summary;
    }
    
    private Payment mapDocumentToPayment(Document doc) {
        Payment payment = new Payment();
        payment.setTransactionId(doc.getString("transaction_id"));
        payment.setCustomerId(doc.getString("customer_id"));
        payment.setAccountId(doc.getString("account_id"));
        payment.setAmount(doc.getDouble("amount"));
        payment.setFee(doc.getDouble("fee"));
        payment.setType(doc.getString("type"));
        payment.setStatus(doc.getString("status"));
        payment.setProcessedAt(doc.getDate("processed_at").toInstant().atZone(java.time.ZoneId.systemDefault()).toLocalDateTime());
        payment.setDeviceId(doc.getString("device_id"));
        payment.setIpAddress(doc.getString("ip_address"));
        payment.setGeoLocation(doc.getString("geo_location"));
        payment.setRequiresManualReview(doc.getBoolean("requires_manual_review", false));
        return payment;
    }
}

