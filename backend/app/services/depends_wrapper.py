"""
Wrapper for DEPENDS dependency analysis tool
Parses output and transforms to our format
"""

import subprocess
import json
import os
from typing import Dict, List
from pathlib import Path
import tempfile
import shutil

class DependsAnalyzer:
    def __init__(self):
        # Build the absolute path to the jar file inside the container
        # The 'tools' directory is mounted at /tools in docker-compose.yml
        default_jar_path = "/tools/depends/depends.jar"

        self.depends_jar = os.getenv(
            "DEPENDS_JAR_PATH",
            default_jar_path
        )

        # Convert to string for consistency in os.path.exists and subprocess
        self.depends_jar = str(self.depends_jar)

        if not os.path.exists(self.depends_jar):
            raise FileNotFoundError(
                f"DEPENDS jar not found at {self.depends_jar}")

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

        # --- FIX: Create a temporary DIRECTORY ---
        temp_dir = tempfile.mkdtemp()
        # The file depends.jar will create, based on our debug logs
        output_file_name = "-file.json" 
        expected_output_file = os.path.join(temp_dir, output_file_name)
        # ----------------------------------------

        # Build command
        cmd = [
            "java", "-jar", self.depends_jar,
            language,
            code_path,
            "-s", "./", # This seems to be relative to the code_path
            "-f", "json",
            "-d", temp_dir, # Pass the DIRECTORY
            "--auto-include"
        ]

        try:
            print(f"Running command: {' '.join(cmd)}")
            # Run DEPENDS
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            if result.stderr:
                print(f"Subprocess stderr: {result.stderr}")
            
            # Read output
            if not os.path.exists(expected_output_file) or os.path.getsize(expected_output_file) == 0:
                print(f"❌ DEPENDS did not create output file or file is empty.")
                print(f"Expected file at: {expected_output_file}")
                if result.stdout:
                    print(f"Subprocess stdout: {result.stdout}")
                raise Exception(f"DEPENDS did not produce valid output. Stderr: {result.stderr or 'None'}")
            
            with open(expected_output_file, 'r') as f:
                raw_data = json.load(f)

            # Transform to our format
            transformed = self.transform_depends_output(raw_data, code_path)

            print(
                f"✅ Analysis complete: {len(transformed['modules'])} modules found")

            return transformed

        except subprocess.TimeoutExpired:
            raise Exception("DEPENDS analysis timed out (>60s)")
        except Exception as e:
            raise Exception(f"DEPENDS analysis failed: {str(e)}")
        finally:
            # Clean up the temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


    def transform_depends_output(self, raw_data: Dict, base_path: str) -> Dict:
        """Transform DEPENDS output to our schema"""

        result = {
            "modules": [],
            "dependencies": {
                "direct": [],
                "indirect": []
            },
            "statistics": {}
        }
        
        # --- DEPENDENCY PARSING FIX ---
        
        # 1. Get the list of file names from 'variables'
        # We strip the base path to get a clean relative path
        def clean_path(path_str):
            if path_str.startswith(base_path):
                path_str = path_str[len(base_path):]
            return path_str.lstrip('/')

        # Use os.path.basename to get just the filename
        module_names = [os.path.basename(p) for p in raw_data.get("variables", [])]
        
        for name in module_names:
             result["modules"].append({
                "name": name,
                "type": "file",
                "relations_count": 0 
            })

        # 2. Parse the 'cells' array to find relationships
        for cell in raw_data.get("cells", []):
            try:
                # Get the source and destination file names using the index
                source_name = module_names[cell.get("src")]
                target_name = module_names[cell.get("dest")]

                # 'values' is a dictionary of relationship types
                for rel_type, count in cell.get("values", {}).items():
                    # Create a dependency object for each type
                    dep = {
                        "source": source_name,
                        "target": target_name,
                        "type": rel_type.upper(),
                        "file": source_name, # The relation originates in the source file
                        "line": 0 # Line number not provided in this view
                    }
                    
                    # Categorize as direct or indirect
                    if dep["type"] in ["CALL", "USE", "IMPORT", "CREATE", "EXTEND", "IMPLEMENT"]:
                        result["dependencies"]["direct"].append(dep)
                    else:
                        # "Contain" and other types
                        result["dependencies"]["indirect"].append(dep)
            except IndexError:
                print(f"⚠️ Error parsing cell: {cell}. Index out of bounds.")
            except Exception as e:
                print(f"⚠️ Error parsing cell: {e}")
        
        # --- END OF FIX ---

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
        Analyze dependencies for a single file.
        This now scans the entire 'src' root to build a full graph.
        """
        
        # --- FIX: Find the 'src' directory to scan ---
        # We assume the file_path is like 'sample-repo/banking-app/src/payment/File.java'
        # We want to find 'sample-repo/banking-app/src'
        p = Path(file_path)
        src_root = p
        while src_root.name != 'src' and src_root.parent != src_root:
            src_root = src_root.parent
        
        # If 'src' not found, fall back to the file's directory
        if src_root.name != 'src':
            print(f"⚠️ 'src' directory not in path. Falling back to {p.parent}")
            directory_to_scan = str(p.parent)
        else:
            directory_to_scan = str(src_root)
        
        # --- FIX: Build an ABSOLUTE path inside the container ---
        # We know 'sample-repo' is mounted at '/sample-repo'
        # We must construct the absolute path for the subprocess
        if not os.path.isabs(directory_to_scan):
             # This assumes the path is relative to the project root
             # and the project root is mounted at /
             directory_to_scan = "/" + directory_to_scan
        # ----------------------------------------------------

        # Run full analysis on the 'src' root
        full_analysis = self.analyze_code(directory_to_scan)

        # Filter to just this file
        file_name = os.path.basename(file_path)

        # The 'modules' list from transform_depends_output is already
        # just the filenames. We need to filter the dependencies.
        
        file_deps = {
            "modules": full_analysis.get("modules", []),
            "statistics": full_analysis.get("statistics", {}),
            "direct_dependencies": [],
            "indirect_dependencies": []
        }

        # Filter dependencies to only those originating from the changed file
        for dep in full_analysis["dependencies"]["direct"]:
            if file_name == dep["source"]:
                file_deps["direct_dependencies"].append(dep)

        for dep in full_analysis["dependencies"]["indirect"]:
            if file_name == dep["source"]:
                file_deps["indirect_dependencies"].append(dep)

        return file_deps

