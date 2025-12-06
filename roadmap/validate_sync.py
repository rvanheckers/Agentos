#!/usr/bin/env python3
"""
Roadmap Sync Validator
=====================

Valideert of ROADMAP_VALIDATED.md en roadmap_validated.json in sync zijn.
Gebruikt voor pre-commit checks en CI/CD pipelines.

Usage:
    python validate_sync.py [--auto-fix]
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import hashlib
import subprocess

class SyncValidator:
    def __init__(self):
        self.current_dir = Path(__file__).parent
        self.md_file = self.current_dir / "ROADMAP_VALIDATED.md"
        self.json_file = self.current_dir / "roadmap_validated.json"
        self.converter_script = self.current_dir / "md_to_json_converter.py"

    def check_files_exist(self) -> bool:
        """Check if required files exist"""
        missing_files = []

        if not self.md_file.exists():
            missing_files.append(str(self.md_file))
        if not self.json_file.exists():
            missing_files.append(str(self.json_file))
        if not self.converter_script.exists():
            missing_files.append(str(self.converter_script))

        if missing_files:
            print("❌ Missing required files:")
            for file in missing_files:
                print(f"   - {file}")
            return False

        return True

    def get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of file content"""
        if not file_path.exists():
            return ""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def get_file_mtime(self, file_path: Path) -> float:
        """Get file modification time"""
        if not file_path.exists():
            return 0.0
        return file_path.stat().st_mtime

    def generate_fresh_json(self) -> str:
        """Generate fresh JSON from MD file"""
        try:
            result = subprocess.run([
                sys.executable, str(self.converter_script),
                '--input', str(self.md_file),
                '--output', '/tmp/roadmap_temp.json'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"❌ Converter script failed:")
                print(f"   STDOUT: {result.stdout}")
                print(f"   STDERR: {result.stderr}")
                return ""

            temp_json = Path('/tmp/roadmap_temp.json')
            if temp_json.exists():
                content = temp_json.read_text()
                temp_json.unlink()  # cleanup
                return content
            return ""

        except Exception as e:
            print(f"❌ Error generating fresh JSON: {e}")
            return ""

    def compare_json_content(self, current_json: str, fresh_json: str) -> bool:
        """Compare JSON content (ignoring formatting differences)"""
        try:
            current_data = json.loads(current_json)
            fresh_data = json.loads(fresh_json)

            # Compare data structures
            return current_data == fresh_data

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return False

    def validate_sync(self) -> tuple[bool, dict]:
        """Main validation logic"""
        if not self.check_files_exist():
            return False, {"error": "Missing required files"}

        # Get file timestamps
        md_mtime = self.get_file_mtime(self.md_file)
        json_mtime = self.get_file_mtime(self.json_file)

        # Get file hashes
        md_hash = self.get_file_hash(self.md_file)
        json_hash = self.get_file_hash(self.json_file)

        print(f"📊 File Analysis:")
        print(f"   MD file:   {self.md_file.name} (modified: {datetime.fromtimestamp(md_mtime)})")
        print(f"   JSON file: {self.json_file.name} (modified: {datetime.fromtimestamp(json_mtime)})")

        # Check if MD is newer than JSON
        md_newer = md_mtime > json_mtime
        if md_newer:
            print(f"⚠️  MD file is newer than JSON file (Δ {md_mtime - json_mtime:.1f}s)")

        # Generate fresh JSON from MD
        print("🔄 Generating fresh JSON from MD...")
        fresh_json_content = self.generate_fresh_json()
        if not fresh_json_content:
            return False, {"error": "Failed to generate fresh JSON"}

        # Compare current JSON with fresh JSON
        current_json_content = self.json_file.read_text()
        content_matches = self.compare_json_content(current_json_content, fresh_json_content)

        status = {
            "files_exist": True,
            "md_mtime": md_mtime,
            "json_mtime": json_mtime,
            "md_newer": md_newer,
            "md_hash": md_hash,
            "json_hash": json_hash,
            "content_matches": content_matches,
            "time_diff": md_mtime - json_mtime
        }

        if content_matches:
            print("✅ JSON content matches MD source")
            if md_newer:
                print("ℹ️  Note: MD file is newer, but content is still in sync")
            return True, status
        else:
            print("❌ JSON content does NOT match MD source")
            print("   → JSON file needs to be regenerated from MD")
            return False, status

    def auto_fix(self) -> bool:
        """Automatically fix sync by regenerating JSON"""
        print("🔧 Auto-fixing: Regenerating JSON from MD...")

        try:
            result = subprocess.run([
                sys.executable, str(self.converter_script),
                '--input', str(self.md_file),
                '--output', str(self.json_file)
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ Auto-fix successful!")
                print("   JSON file has been regenerated from MD source")
                return True
            else:
                print("❌ Auto-fix failed:")
                print(f"   STDOUT: {result.stdout}")
                print(f"   STDERR: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Auto-fix error: {e}")
            return False

    def run(self, auto_fix: bool = False) -> int:
        """Main runner"""
        print("🔍 AgentOS Roadmap Sync Validator")
        print("=" * 40)

        is_synced, status = self.validate_sync()

        if is_synced:
            print("\n✅ RESULT: Files are in sync!")
            return 0

        print(f"\n❌ RESULT: Files are NOT in sync!")

        if auto_fix:
            if self.auto_fix():
                print("\n🎉 Auto-fix completed successfully!")
                return 0
            else:
                print("\n💥 Auto-fix failed!")
                return 1

        print("\n🔧 To fix manually:")
        print("   python roadmap/md_to_json_converter.py")
        print("\n🔧 To auto-fix:")
        print("   python roadmap/validate_sync.py --auto-fix")

        return 1

def main():
    parser = argparse.ArgumentParser(description='Validate roadmap MD/JSON sync')
    parser.add_argument('--auto-fix', action='store_true',
                       help='Automatically fix sync issues by regenerating JSON')

    args = parser.parse_args()

    validator = SyncValidator()
    return validator.run(auto_fix=args.auto_fix)

if __name__ == '__main__':
    sys.exit(main())