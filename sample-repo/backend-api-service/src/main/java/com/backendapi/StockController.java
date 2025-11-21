package com.backendapi;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

/**
 * Stock Management API Controller
 * 
 * This API is consumed by:
 * - Stocks_Portfolio_Management (frontend)
 * - auctioneer (auction platform)
 * - MobileStore_Project (mobile store)
 */
@RestController
@RequestMapping("/api/stocks")
public class StockController {
    
    /**
     * Get all stocks
     * GET /api/stocks
     * 
     * NOTE: This endpoint is used by Stocks_Portfolio_Management (Portfolio.js)
     * Scenario 1 tests breaking change: response changed from array to StockListResponse object
     */
    @GetMapping
    public ResponseEntity<?> getAllStocks() {
        // Returns list of all stocks
        // Current: Returns array
        // After Scenario 1: Will return StockListResponse (paginated object)
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get stock by ID
     * GET /api/stocks/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getStockById(@PathVariable String id) {
        // Returns stock details by ID
        return ResponseEntity.ok().build();
    }
    
    /**
     * Buy stock
     * POST /api/stocks/buy
     * 
     * Request body: { stockId, quantity, accountId }
     * 
     * NOTE: This endpoint is NOT used by any consumer repository
     * Scenario 4 tests breaking change: adding required verificationCode parameter (no impact expected)
     */
    @PostMapping("/buy")
    public ResponseEntity<?> buyStock(@RequestBody Map<String, Object> request) {
        // Processes stock purchase
        // Required fields: stockId, quantity, accountId
        // After Scenario 4: Will require verificationCode parameter (BREAKING, but no consumers)
        return ResponseEntity.ok().build();
    }
    
    /**
     * Sell stock
     * POST /api/stocks/sell
     * 
     * Request body: { stockId, quantity, accountId }
     */
    @PostMapping("/sell")
    public ResponseEntity<?> sellStock(@RequestBody Map<String, Object> request) {
        // Processes stock sale
        // Required fields: stockId, quantity, accountId
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get stock price
     * GET /api/stocks/{id}/price
     */
    @GetMapping("/{id}/price")
    public ResponseEntity<?> getStockPrice(@PathVariable String id) {
        // Returns current stock price
        return ResponseEntity.ok().build();
    }
}

