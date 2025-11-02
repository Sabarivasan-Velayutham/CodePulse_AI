"""
Wrapper for DEPENDS dependency analysis tool
Parses output and transforms to our format
"""

import subprocess
import json
import os
from typing import Dict, List
from pathlib import Path

class DependsAnalyzer:
    def __init__(self):
        self.depends_jar = os.getenv(
            "DEPENDS_JAR_PATH",
            "/tools/depends/depends-0.9.7.jar"
        )
        
        if not os.path.exists(self.depends_jar):
            # Try alternative path
            self.depends_jar = "tools/depends/depends-0.9.7.jar"
        
        if not os.path.exists(self.depends_jar):
            raise FileNotFoundError(f"DEPENDS jar not found at {self.depends_jar}")
    
    def analyze_code(self, code_path: str, language: str = "java") -> Dict:
        """
        Run DEPENDS analysis on code
        
        Args:
            code_path: Path to code directory
            language: Programming language (java, python, cpp, etc.)
        
        Returns:
            Parsed dependency data
        """
        print(f"🔍 Running DEPENDS analysis on {code_path}...")
        
        # Create temp output file
        output_file = "/tmp/depends_output.json"
        
        # Build command
        cmd = [
            "java", "-jar", self.depends_jar,
            language,
            code_path,
            "-s", "./",
            "-f", "json",
            "-d", output_file,
            "--auto-include"
        ]
        
        try:
            # Run DEPENDS
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                print(f"⚠️ DEPENDS stderr: {result.stderr}")
                # Continue anyway, sometimes DEPENDS succeeds with warnings
            
            # Read output
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"DEPENDS did not create output file")
            
            with open(output_file, 'r') as f:
                raw_data = json.load(f)
            
            # Transform to our format
            transformed = self.transform_depends_output(raw_data)
            
            print(f"✅ Analysis complete: {len(transformed['modules'])} modules found")
            
            return transformed
            
        except subprocess.TimeoutExpired:
            raise Exception("DEPENDS analysis timed out (>60s)")
        except Exception as e:
            raise Exception(f"DEPENDS analysis failed: {str(e)}")
    
    def transform_depends_output(self, raw_data: Dict) -> Dict:
        """Transform DEPENDS output to our schema"""
        
        result = {
            "modules": [],
            "dependencies": {
                "direct": [],
                "indirect": []
            },
            "statistics": {}
        }
        
        # Extract modules
        for cell in raw_data.get("cells", []):
            module = {
                "name": cell.get("name", "Unknown"),
                "type": cell.get("type", "class"),
                "relations_count": len(cell.get("relations", []))
            }
            result["modules"].append(module)
            
            # Extract dependencies
            for relation in cell.get("relations", []):
                dep = {
                    "source": relation.get("src", ""),
                    "target": relation.get("dest", ""),
                    "type": relation.get("type", "UNKNOWN"),
                    "file": relation.get("file", ""),
                    "line": relation.get("line", 0)
                }
                
                # Categorize as direct or indirect
                if dep["type"] in ["CALL", "USE", "IMPORT", "CREATE"]:
                    result["dependencies"]["direct"].append(dep)
                else:
                    result["dependencies"]["indirect"].append(dep)
        
        # Calculate statistics
        result["statistics"] = {
            "total_modules": len(result["modules"]),
            "direct_dependencies": len(result["dependencies"]["direct"]),
            "indirect_dependencies": len(result["dependencies"]["indirect"]),
            "total_dependencies": (
                len(result["dependencies"]["direct"]) + 
                len(result["dependencies"]["indirect"])
            )
        }
        
        return result
    
    def analyze_single_file(self, file_path: str) -> Dict:
        """
        Analyze dependencies for a single file
        
        Args:
            file_path: Path to the file (e.g., "PaymentProcessor.java")
        
        Returns:
            Dependencies for that file
        """
        # Get directory containing the file
        directory = os.path.dirname(file_path)
        if not directory:
            directory = "."
        
        # Run full analysis
        full_analysis = self.analyze_code(directory)
        
        # Filter to just this file
        file_name = os.path.basename(file_path)
        
        file_deps = {
            "file": file_name,
            "direct_dependencies": [],
            "indirect_dependencies": []
        }
        
        for dep in full_analysis["dependencies"]["direct"]:
            if file_name in dep["source"]:
                file_deps["direct_dependencies"].append(dep)
        
        for dep in full_analysis["dependencies"]["indirect"]:
            if file_name in dep["source"]:
                file_deps["indirect_dependencies"].append(dep)
        
        return file_deps