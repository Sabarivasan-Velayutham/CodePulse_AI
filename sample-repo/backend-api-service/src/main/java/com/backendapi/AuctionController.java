package com.backendapi;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

/**
 * Auction API Controller
 * 
 * This API is consumed by:
 * - auctioneer (main auction platform)
 */
@RestController
@RequestMapping("/api/auctions")
public class AuctionController {
    
    /**
     * Get all auctions
     * GET /api/auctions
     */
    @GetMapping
    public ResponseEntity<?> getAllAuctions() {
        // Returns list of all auctions
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get auction by ID
     * GET /api/auctions/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getAuctionById(@PathVariable String id) {
        // Returns auction details by ID
        return ResponseEntity.ok().build();
    }
    
    /**
     * Create auction
     * POST /api/auctions
     * 
     * Request body: { title, description, startingPrice, endTime }
     */
    @PostMapping
    public ResponseEntity<?> createAuction(@RequestBody Map<String, Object> request) {
        // Creates a new auction
        // Required fields: title, startingPrice
        return ResponseEntity.ok().build();
    }
    
    /**
     * Place bid on auction
     * POST /api/auctions/{id}/bid
     * 
     * Request body: { bidAmount, bidderId }
     * 
     * NOTE: This endpoint is used by auctioneer repository
     * Scenario 2 tests breaking change: adding required paymentMethod parameter
     */
    @PostMapping("/{id}/bid")
    public ResponseEntity<?> placeBid(
        @PathVariable String id,
        @RequestBody Map<String, Object> request
    ) {
        // Places a bid on an auction
        // Required fields: bidAmount, bidderId
        // After Scenario 2: Will require paymentMethod parameter (BREAKING)
        return ResponseEntity.ok().build();
    }
}

