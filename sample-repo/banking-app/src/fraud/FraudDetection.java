package com.bank.fraud;

import com.bank.payment.Payment;
import com.bank.database.CustomerDAO;

/**
 * Fraud detection service
 * Analyzes transactions for suspicious activity
 */
public class FraudDetection {
    
    private CustomerDAO customerDAO;
    private RuleEngine ruleEngine;
    
    public FraudDetection() {
        this.customerDAO = new CustomerDAO();
        this.ruleEngine = new RuleEngine();
    }
    
    /**
     * Check if transaction is fraudulent
     * @param payment Payment to check
     * @return true if fraud detected
     */
    public boolean checkTransaction(Payment payment) {
        // Rule 1: Check amount threshold
        if (payment.getAmount() > 50000) {
            logSuspiciousActivity(payment, "High amount");
            return true;
        }
        
        // Rule 2: Check customer history
        Customer customer = customerDAO.findById(payment.getCustomerId());
        double avgTransaction = customer.getAverageTransactionAmount();
        
        if (payment.getAmount() > avgTransaction * 10) {
            logSuspiciousActivity(payment, "Unusual amount for customer");
            return true;
        }
        
        // Rule 3: Check frequency
        int recentTransactionCount = customerDAO.getRecentTransactionCount(
            payment.getCustomerId(), 
            24 // last 24 hours
        );
        
        if (recentTransactionCount > 10) {
            logSuspiciousActivity(payment, "Too many transactions");
            return true;
        }
        
        // Rule 4: Geographic check
        if (isHighRiskLocation(payment.getLocation())) {
            logSuspiciousActivity(payment, "High risk location");
            return true;
        }
        
        return false;
    }
    
    private void logSuspiciousActivity(Payment payment, String reason) {
        // Log to fraud database
        System.out.println("⚠️ Suspicious activity: " + reason 
            + " - Payment ID: " + payment.getId());
    }
    
    private boolean isHighRiskLocation(String location) {
        // Check against high-risk country list
        String[] highRiskCountries = {"XX", "YY", "ZZ"};
        for (String country : highRiskCountries) {
            if (location.startsWith(country)) {
                return true;
            }
        }
        return false;
    }
}