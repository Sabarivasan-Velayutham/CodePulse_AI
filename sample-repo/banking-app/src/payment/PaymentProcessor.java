package com.bank.payment;

import com.bank.fraud.FraudDetection;
import com.bank.fraud.RiskScorer;
import com.bank.database.TransactionDAO;
import com.bank.database.CustomerDAO;
import com.bank.account.AccountBalance;
import com.bank.account.OverdraftManager;
import com.bank.notification.NotificationService;
import com.bank.reporting.AuditLogger;
import com.bank.api.PaymentAPI;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Core payment processing engine
 * Handles all types of payments: domestic, international, wire transfers
 * Critical component - changes require extensive testing
 */
public class PaymentProcessor {
    
    private FraudDetection fraudDetection;
    private RiskScorer riskScorer;
    private TransactionDAO transactionDAO;
    private CustomerDAO customerDAO;
    private AccountBalance accountBalance;
    private OverdraftManager overdraftManager;
    private NotificationService notificationService;
    private AuditLogger auditLogger;
    private PaymentValidator validator;
    private FeeCalculator feeCalculator;
    private PaymentGateway paymentGateway;
    
    public PaymentProcessor() {
        this.fraudDetection = new FraudDetection();
        this.riskScorer = new RiskScorer();
        this.transactionDAO = new TransactionDAO();
        this.customerDAO = new CustomerDAO();
        this.accountBalance = new AccountBalance();
        this.overdraftManager = new OverdraftManager();
        this.notificationService = new NotificationService();
        this.auditLogger = new AuditLogger();
        this.validator = new PaymentValidator();
        this.feeCalculator = new FeeCalculator();
        this.paymentGateway = new PaymentGateway();
    }
    
    /**
     * Process a payment transaction
     * @param payment Payment object with details
     * @return PaymentResult with status and transaction ID
     */
    public PaymentResult processPayment(Payment payment) {
        String transactionId = UUID.randomUUID().toString();
        auditLogger.log("PAYMENT_INITIATED", transactionId, payment);
        
        try {
            // Step 1: Validate payment data
            ValidationResult validationResult = validator.validate(payment);
            if (!validationResult.isValid()) {
                auditLogger.log("PAYMENT_VALIDATION_FAILED", transactionId, validationResult);
                return PaymentResult.failed("Validation failed: " + validationResult.getMessage());
            }
            
            // Step 2: Check customer status
            Customer customer = customerDAO.findById(payment.getCustomerId());
            if (customer.isBlocked() || customer.isSuspended()) {
                auditLogger.log("CUSTOMER_BLOCKED", transactionId, customer.getId());
                return PaymentResult.failed("Customer account is blocked");
            }
            
            // Step 3: Check account balance
            double currentBalance = accountBalance.getBalance(payment.getAccountId());
            double requiredAmount = payment.getAmount();
            
            // Step 4: Check if overdraft needed
            boolean needsOverdraft = currentBalance < requiredAmount;
            if (needsOverdraft) {
                if (!overdraftManager.isEligible(payment.getAccountId())) {
                    auditLogger.log("INSUFFICIENT_FUNDS", transactionId, payment.getAccountId());
                    return PaymentResult.failed("Insufficient funds");
                }
                
                double overdraftLimit = overdraftManager.getLimit(payment.getAccountId());
                if (currentBalance + overdraftLimit < requiredAmount) {
                    return PaymentResult.failed("Exceeds overdraft limit");
                }
            }
            
            // Step 5: Fraud detection (CRITICAL)
            boolean isFraudulent = fraudDetection.checkTransaction(payment);
            if (isFraudulent) {
                auditLogger.log("FRAUD_DETECTED", transactionId, payment);
                notificationService.alertSecurityTeam(payment, "Fraud detected");
                return PaymentResult.rejected("Transaction rejected due to fraud risk");
            }
            
            // Step 6: Risk scoring
            double riskScore = riskScorer.calculateRisk(payment, customer);
            if (riskScore > 0.85) {
                auditLogger.log("HIGH_RISK_TRANSACTION", transactionId, riskScore);
                payment.setRequiresManualReview(true);
            }
            
            // Step 7: Calculate fees
            double fee = feeCalculator.calculate(payment);
            payment.setFee(fee);
            
            // Step 8: Process through payment gateway
            GatewayResult gatewayResult = paymentGateway.process(payment);
            if (!gatewayResult.isSuccess()) {
                auditLogger.log("GATEWAY_FAILED", transactionId, gatewayResult);
                return PaymentResult.failed("Payment gateway error: " + gatewayResult.getMessage());
            }
            
            // Step 9: Debit account
            double totalAmount = payment.getAmount() + fee;
            accountBalance.debit(payment.getAccountId(), totalAmount, needsOverdraft);
            
            // Step 10: Save transaction
            payment.setTransactionId(transactionId);
            payment.setStatus("COMPLETED");
            payment.setProcessedAt(LocalDateTime.now());
            transactionDAO.save(payment);
            
            // Step 11: Send notifications
            notificationService.sendPaymentConfirmation(payment);
            
            // Step 12: Audit logging
            auditLogger.log("PAYMENT_COMPLETED", transactionId, payment);
            
            return PaymentResult.success(transactionId);
            
        } catch (Exception e) {
            auditLogger.log("PAYMENT_ERROR", transactionId, e);
            return PaymentResult.failed("System error: " + e.getMessage());
        }
    }
    
    /**
     * Process batch payments (end-of-day processing)
     */
    public BatchResult processBatch(List<Payment> payments) {
        BatchResult result = new BatchResult();
        
        for (Payment payment : payments) {
            PaymentResult paymentResult = processPayment(payment);
            result.add(paymentResult);
        }
        
        auditLogger.log("BATCH_COMPLETED", result);
        return result;
    }
    
    /**
     * Reverse a payment (refund/chargeback)
     */
    public PaymentResult reversePayment(String transactionId, String reason) {
        auditLogger.log("REVERSAL_INITIATED", transactionId, reason);
        
        Payment originalPayment = transactionDAO.findByTransactionId(transactionId);
        if (originalPayment == null) {
            return PaymentResult.failed("Original transaction not found");
        }
        
        // Credit back to account
        double refundAmount = originalPayment.getAmount() + originalPayment.getFee();
        accountBalance.credit(originalPayment.getAccountId(), refundAmount);
        
        // Create reversal record
        Payment reversal = new Payment();
        reversal.setTransactionId(UUID.randomUUID().toString());
        reversal.setOriginalTransactionId(transactionId);
        reversal.setAmount(refundAmount);
        reversal.setType("REVERSAL");
        reversal.setReason(reason);
        transactionDAO.save(reversal);
        
        notificationService.sendReversalNotification(originalPayment.getCustomerId(), refundAmount);
        auditLogger.log("REVERSAL_COMPLETED", reversal.getTransactionId(), reversal);
        
        return PaymentResult.success(reversal.getTransactionId());
    }
}