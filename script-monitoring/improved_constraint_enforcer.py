#!/usr/bin/env python3
"""
Verbeterde constraint enforcer die alle relevante AgentOS bestanden monitort
"""

import os
from pathlib import Path
from typing import List

def discover_all_project_files(project_path: str = "../") -> List[Path]:
    """
    Ontdek alle relevante bestanden in AgentOS project
    Inclusief: Python, JavaScript, JSON, TypeScript bestanden
    """
    project_path = Path(project_path).resolve()
    core_files = []
    
    # Relevante directories voor AgentOS
    core_directories = [
        "api", "services", "workers", "agents2", "database", "websockets",
        "ui-admin/src", "ui-v2/src", "ui-admin-clean/assets/js",
        "scripts", "script-monitoring"
    ]
    
    # Relevante file extensies
    extensions = [".py", ".js", ".json", ".ts", ".tsx", ".vue"]
    
    print(f"🔍 Scanning project: {project_path}")
    
    # Scan root level bestanden
    for ext in [".py", ".js", ".json"]:
        for file_path in project_path.glob(f"*{ext}"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                core_files.append(file_path)
                print(f"   📄 Root: {file_path.name}")
    
    # Scan core directories
    for core_dir in core_directories:
        core_dir_path = project_path / core_dir
        if core_dir_path.exists() and core_dir_path.is_dir():
            for ext in extensions:
                for file_path in core_dir_path.rglob(f"*{ext}"):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # Skip node_modules en andere ignore directories
                        if "node_modules" not in str(file_path) and ".git" not in str(file_path):
                            core_files.append(file_path)
                            rel_path = file_path.relative_to(project_path)
                            print(f"   📁 {core_dir}: {rel_path}")
    
    print(f"\n✅ Gevonden: {len(core_files)} bestanden")
    return core_files

def count_lines_in_file(file_path: Path) -> int:
    """Tel regels in bestand (skip lege regels en comments)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f.readlines()]
            # Filter lege regels en pure comments
            content_lines = [line for line in lines if line and not line.startswith(('#', '//', '/*', '*', '<!--'))]
            return len(content_lines)
    except Exception as e:
        print(f"⚠️  Fout bij lezen {file_path}: {e}")
        return 0

if __name__ == "__main__":
    print("🎯 AGENTOS FILE DISCOVERY TEST")
    print("=" * 50)
    
    files = discover_all_project_files()
    
    print(f"\n📊 STATISTIEKEN:")
    total_lines = 0
    file_stats = []
    
    for file_path in files:
        lines = count_lines_in_file(file_path)
        total_lines += lines
        rel_path = file_path.relative_to(Path("../").resolve())
        file_stats.append((str(rel_path), lines))
    
    # Sorteer op grootte
    file_stats.sort(key=lambda x: x[1], reverse=True)
    
    print(f"📈 Totaal: {total_lines} regels code")
    print(f"📁 Grootste bestanden:")
    for file_path, lines in file_stats[:10]:  # Top 10
        print(f"   {lines:4d} regels - {file_path}")