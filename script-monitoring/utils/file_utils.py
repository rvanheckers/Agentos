"""
File Utils - Hulpfuncties voor Script Size Monitoring in AgentOS

Wat doet het: Telt regels code in alle bestanden (Python, JavaScript, JSON, TypeScript, etc.)
Voor wie: Developers die willen voorkomen dat scripts te groot worden
Gebruikt door: constraint_enforcer.py om te checken of bestanden binnen limieten blijven
Waarom: Te grote bestanden zijn moeilijk te onderhouden en debuggen
Monitort: 145+ bestanden in alle AgentOS directories
"""

import os
from pathlib import Path
from typing import List, Dict, Any

def count_lines_in_file(file_path: Path) -> int:
    """Count non-empty lines in any text file (Python, JavaScript, JSON, etc.) - optimized"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # More efficient counting without storing all lines
            return sum(1 for line in f if line.strip() and
                      not line.strip().startswith(('#', '//', '/*', '*', '<!--')))
    except Exception:
        return 0

def find_code_files(project_path: Path, file_types: List[str] = None, exclude_dirs: List[str] = None) -> Dict[str, List[Path]]:
    """Find all code files by type in project, excluding specified directories"""
    if file_types is None:
        file_types = ['.py', '.js', '.ts', '.tsx', '.vue', '.css', '.scss', '.html', '.json', '.yaml', '.yml']

    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules',
                       'logs', 'io/input', 'io/output', 'io/downloads', 'database/postgresql',
                       '.env', 'temp', 'cache',
                       # Exclude backup directories and other projects
                       'AgentOS - kopie', 'AgentOS_Copy', 'AgentOS-BACKUP', 'Nieuwe map',
                       'Clipper&VideoUI', 'SmartFoodScan', 'vibecoder', 'XXXClipper']

    code_files = {ext: [] for ext in file_types}

    for root, dirs, files in os.walk(project_path):
        # Remove excluded directories from search (support names én relatieve paden)
        ex_names = {n.lower() for n in exclude_dirs if ('/' not in n and os.sep not in n)}
        ex_rel = tuple(
            n.strip('/').replace('\\', '/').lower()
            for n in exclude_dirs if ('/' in n or os.sep in n)
        )
        rel_root = os.path.relpath(root, project_path).replace('\\', '/').lstrip('./').lower()

        def is_excluded(dname: str) -> bool:
            if dname.lower() in ex_names:
                return True
            rel = f"{rel_root}/{dname}".lstrip('./').lower() if rel_root and rel_root != '.' else dname.lower()
            return any(rel == p or rel.startswith(p + '/') for p in ex_rel)

        dirs[:] = [d for d in dirs if not is_excluded(d)]

        for file in files:
            for ext in file_types:
                if file.endswith(ext):
                    code_files[ext].append(Path(root) / file)
                    break

    return code_files

def find_python_files(project_path: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in project, excluding specified directories"""
    code_files = find_code_files(project_path, ['.py'], exclude_dirs)
    return code_files['.py']

def get_project_structure(project_path: Path) -> Dict[str, Any]:
    """Get basic project structure information"""
    structure = {
        'files': [],
        'total_lines': 0,
        'modules': {}
    }

    python_files = find_python_files(project_path)

    for file_path in python_files:
        rel_path = file_path.relative_to(project_path)
        lines = count_lines_in_file(file_path)

        structure['files'].append(str(rel_path))
        structure['total_lines'] += lines
        structure['modules'][str(rel_path)] = {
            'lines': lines,
            'path': str(file_path)
        }

    return structure
