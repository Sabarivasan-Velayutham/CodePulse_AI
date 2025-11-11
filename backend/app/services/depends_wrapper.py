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
                source_idx = cell.get("src")
                dest_idx = cell.get("dest")
                source_name = module_names[source_idx]
                target_name = module_names[dest_idx]
                
                # Get full paths for source file to extract line numbers
                source_full_path = raw_data.get("variables", [])[source_idx] if source_idx < len(raw_data.get("variables", [])) else None

                # 'values' is a dictionary of relationship types
                for rel_type, count in cell.get("values", {}).items():
                    # Extract line numbers and code references from source file
                    line_numbers, code_references = self._extract_code_references(
                        source_full_path, target_name, rel_type.upper(), base_path
                    )
                    
                    # Create a dependency object for each type
                    dep = {
                        "source": source_name,
                        "target": target_name,
                        "type": rel_type.upper(),
                        "file": source_name, # The relation originates in the source file
                        "line": line_numbers[0] if line_numbers else 0,
                        "line_numbers": line_numbers,
                        "code_reference": code_references[0] if code_references else "",
                        "code_references": code_references
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

    def _extract_code_references(self, source_file_path: str, target_name: str, rel_type: str, base_path: str) -> tuple:
        """
        Extract line numbers and code references from source file
        Supports both Java and Python files
        
        Returns:
            tuple: (list of line_numbers, list of code_references)
        """
        line_numbers = []
        code_references = []
        
        if not source_file_path or not os.path.exists(source_file_path):
            return line_numbers, code_references
        
        try:
            # Detect file type
            is_python = source_file_path.endswith('.py')
            
            # Get target class/module name
            if is_python:
                target_class = target_name.replace('.py', '').split('/')[-1]
                target_module = target_name.replace('.py', '').replace('/', '.').replace('\\', '.')
            else:
                target_class = target_name.replace('.java', '').split('/')[-1]
                target_module = target_name.replace('.java', '').replace('/', '.').lower()
            
            with open(source_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, start=1):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Skip comments
                if is_python:
                    if line_stripped.startswith('#'):
                        continue
                else:
                    if line_stripped.startswith('//'):
                        continue
                
                found = False
                
                if rel_type == "IMPORT":
                    if is_python:
                        # Python: import module or from module import class
                        if (line_stripped.startswith("import ") and target_class in line_stripped) or \
                           (line_stripped.startswith("from ") and target_module in line_stripped):
                            found = True
                    else:
                        # Java: import statements
                        if line_stripped.startswith("import") and target_class in line_stripped:
                            found = True
                elif rel_type == "CALL":
                    if is_python:
                        # Python: method calls - object.method( or Class.method(
                        if target_class in line_stripped and '.' in line_stripped and '(' in line_stripped:
                            found = True
                    else:
                        # Java: method calls
                        if target_class in line_stripped and '.' in line_stripped and '(' in line_stripped:
                            found = True
                elif rel_type == "USE":
                    if is_python:
                        # Python: variable/attribute usage
                        if target_class in line_stripped:
                            if not line_stripped.startswith("import") and not line_stripped.startswith("from") and \
                               not line_stripped.startswith("class") and not line_stripped.startswith("def"):
                                found = True
                    else:
                        # Java: variable/field usage
                        if target_class in line_stripped:
                            if not line_stripped.startswith("import") and not line_stripped.startswith("package"):
                                found = True
                elif rel_type == "CREATE":
                    if is_python:
                        # Python: object instantiation - Class( or Class()
                        if target_class in line_stripped and '(' in line_stripped:
                            # Check if it's not a function definition
                            if not line_stripped.startswith("def ") and not line_stripped.startswith("class "):
                                found = True
                    else:
                        # Java: object instantiation (new keyword)
                        if "new " in line_stripped and target_class in line_stripped:
                            found = True
                elif rel_type == "CONTAIN":
                    if is_python:
                        # Python: class definitions, inheritance
                        if (f"class {target_class}" in line_stripped) or \
                           (f"({target_class}" in line_stripped and "class" in lines[max(0, line_num-2):line_num]):
                            found = True
                    else:
                        # Java: class declarations, extends, implements
                        if (f"class " in line_stripped and target_class in line_stripped) or \
                           (f"extends {target_class}" in line_stripped) or \
                           (f"implements {target_class}" in line_stripped):
                            found = True
                
                if found:
                    line_numbers.append(line_num)
                    # Get context (2 lines before, current line, 2 lines after)
                    context_start = max(0, line_num - 3)
                    context_end = min(len(lines), line_num + 2)
                    context_lines = lines[context_start:context_end]
                    context = ''.join(context_lines)
                    code_references.append(context.strip())
                    
                    # Limit to first 5 occurrences to avoid too much data
                    if len(line_numbers) >= 5:
                        break
        
        except Exception as e:
            print(f"⚠️ Error extracting code references from {source_file_path}: {e}")
        
        return line_numbers, code_references

    def analyze_single_file(self, file_path: str) -> Dict:
        """
        Analyze dependencies for a single file.
        This now scans the entire 'src' root to build a full graph.
        """
        
        # Detect language from file extension
        file_ext = Path(file_path).suffix.lower()
        language_map = {
            '.java': 'java',
            '.py': 'python',
            '.cpp': 'cpp',
            '.c': 'c',
            '.js': 'javascript',
            '.ts': 'typescript'
        }
        language = language_map.get(file_ext, 'java')  # Default to java
        
        # --- FIX: Find the 'src' directory to scan ---
        # We assume the file_path is like 'sample-repo/banking-app/src/payment/File.java'
        # or 'sample-repo/python-analytics/fraud_analysis.py'
        # We want to find the root directory (either 'src' or the repo root)
        p = Path(file_path)
        src_root = p
        found_src = False
        
        # First, try to find 'src' directory
        while src_root.name != 'src' and src_root.parent != src_root:
            src_root = src_root.parent
            if src_root.name == 'src':
                found_src = True
                break
        
        # If 'src' not found, use the parent directory (e.g., python-analytics)
        if not found_src:
            # For Python files, use the directory containing the file
            # For Java files, try to find a common parent
            if language == 'python':
                directory_to_scan = str(p.parent)
            else:
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

        # Run full analysis on the directory with detected language
        print(f"🔍 Detected language: {language} for file: {file_path}")
        full_analysis = self.analyze_code(directory_to_scan, language=language)

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
        
        # NEW: Find reverse dependencies (files that depend on this file)
        reverse_direct = []
        reverse_indirect = []
        
        for dep in full_analysis["dependencies"]["direct"]:
            if file_name == dep["target"]:  # This file is the target
                reverse_direct.append({
                    "source": dep["source"],  # File that depends on us
                    "target": file_name,
                    "type": dep["type"],
                    "file": dep["source"],
                    "line": dep.get("line", 0),
                    "line_numbers": dep.get("line_numbers", []),
                    "code_reference": dep.get("code_reference", ""),
                    "code_references": dep.get("code_references", [])
                })
        
        for dep in full_analysis["dependencies"]["indirect"]:
            if file_name == dep["target"]:  # This file is the target
                reverse_indirect.append({
                    "source": dep["source"],  # File that depends on us
                    "target": file_name,
                    "type": dep["type"],
                    "file": dep["source"],
                    "line": dep.get("line", 0),
                    "line_numbers": dep.get("line_numbers", []),
                    "code_reference": dep.get("code_reference", ""),
                    "code_references": dep.get("code_references", [])
                })
        
        file_deps["reverse_direct_dependencies"] = reverse_direct
        file_deps["reverse_indirect_dependencies"] = reverse_indirect

        return file_deps

