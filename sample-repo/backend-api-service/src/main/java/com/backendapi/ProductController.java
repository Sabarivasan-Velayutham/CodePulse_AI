package com.backendapi;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

/**
 * Product API Controller
 * 
 * This API is consumed by:
 * - MobileStore_Project (product catalog)
 */
@RestController
@RequestMapping("/api/products")
public class ProductController {
    
    /**
     * Get all products
     * GET /api/products
     * 
     * NOTE: This endpoint is used by MobileStore_Project repository
     * Scenario 3 tests breaking change: response changed from array to ProductListResponse object
     */
    @GetMapping
    public ResponseEntity<?> getAllProducts() {
        // Returns list of all products
        // Current: Returns array
        // After Scenario 3: Will return ProductListResponse (paginated object)
        return ResponseEntity.ok().build();
    }
    
    /**
     * Get product by ID
     * GET /api/products/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getProductById(@PathVariable String id) {
        // Returns product details by ID
        return ResponseEntity.ok().build();
    }
    
    /**
     * Create product
     * POST /api/products
     * 
     * Request body: { name, price, description, category }
     */
    @PostMapping
    public ResponseEntity<?> createProduct(@RequestBody Map<String, Object> request) {
        // Creates a new product
        // Required fields: name, price
        return ResponseEntity.ok().build();
    }
    
    /**
     * Update product
     * PUT /api/products/{id}
     */
    @PutMapping("/{id}")
    public ResponseEntity<?> updateProduct(
        @PathVariable String id,
        @RequestBody Map<String, Object> request
    ) {
        // Updates product details
        return ResponseEntity.ok().build();
    }
}

