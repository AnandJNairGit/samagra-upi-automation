#!/usr/bin/env python3
"""
JSON Context Generator for LLM
Generates a structured JSON file containing the entire codebase context
while respecting .gitignore rules.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
import pathspec
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

class JSONContextGenerator:
    # Ignore common generated/build/tooling directories even if the local
    # .gitignore does not list them. This keeps scans focused on source files.
    DEFAULT_IGNORED_PATTERNS = (
        '.git/',
        '.venv/',
        '.mypy_cache/',
        '.pytest_cache/',
        '.ruff_cache/',
        '.ipynb_checkpoints/',
        '.tox/',
        '.nox/',
        '.idea/',
        '.vscode/',
        'node_modules/',
        'dist/',
        'build/',
        'htmlcov/',
        'site/',
        '.coverage',
        '.coverage.*',
        '*.egg-info/',
        'code_context.json',
        '__pycache__/',
        '**/__pycache__/',
        '*.py[cod]',
        '*$py.class',
        '.DS_Store',
    )

    def __init__(self, root_dir: str = ".", verbose: bool = False):
        """
        Initialize the context generator.
        
        Args:
            root_dir: Root directory of the project (default: current directory)
            verbose: Enable verbose logging to see what's being scanned
        """
        self.root_dir = Path(root_dir).resolve()
        self.verbose = verbose  # FIX: Set this BEFORE calling _load_gitignore()
        self.gitignore_spec = self._load_gitignore()
        
        # Track statistics
        self.stats = {
            'total_dirs_scanned': 0,
            'total_files_found': 0,
            'total_files_processed': 0,
            'files_ignored_by_gitignore': 0,
            'files_ignored_binary': 0,
            'dirs_ignored_by_gitignore': 0,
            'errors': []
        }
        
        # Store all scanned paths for validation
        self.scanned_directories: Set[Path] = set()
        self.processed_files: Set[Path] = set()
        self.ignored_files: Set[Path] = set()
        
        # Common binary file extensions to skip
        self.binary_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.zip', '.tar', '.gz',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx'
        }
        
    def _load_gitignore(self) -> pathspec.PathSpec:
        """
        Load and parse .gitignore file using pathspec library.
        
        Returns:
            PathSpec object containing gitignore patterns
        """
        gitignore_path = self.root_dir / '.gitignore'
        patterns = []
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = f.readlines()
            if self.verbose:
                print(f"✓ Loaded .gitignore with {len(patterns)} patterns")
        
        # Always ignore generated/tooling directories and the output JSON file
        patterns.extend(self.DEFAULT_IGNORED_PATTERNS)
        
        return pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            patterns
        )
    
    def _should_ignore(self, file_path: Path, is_dir: Optional[bool] = None) -> bool:
        """
        Check if a file/directory should be ignored.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if should be ignored, False otherwise
        """
        # Get relative path from root
        try:
            rel_path = file_path.relative_to(self.root_dir)
        except ValueError:
            return True
        
        # Convert to string with forward slashes for gitignore matching
        rel_path_str = str(rel_path).replace('\\', '/')
        
        # Add trailing slash for directories
        if is_dir is None:
            is_dir = file_path.is_dir()
        if is_dir:
            rel_path_str += '/'
        
        # Check against gitignore patterns
        is_ignored = self.gitignore_spec.match_file(rel_path_str)
        
        if is_ignored:
            if is_dir:
                self.stats['dirs_ignored_by_gitignore'] += 1
            else:
                self.stats['files_ignored_by_gitignore'] += 1
                self.ignored_files.add(file_path)
        
        return is_ignored
    
    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if file is likely a text file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if text file, False otherwise
        """
        # Check extension
        if file_path.suffix.lower() in self.binary_extensions:
            self.stats['files_ignored_binary'] += 1
            self.ignored_files.add(file_path)
            return False
        
        # Try reading first 1024 bytes to detect binary
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # Check for null bytes (common in binary files)
                if b'\x00' in chunk:
                    self.stats['files_ignored_binary'] += 1
                    self.ignored_files.add(file_path)
                    return False
            return True
        except Exception:
            return False
    
    def _read_file_content(self, file_path: Path) -> str:
        """
        Read file content safely.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string or error message
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            error_msg = f"Error reading {file_path}: {str(e)}"
            self.stats['errors'].append(error_msg)
            return f"[Error reading file: {str(e)}]"
    
    def _build_tree_structure(self, directory: Path) -> Dict[str, Any]:
        """
        Recursively build tree structure with file contents.
        Uses DFS (Depth-First Search) to ensure EVERY subdirectory is visited.
        
        Args:
            directory: Directory to process
            
        Returns:
            Dictionary representing the directory structure
        """
        self.stats['total_dirs_scanned'] += 1
        self.scanned_directories.add(directory)
        
        if self.verbose:
            rel_path = directory.relative_to(self.root_dir) if directory != self.root_dir else Path('.')
            print(f"📂 Scanning: {rel_path}")
        
        structure = {
            "name": directory.name if directory != self.root_dir else self.root_dir.name,
            "type": "directory",
            "path": str(directory.relative_to(self.root_dir)),
            "children": []
        }
        
        try:
            # Materialize the directory entries once so we can sort them.
            with os.scandir(directory) as entries_iter:
                entries = sorted(
                    list(entries_iter),
                    key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name)
                )
            
            for entry in entries:
                entry_path = directory / entry.name
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
                self.stats['total_files_found'] += 1
                
                # Skip if should be ignored
                if self._should_ignore(entry_path, is_dir=is_dir):
                    if self.verbose:
                        print(f"  ⊘ Ignored (gitignore): {entry.name}")
                    continue
                
                if is_dir:
                    # Recursively process subdirectories.
                    if self.verbose:
                        print(f"  ↳ Entering subdirectory: {entry.name}")
                    child_structure = self._build_tree_structure(entry_path)
                    if child_structure["children"] or child_structure.get("error"):
                        # Add directory even if empty (for completeness)
                        structure["children"].append(child_structure)
                
                elif is_file:
                    # Check if it's a text file
                    if not self._is_text_file(entry_path):
                        if self.verbose:
                            print(f"  ⊘ Ignored (binary): {entry.name}")
                        continue
                    
                    if self.verbose:
                        print(f"  ✓ Processing file: {entry.name}")
                    
                    # Add file information
                    file_info = {
                        "name": entry.name,
                        "type": "file",
                        "path": str(entry_path.relative_to(self.root_dir)),
                        "content": self._read_file_content(entry_path)
                    }
                    structure["children"].append(file_info)
                    self.processed_files.add(entry_path)
                    self.stats['total_files_processed'] += 1
        
        except PermissionError as e:
            error_msg = f"Permission denied: {directory}"
            structure["error"] = "Permission denied"
            self.stats['errors'].append(error_msg)
            if self.verbose:
                print(f"  ✗ {error_msg}")
        except Exception as e:
            error_msg = f"Error scanning {directory}: {str(e)}"
            structure["error"] = str(e)
            self.stats['errors'].append(error_msg)
            if self.verbose:
                print(f"  ✗ {error_msg}")
        
        return structure
    
    def _build_flat_structure(self) -> List[Dict[str, Any]]:
        """
        Build a flat list of all files using os.walk() for guaranteed complete traversal.
        os.walk() recursively visits EVERY subdirectory.
        
        Returns:
            List of file information dictionaries
        """
        files = []
        
        # os.walk() guarantees complete directory tree traversal
        for root, dirs, filenames in os.walk(self.root_dir):
            root_path = Path(root)
            self.stats['total_dirs_scanned'] += 1
            self.scanned_directories.add(root_path)
            
            if self.verbose:
                rel_path = root_path.relative_to(self.root_dir) if root_path != self.root_dir else Path('.')
                print(f"📂 Scanning: {rel_path}")
            
            # Filter directories to skip (modifying dirs in-place affects os.walk traversal)
            original_dirs = dirs.copy()
            dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d, is_dir=True)]
            
            if self.verbose and len(original_dirs) != len(dirs):
                ignored = set(original_dirs) - set(dirs)
                for d in ignored:
                    print(f"  ⊘ Ignored directory: {d}")
            
            for filename in sorted(filenames):
                file_path = root_path / filename
                self.stats['total_files_found'] += 1
                
                # Skip if should be ignored
                if self._should_ignore(file_path):
                    if self.verbose:
                        print(f"  ⊘ Ignored (gitignore): {filename}")
                    continue
                
                # Skip non-text files
                if not self._is_text_file(file_path):
                    if self.verbose:
                        print(f"  ⊘ Ignored (binary): {filename}")
                    continue
                
                if self.verbose:
                    print(f"  ✓ Processing: {filename}")
                
                files.append({
                    "name": filename,
                    "path": str(file_path.relative_to(self.root_dir)),
                    "content": self._read_file_content(file_path)
                })
                self.processed_files.add(file_path)
                self.stats['total_files_processed'] += 1
        
        return files
    
    def generate(self, output_file: str = "code_context.json", 
                 structure: str = "tree") -> None:
        """
        Generate the JSON context file.
        
        Args:
            output_file: Output JSON filename
            structure: "tree" for hierarchical or "flat" for flat list
        """
        print(f"🔍 Scanning project at: {self.root_dir}")
        print(f"📋 Respecting .gitignore rules...")
        
        if structure == "tree":
            print("🌲 Building tree structure (recursively visiting ALL directories)...")
            data = {
                "project_root": str(self.root_dir),
                "structure_type": "hierarchical",
                "generated_at": datetime.now().isoformat(),
                "project": self._build_tree_structure(self.root_dir)
            }
        else:
            print("📄 Building flat structure (using os.walk for complete traversal)...")
            data = {
                "project_root": str(self.root_dir),
                "structure_type": "flat",
                "generated_at": datetime.now().isoformat(),
                "files": self._build_flat_structure()
            }
        
        # Add statistics to output
        data["statistics"] = self.stats
        
        # Write to JSON file
        output_path = self.root_dir / output_file
        print(f"💾 Writing to {output_file}...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        file_size = output_path.stat().st_size / 1024  # KB
        
        print(f"\n✅ Done!")
        self._print_statistics(file_size, output_path)
    
    def _print_statistics(self, file_size: float, output_path: Path) -> None:
        """Print detailed statistics."""
        print(f"\n{'='*60}")
        print(f"📊 SCAN STATISTICS")
        print(f"{'='*60}")
        print(f"📁 Directories scanned:        {self.stats['total_dirs_scanned']}")
        print(f"📄 Total files found:          {self.stats['total_files_found']}")
        print(f"✓  Files processed:            {self.stats['total_files_processed']}")
        print(f"⊘  Files ignored (gitignore):  {self.stats['files_ignored_by_gitignore']}")
        print(f"⊘  Files ignored (binary):     {self.stats['files_ignored_binary']}")
        print(f"⊘  Directories ignored:        {self.stats['dirs_ignored_by_gitignore']}")
        print(f"💾 Output size:                {file_size:.2f} KB")
        print(f"📍 Location:                   {output_path}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(self.stats['errors']) > 5:
                print(f"   ... and {len(self.stats['errors']) - 5} more")
        
        print(f"{'='*60}\n")
    
    def _count_files(self, node: Dict[str, Any]) -> int:
        """Helper to count files in tree structure."""
        count = 0
        if node.get("type") == "file":
            return 1
        for child in node.get("children", []):
            count += self._count_files(child)
        return count
    
    def validate_completeness(self) -> Tuple[bool, List[str]]:
        """
        Validate that ALL directories and files were scanned.
        This is the TEST function that ensures nothing was missed!
        
        Returns:
            Tuple of (is_complete, list_of_issues)
        """
        print(f"\n{'='*60}")
        print(f"🔍 VALIDATION: Checking for missed files/directories...")
        print(f"{'='*60}")
        
        issues = []
        
        # Use os.walk to get ground truth of all files/dirs
        all_dirs = set()
        all_files = set()
        
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            all_dirs.add(root_path)
            
            for d in dirs:
                all_dirs.add(root_path / d)
            
            for f in files:
                file_path = root_path / f
                # Skip the output file itself
                if file_path.name == 'code_context.json':
                    continue
                all_files.add(file_path)
        
        print(f"Ground truth: {len(all_dirs)} dirs, {len(all_files)} files")
        print(f"Scanned:      {len(self.scanned_directories)} dirs")
        print(f"Processed:    {len(self.processed_files)} files")
        print(f"Ignored:      {len(self.ignored_files)} files\n")
        
        # Check for missed directories
        missed_dirs = all_dirs - self.scanned_directories
        # Filter out ignored directories
        missed_dirs_actual = {d for d in missed_dirs if not self._should_ignore(d, is_dir=True)}
        
        if missed_dirs_actual:
            issues.append(f"❌ Missed {len(missed_dirs_actual)} directories!")
            for d in list(missed_dirs_actual)[:10]:
                rel_path = d.relative_to(self.root_dir) if d != self.root_dir else Path('.')
                issues.append(f"   - {rel_path}")
            if len(missed_dirs_actual) > 10:
                issues.append(f"   ... and {len(missed_dirs_actual) - 10} more")
        
        # Check for missed files
        all_processed_or_ignored = self.processed_files | self.ignored_files
        missed_files = all_files - all_processed_or_ignored
        
        # Filter out files that should have been ignored but weren't tracked
        missed_files_actual = {f for f in missed_files if not self._should_ignore(f, is_dir=False)}
        
        if missed_files_actual:
            issues.append(f"❌ Missed {len(missed_files_actual)} files!")
            for f in list(missed_files_actual)[:10]:
                rel_path = f.relative_to(self.root_dir)
                issues.append(f"   - {rel_path}")
            if len(missed_files_actual) > 10:
                issues.append(f"   ... and {len(missed_files_actual) - 10} more")
        
        # Print results
        if issues:
            print("❌ VALIDATION FAILED - Some files/directories were missed:\n")
            for issue in issues:
                print(issue)
            print(f"\n{'='*60}\n")
            return False, issues
        else:
            print("✅ VALIDATION PASSED!")
            print("   All directories and files were properly scanned.")
            print("   Nothing was missed (except gitignored items).")
            print(f"{'='*60}\n")
            return True, []


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate JSON context of project for LLM consumption"
    )
    parser.add_argument(
        "--output", "-o",
        default="code_context.json",
        help="Output JSON filename (default: code_context.json)"
    )
    parser.add_argument(
        "--structure", "-s",
        choices=["tree", "flat"],
        default="tree",
        help="Output structure: tree (hierarchical) or flat (list)"
    )
    parser.add_argument(
        "--root", "-r",
        default=".",
        help="Root directory of the project (default: current directory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output to see all scanned files"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation test to ensure completeness"
    )
    
    args = parser.parse_args()
    
    # Generate context
    generator = JSONContextGenerator(args.root, verbose=args.verbose)
    generator.generate(args.output, args.structure)
    
    # Run validation if requested
    if args.validate:
        is_complete, issues = generator.validate_completeness()
        if not is_complete:
            exit(1)


if __name__ == "__main__":
    main()
