"""Quick test for API extractor"""
from app.services.api_extractor import APIContractExtractor
import os

extractor = APIContractExtractor()

# Read the StockController file
file_path = os.path.join('..', 'sample-repo', 'backend-api-service', 'src', 'main', 'java', 'com', 'backendapi', 'StockController.java')
print(f"Reading file: {file_path}")
print(f"File exists: {os.path.exists(file_path)}")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File content length: {len(content)}")
print(f"Contains @RestController: {'@RestController' in content}")
print(f"Contains @PostMapping: {'@PostMapping' in content}")

# Check framework detection
framework = extractor._detect_framework('StockController.java', content)
print(f"Detected framework: {framework}")

contracts = extractor.extract_api_contracts('StockController.java', content)

print(f'\nFound {len(contracts)} contracts:')
for c in contracts:
    print(f"  - {c['method']} {c['path']} (line {c['line_number']})")
    
# Debug: Check specific lines
print("\nChecking specific lines:")
lines = content.split('\n')
for i, line in enumerate(lines[15:50], start=16):
    if '@GetMapping' in line or '@PostMapping' in line or '@RequestMapping' in line:
        print(f"  Line {i}: {line.strip()}")

