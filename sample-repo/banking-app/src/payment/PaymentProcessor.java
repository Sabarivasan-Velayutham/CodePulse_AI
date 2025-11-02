package com.bank.payment;

import com.bank.fraud.FraudDetection;
import com.bank.database.TransactionDAO;
import com.bank.account.AccountBalance;

/**
 * Main payment processing class
 * Handles all payment operations
 */
public class PaymentProcessor {
    
    private FraudDetection fraudDetection;
    private TransactionDAO transactionDAO;
    private AccountBalance accountBalance;
    
    public PaymentProcessor() {
        this.fraudDetection = new FraudDetection();
        this.transactionDAO = new TransactionDAO();
        this.accountBalance = new AccountBalance();
    }
    
    /**
     * Process a payment transaction
     * @param payment Payment object with details
     * @return PaymentResult with status
     */
    public PaymentResult processPayment(Payment payment) {
        // Step 1: Validate payment
        if (!validatePayment(payment)) {
            return PaymentResult.failed("Invalid payment data");
        }
        
        // Step 2: Check account balance
        double currentBalance = accountBalance.getBalance(payment.getAccountId());
        if (currentBalance < payment.getAmount()) {
            return PaymentResult.failed("Insufficient funds");
        }
        
        // Step 3: Fraud detection
        boolean isFraudulent = fraudDetection.checkTransaction(payment);
        if (isFraudulent) {
            return PaymentResult.rejected("Fraud detected");
        }
        
        // Step 4: Calculate fee
        double fee = calculateFee(payment.getAmount(), payment.getType());
        payment.setFee(fee);
        
        // Step 5: Process payment
        transactionDAO.save(payment);
        
        // Step 6: Update balance
        accountBalance.updateBalance(
            payment.getAccountId(), 
            payment.getAmount() + fee
        );
        
        // Step 7: Send notification
        sendNotification(payment);
        
        return PaymentResult.success(payment.getId());
    }
    
    /**
     * Calculate transaction fee
     * THIS METHOD WILL BE CHANGED IN DEMO
     */
    private double calculateFee(double amount, String type) {
        if (type.equals("DOMESTIC")) {
            if (amount < 1000) {
                return 10.0;
            } else if (amount < 10000) {
                return 25.0;
            } else {
                return 45.0;
            }
        } else if (type.equals("INTERNATIONAL")) {
            // International transfers have higher fees
            return amount * 0.03; // 3% fee
        }
        return 0.0;
    }
    
    private boolean validatePayment(Payment payment) {
        return payment != null 
            && payment.getAmount() > 0 
            && payment.getAccountId() != null;
    }
    
    private void sendNotification(Payment payment) {
        // Send email/SMS notification
        NotificationService.send(payment.getAccountId(), 
            "Payment processed: $" + payment.getAmount());
    }
}