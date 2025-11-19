package com.bank.payment;

import com.bank.database.TransactionDAO;
import com.bank.fraud.FraudDetection;
import com.bank.account.AccountBalance;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.Filters;
import org.bson.Document;
import java.time.LocalDateTime;

/**
 * Payment processing service (MongoDB version)
 * Handles payment transactions and fraud checks
 */
public class PaymentProcessor {
    
    private TransactionDAO transactionDAO;
    private FraudDetection fraudDetection;
    private AccountBalance accountBalance;
    private MongoCollection<Document> accountsCollection;
    
    public PaymentProcessor() {
        this.transactionDAO = new TransactionDAO();
        this.fraudDetection = new FraudDetection();
        this.accountBalance = new AccountBalance();
        
        MongoClient mongoClient = MongoClients.create("mongodb://localhost:27017");
        MongoDatabase database = mongoClient.getDatabase("banking_db");
        this.accountsCollection = database.getCollection("accounts");
    }
    
    /**
     * Process a payment transaction
     * @param payment Payment to process
     * @return Processing result
     */
    public PaymentResult processPayment(Payment payment) {
        // Step 1: Fraud check
        if (fraudDetection.checkTransaction(payment)) {
            payment.setStatus("FRAUD_DETECTED");
            transactionDAO.save(payment);
            return PaymentResult.fraudDetected();
        }
        
        // Step 2: Check account balance
        String accountId = payment.getAccountId();
        double currentBalance = accountBalance.getBalance(accountId);
        double requiredAmount = payment.getAmount() + payment.getFee();
        
        if (currentBalance < requiredAmount) {
            payment.setStatus("INSUFFICIENT_FUNDS");
            transactionDAO.save(payment);
            return PaymentResult.insufficientFunds();
        }
        
        // Step 3: Update account balance
        accountBalance.updateBalance(accountId, requiredAmount);
        
        // Step 4: Save transaction
        payment.setStatus("COMPLETED");
        payment.setProcessedAt(LocalDateTime.now());
        transactionDAO.save(payment);
        
        // Step 5: Update account document
        accountsCollection.updateOne(
            Filters.eq("account_id", accountId),
            new Document("$inc", new Document("balance", -requiredAmount))
        );
        
        return PaymentResult.success(payment.getTransactionId());
    }
    
    /**
     * Get transaction by ID
     */
    public Payment getTransaction(String transactionId) {
        return transactionDAO.findByTransactionId(transactionId);
    }
    
    /**
     * Get account transactions
     */
    public java.util.List<Payment> getAccountTransactions(String accountId) {
        return transactionDAO.findByAccountId(accountId);
    }
}

