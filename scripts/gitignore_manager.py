#!/usr/bin/env python3
"""
GitIgnore Manager - Automated .gitignore maintenance and validation
Ensures repository stays clean and doesn't include unwanted files
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

class GitIgnoreManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.gitignore_path = self.repo_path / ".gitignore"
        self.large_file_threshold = 10 * 1024 * 1024  # 10MB
        self.media_extensions = {
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.3gp'],
            'audio': ['.mp3', '.wav', '.aac', '.ogg', '.wma', '.flac', '.m4a'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.raw']
        }
        self.generated_patterns = [
            '__pycache__', '*.pyc', 'node_modules', 'dist', 'build',
            '*.log', '*.tmp', '*.temp', '*.cache', '.DS_Store'
        ]

    def check_git_status(self) -> Dict:
        """Check current git status and find untracked files"""
        try:
            # Get untracked files
            result = subprocess.run(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            untracked = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Get tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            tracked = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Get ignored files
            result = subprocess.run(
                ['git', 'status', '--ignored', '--porcelain'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            ignored = [line[3:] for line in result.stdout.strip().split('\n') if line.startswith('!! ')]

            return {
                'tracked': tracked,
                'untracked': untracked,
                'ignored': ignored
            }
        except subprocess.CalledProcessError as e:
            print(f"Error checking git status: {e}")
            return {'tracked': [], 'untracked': [], 'ignored': []}

    def find_large_files(self, files: List[str]) -> List[Tuple[str, int]]:
        """Find files larger than threshold"""
        large_files = []
        for file in files:
            file_path = self.repo_path / file
            if file_path.exists() and file_path.is_file():
                size = file_path.stat().st_size
                if size > self.large_file_threshold:
                    large_files.append((file, size))
        return large_files

    def find_media_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Find media files that might need to be ignored"""
        media_files = {'video': [], 'audio': [], 'image': []}
        for file in files:
            file_ext = Path(file).suffix.lower()
            for media_type, extensions in self.media_extensions.items():
                if file_ext in extensions:
                    media_files[media_type].append(file)
        return media_files

    def check_io_folders(self) -> Dict[str, List[str]]:
        """Check io folders for content that should be ignored"""
        io_issues = {}
        io_base = self.repo_path / 'io'

        if io_base.exists():
            for folder in ['downloads', 'uploads', 'output', 'input', 'temp']:
                folder_path = io_base / folder
                if folder_path.exists():
                    files = []
                    for item in folder_path.rglob('*'):
                        if item.is_file() and item.name != '.gitkeep':
                            rel_path = item.relative_to(self.repo_path)
                            files.append(str(rel_path))
                    if files:
                        io_issues[folder] = files
        return io_issues

    def validate_gitignore(self) -> Dict:
        """Validate current .gitignore configuration"""
        issues = []
        recommendations = []

        if not self.gitignore_path.exists():
            issues.append("No .gitignore file found!")
            return {'issues': issues, 'recommendations': recommendations}

        with open(self.gitignore_path, 'r') as f:
            gitignore_content = f.read()

        # Check for essential patterns
        essential_patterns = {
            'Python': ['__pycache__/', '*.pyc', '.env'],
            'Node.js': ['node_modules/'],
            'Logs': ['*.log'],
            'Database': ['*.db', '*.sqlite'],
            'OS': ['.DS_Store', 'Thumbs.db']
        }

        for category, patterns in essential_patterns.items():
            missing = [p for p in patterns if p not in gitignore_content]
            if missing:
                recommendations.append(f"Missing {category} patterns: {', '.join(missing)}")

        return {'issues': issues, 'recommendations': recommendations}

    def generate_report(self) -> Dict:
        """Generate comprehensive gitignore health report"""
        print("🔍 Analyzing repository...")

        git_status = self.check_git_status()
        report = {
            'timestamp': datetime.now().isoformat(),
            'repo_path': str(self.repo_path),
            'statistics': {
                'tracked_files': len(git_status['tracked']),
                'untracked_files': len(git_status['untracked']),
                'ignored_files': len(git_status['ignored'])
            }
        }

        # Find problematic files in tracked files
        print("📊 Checking tracked files...")
        tracked_large = self.find_large_files(git_status['tracked'])
        tracked_media = self.find_media_files(git_status['tracked'])

        if tracked_large:
            report['warnings'] = report.get('warnings', [])
            report['warnings'].append({
                'type': 'large_tracked_files',
                'message': f"Found {len(tracked_large)} large files being tracked",
                'files': [{'file': f, 'size_mb': f'{s/(1024*1024):.2f}'} for f, s in tracked_large]
            })

        if any(tracked_media.values()):
            report['warnings'] = report.get('warnings', [])
            total_media = sum(len(files) for files in tracked_media.values())
            report['warnings'].append({
                'type': 'media_files_tracked',
                'message': f"Found {total_media} media files being tracked",
                'files': tracked_media
            })

        # Check untracked files
        print("🔎 Checking untracked files...")
        untracked_large = self.find_large_files(git_status['untracked'])
        self.find_media_files(git_status['untracked'])

        if untracked_large:
            report['info'] = report.get('info', [])
            report['info'].append({
                'type': 'large_untracked_files',
                'message': f"Found {len(untracked_large)} large untracked files",
                'files': [{'file': f, 'size_mb': f'{s/(1024*1024):.2f}'} for f, s in untracked_large]
            })

        # Check IO folders
        print("📁 Checking IO folders...")
        io_issues = self.check_io_folders()
        if io_issues:
            report['io_folder_issues'] = io_issues

        # Validate gitignore
        print("✅ Validating .gitignore...")
        validation = self.validate_gitignore()
        if validation['issues'] or validation['recommendations']:
            report['gitignore_validation'] = validation

        return report

    def auto_fix(self, report: Dict) -> List[str]:
        """Automatically fix common issues"""
        fixes_applied = []

        # Check if we need to add patterns to gitignore
        if 'warnings' in report:
            for warning in report['warnings']:
                if warning['type'] == 'media_files_tracked':
                    print("\n⚠️  Found media files in repository!")
                    print("These files should probably be ignored.")
                    response = input("Add media file patterns to .gitignore? (y/n): ")
                    if response.lower() == 'y':
                        self.add_to_gitignore([
                            "\n# Auto-added media patterns",
                            "*.mp4", "*.avi", "*.mov", "*.mkv",
                            "*.mp3", "*.wav", "*.aac"
                        ])
                        fixes_applied.append("Added media file patterns to .gitignore")

        # Create .gitkeep files if needed
        if 'io_folder_issues' in report:
            print("\n📁 IO folders contain files but might need .gitkeep files")
            response = input("Create .gitkeep files in IO folders? (y/n): ")
            if response.lower() == 'y':
                io_base = self.repo_path / 'io'
                for folder in ['downloads', 'uploads', 'output', 'input', 'temp']:
                    folder_path = io_base / folder
                    if folder_path.exists():
                        gitkeep = folder_path / '.gitkeep'
                        if not gitkeep.exists():
                            gitkeep.touch()
                            fixes_applied.append(f"Created .gitkeep in io/{folder}")

        return fixes_applied

    def add_to_gitignore(self, patterns: List[str]):
        """Add patterns to .gitignore if not already present"""
        if not self.gitignore_path.exists():
            self.gitignore_path.touch()

        with open(self.gitignore_path, 'r') as f:
            current_content = f.read()

        patterns_to_add = []
        for pattern in patterns:
            if pattern not in current_content:
                patterns_to_add.append(pattern)

        if patterns_to_add:
            with open(self.gitignore_path, 'a') as f:
                f.write('\n' + '\n'.join(patterns_to_add))

    def print_report(self, report: Dict):
        """Print formatted report"""
        print("\n" + "="*60)
        print("📋 GITIGNORE HEALTH REPORT")
        print("="*60)
        print(f"📅 Generated: {report['timestamp']}")
        print(f"📁 Repository: {report['repo_path']}")
        print("\n📊 Statistics:")
        print(f"  • Tracked files: {report['statistics']['tracked_files']}")
        print(f"  • Untracked files: {report['statistics']['untracked_files']}")
        print(f"  • Ignored files: {report['statistics']['ignored_files']}")

        if 'warnings' in report:
            print("\n⚠️  WARNINGS:")
            for warning in report['warnings']:
                print(f"\n  {warning['message']}")
                if warning['type'] == 'large_tracked_files':
                    for file_info in warning['files'][:5]:  # Show max 5
                        print(f"    • {file_info['file']} ({file_info['size_mb']} MB)")
                elif warning['type'] == 'media_files_tracked':
                    for media_type, files in warning['files'].items():
                        if files:
                            print(f"    • {media_type}: {len(files)} files")
                            for file in files[:3]:  # Show max 3 per type
                                print(f"      - {file}")

        if 'io_folder_issues' in report:
            print("\n📁 IO Folder Issues:")
            for folder, files in report['io_folder_issues'].items():
                print(f"  • io/{folder}/: {len(files)} files found (should be empty except .gitkeep)")

        if 'gitignore_validation' in report:
            validation = report['gitignore_validation']
            if validation['recommendations']:
                print("\n💡 Recommendations:")
                for rec in validation['recommendations']:
                    print(f"  • {rec}")

        print("\n" + "="*60)

def main():
    print("🚀 GitIgnore Manager - Automated Repository Cleaner")
    print("="*60)

    # Initialize manager
    manager = GitIgnoreManager()

    # Generate report
    report = manager.generate_report()

    # Save report to file
    report_file = Path('gitignore_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Full report saved to: {report_file}")

    # Print report
    manager.print_report(report)

    # Ask for auto-fix
    if 'warnings' in report or 'io_folder_issues' in report:
        print("\n🔧 Issues detected that can be auto-fixed.")
        response = input("Would you like to apply automatic fixes? (y/n): ")
        if response.lower() == 'y':
            fixes = manager.auto_fix(report)
            if fixes:
                print("\n✅ Fixes applied:")
                for fix in fixes:
                    print(f"  • {fix}")
            else:
                print("\n❌ No fixes applied.")
    else:
        print("\n✅ No major issues found!")

    print("\n🎉 GitIgnore health check complete!")

if __name__ == "__main__":
    main()
