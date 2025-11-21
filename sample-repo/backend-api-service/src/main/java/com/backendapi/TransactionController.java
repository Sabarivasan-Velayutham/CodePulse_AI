package com.backendapi;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

/**
 * Transaction Management API Controller
 * 
 * This API is consumed by:
 * - Stocks_Portfolio_Management (transaction history)
 * - auctioneer (payment processing)
 * - MobileStore_Project (order transactions)
 */
@RestController
@RequestMapping("/api/transactions")
public class TransactionController {
    
    /**
     * Get all transactions
     * GET /api/transactions
     */
    @GetMapping
    public ResponseEntity<?> getAllTransactions() {
        // Returns list of all transactions
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get transaction by ID
     * GET /api/transactions/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getTransactionById(@PathVariable String id) {
        // Returns transaction details by ID
        return ResponseEntity.ok().build();
    }
    
    /**
     * Create transaction
     * POST /api/transactions
     * 
     * Request body: { type, amount, accountId, description }
     */
    @PostMapping
    public ResponseEntity<?> createTransaction(@RequestBody Map<String, Object> request) {
        // Creates a new transaction
        // Required fields: type, amount, accountId
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get transactions by account
     * GET /api/transactions/account/{accountId}
     * 
     * NOTE: This endpoint is NOT used by any consumer repository
     * Scenario 5 tests breaking change: path changed from /account/{accountId} to /by-account/{accountId}
     */
    @GetMapping("/account/{accountId}")
    public ResponseEntity<?> getTransactionsByAccount(@PathVariable String accountId) {
        // Returns all transactions for a specific account
        // Current path: /account/{accountId}
        // After Scenario 5: Path will be /by-account/{accountId} (BREAKING, but no consumers)
        return ResponseEntity.ok().build();
    }
}

