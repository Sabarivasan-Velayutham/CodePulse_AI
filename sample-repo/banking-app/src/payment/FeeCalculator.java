package com.bank.payment;

import com.bank.database.CustomerDAO;
import java.time.LocalTime;

/**
 * Fee calculation engine
 * Handles various fee structures: flat, percentage, tiered
 */
public class FeeCalculator {
    
    private CustomerDAO customerDAO;
    
    public FeeCalculator() {
        this.customerDAO = new CustomerDAO();
    }
    
    /**
     * Calculate transaction fee based on type and amount
     * CRITICAL: Changes here affect revenue and customer statements
     */
    public double calculate(Payment payment) {
        double baseFee = 0.0;
        
        String paymentType = payment.getType();
        double amount = payment.getAmount();
        
        // Domestic payments
        if (paymentType.equals("DOMESTIC")) {
            if (amount < 1000) {
                baseFee = 5.0;
            } else if (amount < 5000) {
                baseFee = 10.0;
            } else if (amount < 10000) {
                baseFee = 25.0;
            } else {
                baseFee = 45.0;
            }
        }
        
        // International wire transfers
        else if (paymentType.equals("INTERNATIONAL")) {
            // Percentage-based fee
            baseFee = amount * 0.03; // 3% fee
            
            // Minimum fee
            if (baseFee < 35.0) {
                baseFee = 35.0;
            }
            
            // Maximum cap
            if (baseFee > 250.0) {
                baseFee = 250.0;
            }
        }
        
        // ACH transfers
        else if (paymentType.equals("ACH")) {
            baseFee = 2.0;
        }
        
        // Wire transfers
        else if (paymentType.equals("WIRE")) {
            baseFee = 30.0;
        }
        
        // Check for premium customer discount
        Customer customer = customerDAO.findById(payment.getCustomerId());
        if (customer.isPremiumMember()) {
            baseFee = baseFee * 0.5; // 50% discount for premium
        }
        
        // Peak hour surcharge (8 AM - 5 PM)
        LocalTime now = LocalTime.now();
        if (now.isAfter(LocalTime.of(8, 0)) && now.isBefore(LocalTime.of(17, 0))) {
            if (amount > 50000) {
                baseFee = baseFee * 1.1; // 10% surcharge for large daytime transactions
            }
        }
        
        return Math.round(baseFee * 100.0) / 100.0; // Round to 2 decimal places
    }
    
    /**
     * Get fee schedule for customer display
     */
    public FeeSchedule getSchedule(String customerId) {
        Customer customer = customerDAO.findById(customerId);
        FeeSchedule schedule = new FeeSchedule();
        
        // Build fee schedule based on customer type
        schedule.addTier("Domestic < $1,000", customer.isPremiumMember() ? "$2.50" : "$5.00");
        schedule.addTier("Domestic $1,000-$5,000", customer.isPremiumMember() ? "$5.00" : "$10.00");
        schedule.addTier("International", customer.isPremiumMember() ? "1.5%" : "3%");
        
        return schedule;
    }
}