package com.bank.account;

import com.bank.database.TransactionDAO;
import java.util.List;

/**
 * Account balance management (MongoDB version)
 */
public class AccountBalance {
    
    private TransactionDAO transactionDAO;
    
    public AccountBalance() {
        this.transactionDAO = new TransactionDAO();
    }
    
    /**
     * Get current account balance
     * @param accountId Account identifier
     * @return Current balance
     */
    public double getBalance(String accountId) {
        List<Transaction> transactions = 
            transactionDAO.findByAccountId(accountId);
        
        double balance = 0.0;
        for (Transaction txn : transactions) {
            if (txn.getType().equals("CREDIT")) {
                balance += txn.getAmount();
            } else if (txn.getType().equals("DEBIT")) {
                balance -= txn.getAmount();
            }
        }
        
        return balance;
    }
    
    /**
     * Update account balance
     * @param accountId Account identifier
     * @param amount Amount to deduct (including fees)
     */
    public void updateBalance(String accountId, double amount) {
        Transaction debitTxn = new Transaction();
        debitTxn.setAccountId(accountId);
        debitTxn.setAmount(amount);
        debitTxn.setType("DEBIT");
        debitTxn.setTimestamp(System.currentTimeMillis());
        
        transactionDAO.insert(debitTxn);
    }
    
    /**
     * Get account statement
     */
    public List<Transaction> getStatement(String accountId, 
                                         long startDate, 
                                         long endDate) {
        return transactionDAO.findByDateRange(accountId, startDate, endDate);
    }
}

