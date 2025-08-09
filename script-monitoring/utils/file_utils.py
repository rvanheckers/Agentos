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
    """Count non-empty lines in any text file (Python, JavaScript, JSON, etc.)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f.readlines()]
            # Filter out empty lines and common comment patterns
            content_lines = []
            for line in lines:
                if line and not line.startswith(('#', '//', '/*', '*', '<!--')):
                    content_lines.append(line)
            return len(content_lines)
    except Exception:
        return 0

def find_python_files(project_path: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in project, excluding specified directories"""
    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', 'docs', 'tests', 'examples']

    python_files = []
    for root, dirs, files in os.walk(project_path):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return python_files

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
