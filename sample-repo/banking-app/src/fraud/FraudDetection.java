package com.bank.fraud;

import com.bank.payment.Payment;
import com.bank.database.CustomerDAO;
import com.bank.database.TransactionDAO;
import com.bank.reporting.AuditLogger;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;

/**
 * Fraud detection engine
 * Uses rule-based and ML-based detection
 * CRITICAL: Changes affect security and customer experience
 */
public class FraudDetection {
    
    private CustomerDAO customerDAO;
    private TransactionDAO transactionDAO;
    private RiskScorer riskScorer;
    private MLModel mlModel;
    private AuditLogger auditLogger;
    
    public FraudDetection() {
        this.customerDAO = new CustomerDAO();
        this.transactionDAO = new TransactionDAO();
        this.riskScorer = new RiskScorer();
        this.mlModel = new MLModel();
        this.auditLogger = new AuditLogger();
    }
    
    /**
     * Check if transaction is fraudulent
     * @param payment Payment to analyze
     * @return true if fraud detected
     */
    public boolean checkTransaction(Payment payment) {
        auditLogger.log("FRAUD_CHECK_STARTED", payment.getCustomerId(), payment);
        
        // Rule 1: Amount threshold
        if (payment.getAmount() > 50000) {
            logSuspiciousActivity(payment, "HIGH_AMOUNT", "Amount exceeds $50,000");
            return true;
        }
        
        // Rule 2: Unusual amount for customer
        Customer customer = customerDAO.findById(payment.getCustomerId());
        double avgTransaction = customer.getAverageTransactionAmount();
        
        if (payment.getAmount() > avgTransaction * 10) {
            logSuspiciousActivity(payment, "UNUSUAL_AMOUNT", 
                "Amount 10x higher than customer average");
            return true;
        }
        
        // Rule 3: Transaction frequency
        List<Payment> recentTransactions = transactionDAO.findRecentByCustomer(
            payment.getCustomerId(), 
            24 // last 24 hours
        );
        
        if (recentTransactions.size() > 10) {
            logSuspiciousActivity(payment, "HIGH_FREQUENCY", 
                "More than 10 transactions in 24 hours");
            return true;
        }
        
        // Rule 4: Velocity check (rapid succession)
        if (recentTransactions.size() > 0) {
            Payment lastTransaction = recentTransactions.get(0);
            long minutesSinceLastTransaction = ChronoUnit.MINUTES.between(
                lastTransaction.getProcessedAt(), 
                LocalDateTime.now()
            );
            
            if (minutesSinceLastTransaction < 2) {
                logSuspiciousActivity(payment, "VELOCITY_CHECK", 
                    "Transaction within 2 minutes of previous");
                return true;
            }
        }
        
        // Rule 5: Geographic anomaly
        String currentLocation = payment.getGeoLocation();
        if (recentTransactions.size() > 0) {
            String lastLocation = recentTransactions.get(0).getGeoLocation();
            
            if (!currentLocation.equals(lastLocation)) {
                double distance = calculateDistance(currentLocation, lastLocation);
                long hoursSinceLastTransaction = ChronoUnit.HOURS.between(
                    recentTransactions.get(0).getProcessedAt(),
                    LocalDateTime.now()
                );
                
                // Impossible travel speed
                if (distance > 500 && hoursSinceLastTransaction < 2) {
                    logSuspiciousActivity(payment, "IMPOSSIBLE_TRAVEL", 
                        "Geographic locations " + distance + " km apart in " + hoursSinceLastTransaction + " hours");
                    return true;
                }
            }
        }
        
        // Rule 6: High-risk country
        if (isHighRiskCountry(payment.getDestinationCountry())) {
            logSuspiciousActivity(payment, "HIGH_RISK_COUNTRY", 
                "Destination is high-risk country");
            return true;
        }
        
        // Rule 7: New device
        String deviceId = payment.getDeviceId();
        List<String> knownDevices = customerDAO.getKnownDevices(payment.getCustomerId());
        if (!knownDevices.contains(deviceId)) {
            if (payment.getAmount() > 10000) {
                logSuspiciousActivity(payment, "NEW_DEVICE_HIGH_AMOUNT", 
                    "Large transaction from unknown device");
                return true;
            }
        }
        
        // Rule 8: ML-based fraud detection
        double mlFraudScore = mlModel.predictFraudProbability(payment, customer);
        if (mlFraudScore > 0.85) {
            logSuspiciousActivity(payment, "ML_HIGH_FRAUD_SCORE", 
                "ML model fraud score: " + mlFraudScore);
            return true;
        }
        
        // Rule 9: Account age
        long accountAgeDays = ChronoUnit.DAYS.between(customer.getAccountCreatedDate(), LocalDateTime.now());
        if (accountAgeDays < 7 && payment.getAmount() > 5000) {
            logSuspiciousActivity(payment, "NEW_ACCOUNT_HIGH_AMOUNT", 
                "Account less than 7 days old with large transaction");
            return true;
        }
        
        auditLogger.log("FRAUD_CHECK_PASSED", payment.getCustomerId(), payment);
        return false;
    }
    
    private void logSuspiciousActivity(Payment payment, String ruleCode, String reason) {
        FraudAlert alert = new FraudAlert();
        alert.setCustomerId(payment.getCustomerId());
        alert.setPaymentId(payment.getTransactionId());
        alert.setRuleCode(ruleCode);
        alert.setReason(reason);
        alert.setTimestamp(LocalDateTime.now());
        alert.setSeverity("HIGH");
        
        auditLogger.log("FRAUD_ALERT", ruleCode, alert);
        
        // Save to database for investigation
        transactionDAO.saveFraudAlert(alert);
    }
    
    private boolean isHighRiskCountry(String countryCode) {
        String[] highRiskCountries = {"XX", "YY", "ZZ"}; // Placeholder codes
        for (String country : highRiskCountries) {
            if (countryCode.equals(country)) {
                return true;
            }
        }
        return false;
    }
    
    private double calculateDistance(String location1, String location2) {
        // Simplified distance calculation
        // In production, use proper geolocation library
        return 0.0;
    }
}