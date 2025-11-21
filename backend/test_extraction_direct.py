"""Direct test of API extraction"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.api_extractor import APIContractExtractor

# Sample content from StockController.java
content = """package com.backendapi;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

@RestController
@RequestMapping("/api/stocks")
public class StockController {
    
    @GetMapping
    public ResponseEntity<?> getAllStocks() {
        return ResponseEntity.ok().build();
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<?> getStockById(@PathVariable String id) {
        return ResponseEntity.ok().build();
    }
    
    @PostMapping("/buy")
    public ResponseEntity<?> buyStock(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok().build();
    }
    
    @PostMapping("/sell")
    public ResponseEntity<?> sellStock(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok().build();
    }
    
    @GetMapping("/{id}/price")
    public ResponseEntity<?> getStockPrice(@PathVariable String id) {
        return ResponseEntity.ok().build();
    }
}"""

extractor = APIContractExtractor()

# Test framework detection
framework = extractor._detect_framework("StockController.java", content)
print(f"Framework detected: {framework}")

# Test extraction
contracts = extractor.extract_api_contracts("StockController.java", content)

print(f"\nExtracted {len(contracts)} contracts:")
for c in contracts:
    print(f"  - {c['method']} {c['path']} (line {c['line_number']})")
    if c.get('parameters'):
        print(f"    Parameters: {[p['name'] for p in c['parameters']]}")

if len(contracts) == 0:
    print("\n❌ No contracts extracted! Debugging...")
    # Check if @RestController is found
    print(f"  Contains @RestController: {'@RestController' in content}")
    print(f"  Contains @RequestMapping: {'@RequestMapping' in content}")
    print(f"  Contains @GetMapping: {'@GetMapping' in content}")
    print(f"  Contains @PostMapping: {'@PostMapping' in content}")
    
    # Test regex manually
    import re
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if '@GetMapping' in line or '@PostMapping' in line:
            print(f"\n  Line {i}: {line.strip()}")
            # Test regex
            for method in ['GET', 'POST']:
                annotation = f'@{method}Mapping'
                if annotation in line:
                    path_match = re.search(rf'@{method}Mapping\s*\([^)]*(?:value\s*=\s*)?["\']([^"\']+)["\']', line)
                    if path_match:
                        print(f"    ✓ Matched path: {path_match.group(1)}")
                    else:
                        print(f"    ✗ No path match (might be empty path)")

