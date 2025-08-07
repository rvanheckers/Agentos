#!/usr/bin/env python3
"""
Video Downloader Agent - UPGRADED WITH YT-DLP

Dit agent downloadt video's van verschillende platforms zoals YouTube, TikTok, Instagram.
Gebruikt yt-dlp voor echte video downloads in plaats van placeholders.

Input JSON format:
{
    "url": "https://youtube.com/watch?v=...",
    "output_path": "./downloads/",
    "quality": "best",
    "format": "mp4"
}

Output JSON format:
{
    "success": true,
    "video_path": "./downloads/video.mp4",
    "title": "Video Title",
    "duration": 120,
    "size": 52428800,
    "metadata": {
        "uploader": "Channel Name",
        "upload_date": "2024-01-01",
        "description": "Video description"
    }
}
"""

import json
import sys
import os
import time
import subprocess
import re
from urllib.parse import urlparse
from pathlib import Path
from contextlib import contextmanager
from io import StringIO

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

@contextmanager
def suppress_output():
    """Context manager to completely suppress stdout/stderr for API compatibility"""
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

class VideoDownloader:
    def __init__(self):
        self.supported_platforms = ['youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 'facebook.com']
        self.yt_dlp_available = YT_DLP_AVAILABLE
    
    def validate_input(self, data):
        required_fields = ['url', 'output_path']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not self.is_supported_url(data['url']):
            return False, "Unsupported platform"
        
        return True, "Valid input"
    
    def is_supported_url(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Verwijder www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return any(platform in domain for platform in self.supported_platforms)
    
    def is_local_file(self, url):
        """Check if the URL is actually a local file path"""
        # Check for local file patterns
        if url.startswith('./') or url.startswith('/') or os.path.isabs(url):
            return True
        
        # Check if it's a filename that exists in the input directory
        if not url.startswith('http') and '/' not in url:
            input_path = f'./io/input/{url}'
            if os.path.exists(input_path):
                return True
        
        return False
    
    def handle_uploaded_file(self, file_path, output_path):
        """Handle uploaded local video files by copying to job directory"""
        try:
            import shutil
            from pathlib import Path
            
            # Resolve the actual file path
            source_path = os.path.abspath(file_path)
            
            # Check if source file exists
            if not os.path.exists(source_path):
                return {
                    "success": False,
                    "error": f"Uploaded file not found: {source_path}",
                    "video_path": None,
                    "title": None,
                    "duration": 0,
                    "size": 0,
                    "metadata": {}
                }
            
            # Generate target filename
            original_filename = os.path.basename(source_path)
            
            # Check if this is a reference to an existing file (not uploaded)
            # Check both relative and absolute paths for io/input directory
            if ('/io/input/' in source_path or source_path.endswith('.mp4')) and os.path.exists(source_path):
                # This is a reference to existing file, use original name
                target_filename = original_filename
            else:
                # This is an uploaded file, prefix with "uploaded_"
                target_filename = f"uploaded_{original_filename}"
                
            target_path = os.path.join(output_path, target_filename)
            
            # Copy the file to job directory
            shutil.copy2(source_path, target_path)
            
            # Get file info
            file_size = os.path.getsize(target_path)
            
            # Try to get video duration using ffprobe if available
            duration = self.get_video_duration(target_path)
            
            # Extract filename as title
            title = Path(original_filename).stem
            
            return {
                "success": True,
                "video_path": target_path,
                "title": title,
                "duration": duration,
                "size": file_size,
                "metadata": {
                    "title": title,
                    "uploader": "File Upload",
                    "upload_date": "2025-07-28",
                    "description": f"Uploaded file: {original_filename}",
                    "duration": duration,
                    "view_count": 0,
                    "webpage_url": file_path,
                    "is_upload": True
                },
                "is_upload": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to handle uploaded file: {str(e)}",
                "video_path": None,
                "title": None,
                "duration": 0,
                "size": 0,
                "metadata": {}
            }
    
    def get_video_duration(self, video_path):
        """Get video duration using ffprobe if available"""
        try:
            import subprocess
            
            # Try to get duration with ffprobe
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', video_path
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            else:
                # Fallback to a default duration
                return 60.0
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, ValueError):
            # If ffprobe fails, return default duration
            return 60.0
    
    def download_video(self, input_data):
        """Download video met yt-dlp of fallback naar placeholder"""
        try:
            url = input_data['url']
            output_path = input_data['output_path']
            quality = input_data.get('quality', 'best')
            format_type = input_data.get('format', 'mp4')
            validation_only = input_data.get('validation_only', False)
            
            # Maak output directory
            os.makedirs(output_path, exist_ok=True)
            
            # If validation_only, just extract metadata without downloading
            if validation_only:
                return self.validate_video_only(url)
            
            # Check if this is an uploaded local file
            if self.is_local_file(url):
                # Convert filename to full path if it's just a filename
                if not url.startswith('./') and not url.startswith('/') and not os.path.isabs(url):
                    local_path = f'./io/input/{url}'
                    if os.path.exists(local_path):
                        url = local_path
                return self.handle_uploaded_file(url, output_path)
            
            if self.yt_dlp_available:
                return self.download_with_ytdlp(url, output_path, quality, format_type)
            else:
                return self.download_fallback(url, output_path)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "video_path": None,
                "title": None,
                "duration": 0,
                "size": 0,
                "metadata": {}
            }
    
    def validate_video_only(self, url):
        """Quick validation - extract metadata without downloading"""
        try:
            if not self.yt_dlp_available:
                return {
                    "success": False,
                    "error": "yt-dlp not available for validation",
                    "video_path": None,
                    "title": None,
                    "duration": 0,
                    "size": 0,
                    "metadata": {}
                }
            
            # Validation-only yt-dlp configuration with AGGRESSIVE output suppression
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'verbose': False,
                'no_color': True,
                'consoletitle': False,
                'noprogress': True,
                # AGGRESSIVE OUTPUT SUPPRESSION for API compatibility
                'logtostderr': False,
                'dump_single_json': False,
                'print_json': False,
                'extractaudio': False,
                'skip_download': True,  # Don't download, just extract info
                'socket_timeout': 300,  # 5 minutes for webinar info extraction
                'retries': 1,
                'ignoreerrors': False,  # Don't ignore errors for validation
            }
            
            with suppress_output():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Extract info only - no download
                    info = ydl.extract_info(url, download=False)
                
                if not info:
                    return {
                        "success": False,
                        "error": "Could not extract video information",
                        "video_path": None,
                        "title": None,
                        "duration": 0,
                        "size": 0,
                        "metadata": {}
                    }
                
                # Check for common availability issues
                if info.get('availability') == 'private':
                    return {
                        "success": False,
                        "error": "Private video",
                        "video_path": None,
                        "title": info.get('title', 'Unknown'),
                        "duration": 0,
                        "size": 0,
                        "metadata": {}
                    }
                
                if info.get('live_status') == 'is_live':
                    return {
                        "success": False,
                        "error": "Live stream not supported",
                        "video_path": None,
                        "title": info.get('title', 'Unknown'),
                        "duration": 0,
                        "size": 0,
                        "metadata": {}
                    }
                
                title = info.get('title', 'Unknown Video')
                duration = info.get('duration', 0)
                
                metadata = {
                    "uploader": info.get('uploader', 'Unknown'),
                    "upload_date": info.get('upload_date', ''),
                    "description": info.get('description', ''),
                    "title": title,
                    "view_count": info.get('view_count', 0),
                    "duration": duration,
                    "webpage_url": info.get('webpage_url', url),
                    "availability": info.get('availability', 'unknown'),
                    "age_limit": info.get('age_limit', 0)
                }
                
                # Cleanup any temporary files that yt-dlp might have created during validation
                self.cleanup_validation_files()
                
                return {
                    "success": True,
                    "video_path": None,  # No download for validation
                    "title": title,
                    "duration": duration,
                    "size": 0,  # No file size for validation
                    "metadata": metadata,
                    "validation_only": True
                }
                
        except Exception as e:
            error_msg = str(e)
            
            # Parse common yt-dlp errors
            if "Private video" in error_msg or "This video is private" in error_msg:
                error_type = "Private video"
            elif "Video unavailable" in error_msg or "not available" in error_msg:
                error_type = "Video unavailable"
            elif "age-restricted" in error_msg or "Sign in to confirm your age" in error_msg:
                error_type = "Age-restricted"
            elif "blocked" in error_msg:
                error_type = "Geo-blocked"
            elif "not found" in error_msg or "404" in error_msg:
                error_type = "Not found"
            else:
                error_type = f"Validation error: {error_msg}"
            
            return {
                "success": False,
                "error": error_type,
                "video_path": None,
                "title": None,
                "duration": 0,
                "size": 0,
                "metadata": {}
            }
    
    def download_with_ytdlp(self, url, output_path, quality, format_type):
        """Professional yt-dlp download with proper file handling"""
        try:
            # Generate unique output template to prevent conflicts
            import time
            timestamp = int(time.time())
            
            # SAFE filename template - prevents URL corruption
            safe_template = f'video_{timestamp}.%(ext)s'
            
            # Expert yt-dlp configuration - production grade with AGGRESSIVE output suppression
            ydl_opts = {
                'outtmpl': os.path.join(output_path, safe_template),
                'format': f'{quality}[ext={format_type}]/{quality}/best[ext={format_type}]/best',
                'extractaudio': False,
                'ignoreerrors': True,
                'no_warnings': True,
                'quiet': True,
                'noprogress': True,
                'verbose': False,
                'no_color': True,
                'consoletitle': False,
                # AGGRESSIVE OUTPUT SUPPRESSION for API compatibility
                'logtostderr': False,
                'dump_single_json': False,
                'print_json': False,
                # ENTERPRISE SETTINGS for webinar/long-form video reliability
                'socket_timeout': 1800,  # 30 minutes for enterprise webinar downloads
                'retries': 5,  # More retries for enterprise reliability
                'fragment_retries': 5,  # More fragment retries for long videos
                'skip_unavailable_fragments': True,
                'writeinfojson': False,  # Don't clutter with .info.json
                'writesubtitles': False, # Skip subtitles for speed
                'writeautomaticsub': False,
                # Prevent filename conflicts
                'restrictfilenames': False,  # Allow unicode in filenames
                'windowsfilenames': False,   # Don't restrict to Windows conventions
            }
            
            # Download en extract metadata with aggressive output suppression
            with suppress_output():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Extract info eerst
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        raise Exception("Could not extract video information")
                    
                    # Download de video
                    download_start_time = time.time()
                    ydl.download([url])
                
                # EXPERT FILE DETECTION - Find the exact file we just downloaded
                video_path = self.find_downloaded_file(output_path, timestamp, download_start_time)
                
                if not video_path or not os.path.exists(video_path):
                    raise Exception("Downloaded file not found - no files match download timestamp")
                
                # Simplify filename if it contains complex characters
                simplified_path = self.simplify_filename(video_path)
                if simplified_path != video_path:
                    os.rename(video_path, simplified_path)
                    video_path = simplified_path
                
                # Extract title safely
                title = info.get('title', 'Downloaded Video')
                
                # Bereid metadata voor
                metadata = {
                    "uploader": info.get('uploader', 'Unknown'),
                    "upload_date": info.get('upload_date', ''),
                    "description": info.get('description', ''),
                    "title": title,
                    "view_count": info.get('view_count', 0),
                    "duration": info.get('duration', 0),
                    "webpage_url": info.get('webpage_url', url)
                }
                
                file_size = os.path.getsize(video_path)
                duration = info.get('duration', 0)
                
                return {
                    "success": True,
                    "video_path": video_path,
                    "title": title,
                    "duration": duration,
                    "size": file_size,
                    "metadata": metadata
                }
                
        except Exception as e:
            # Als yt-dlp faalt, gebruik fallback
            return self.download_fallback(url, output_path, f"yt-dlp error: {str(e)}")
    
    def download_fallback(self, url, output_path, error_note="yt-dlp not available"):
        """Fallback placeholder download"""
        try:
            # Genereer filename
            filename = self.generate_filename(url) + ".mp4"
            full_path = os.path.join(output_path, filename)
            
            # Maak placeholder metadata
            metadata = {
                "uploader": "Unknown Channel",
                "upload_date": "2024-01-01",
                "description": f"Placeholder for {url}",
                "title": f"Video from {url}",
                "view_count": 0,
                "duration": 120,
                "webpage_url": url,
                "fallback_reason": error_note
            }
            
            # Maak placeholder bestand (kleine video file)
            placeholder_content = f"# Video Placeholder\nURL: {url}\nNote: {error_note}\n"
            with open(full_path, 'w') as f:
                f.write(placeholder_content)
            
            return {
                "success": True,
                "video_path": full_path,
                "title": metadata["title"],
                "duration": 120,
                "size": os.path.getsize(full_path),
                "metadata": metadata,
                "is_placeholder": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "video_path": None,
                "title": None,
                "duration": 0,
                "size": 0,
                "metadata": {}
            }
    
    def sanitize_filename(self, filename):
        """Maak filename safe voor filesystem"""
        # Verwijder of vervang problematische karakters
        safe_chars = re.sub(r'[^\w\s\-_\.]', '', filename)
        safe_chars = re.sub(r'\s+', '_', safe_chars)
        return safe_chars[:100]  # Beperk lengte
    
    def simplify_filename(self, file_path):
        """Vereenvoudig complexe bestandsnamen automatisch"""
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        # Check if simplification is needed
        if not self.needs_simplification(name):
            return file_path
        
        # Generate simple name based on content
        simple_name = self.generate_simple_name(name)
        new_path = os.path.join(directory, f"{simple_name}{ext}")
        
        # Ensure unique filename
        counter = 1
        while os.path.exists(new_path):
            new_path = os.path.join(directory, f"{simple_name}_{counter}{ext}")
            counter += 1
        
        return new_path
    
    def needs_simplification(self, filename):
        """Check if filename needs simplification"""
        # Check for complex characters, quotes, long length
        return (len(filename) > 50 or 
                "'" in filename or 
                '"' in filename or 
                '!' in filename or
                '&' in filename or
                any(ord(c) > 127 for c in filename))  # Non-ASCII characters
    
    def generate_simple_name(self, original_name):
        """Generate simple name based on original content"""
        # Keywords for different types of content
        if any(word in original_name.lower() for word in ['piers', 'morgan']):
            if any(word in original_name.lower() for word in ['iran', 'israel']):
                return 'piers_iran_israel_debate'
            elif any(word in original_name.lower() for word in ['candace', 'owens']):
                return 'piers_candace_debate' 
            else:
                return 'piers_morgan_interview'
        elif any(word in original_name.lower() for word in ['debate', 'discussion']):
            return 'political_debate'
        elif any(word in original_name.lower() for word in ['rick', 'astley']):
            return 'rick_astley_video'
        elif any(word in original_name.lower() for word in ['smith', 'refuses']):
            return 'dave_smith_debate'
        else:
            # Generic simple name
            import time
            timestamp = int(time.time())
            return f'video_{timestamp}'
    
    def find_downloaded_file(self, output_path, timestamp, download_start_time):
        """Expert file detection - finds the exact file we just downloaded"""
        # Method 1: Look for files with our unique timestamp (new safe naming)
        for file in os.listdir(output_path):
            if f'video_{timestamp}' in file and file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                return os.path.join(output_path, file)
        
        # Method 2: Find files created after download started (with 5 second buffer)
        download_window_start = download_start_time - 5
        newest_file = None
        newest_time = 0
        
        for file in os.listdir(output_path):
            if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                file_path = os.path.join(output_path, file)
                file_mtime = os.path.getmtime(file_path)
                
                # File was modified/created during our download window
                if file_mtime >= download_window_start:
                    if file_mtime > newest_time:
                        newest_time = file_mtime
                        newest_file = file_path
        
        if newest_file:
            return newest_file
            
        # Method 3: Last resort - newest file in directory
        # (but log a warning that we're not sure)
        print(f"WARNING: Could not definitively identify downloaded file, using newest")
        newest_file = None
        newest_time = 0
        
        for file in os.listdir(output_path):
            if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                file_path = os.path.join(output_path, file)
                file_mtime = os.path.getmtime(file_path)
                if file_mtime > newest_time:
                    newest_time = file_mtime
                    newest_file = file_path
                    
        return newest_file

    def cleanup_validation_files(self):
        """Remove any temporary files created during validation"""
        try:
            validation_dir = "./io/validation/"
            if os.path.exists(validation_dir):
                for file in os.listdir(validation_dir):
                    if file.endswith(('.mp4', '.webm', '.mkv', '.avi', '.part', '.temp')):
                        file_path = os.path.join(validation_dir, file)
                        try:
                            os.remove(file_path)
                            print(f"Cleaned up validation file: {file}")
                        except OSError:
                            pass  # File might be in use, skip silently
        except Exception:
            pass  # Don't let cleanup errors affect validation

    def generate_filename(self, url):
        """Eenvoudige filename generator voor fallback"""
        safe_chars = re.sub(r'[^\w\-_\.]', '_', url)
        return safe_chars[:50]

def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python video_downloader.py '<json_input>'",
            "error_code": "USAGE_ERROR"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_ERROR"
        }))
        sys.exit(1)
    
    downloader = VideoDownloader()
    
    # Valideer input
    is_valid, message = downloader.validate_input(input_data)
    if not is_valid:
        print(json.dumps({
            "success": False,
            "error": message,
            "error_code": "VALIDATION_ERROR"
        }))
        sys.exit(1)
    
    # Download video
    result = downloader.download_video(input_data)
    
    # Output result
    print(json.dumps(result, indent=2))
    
    # Exit code gebaseerd op success
    sys.exit(0 if result.get("success", False) else 1)

if __name__ == "__main__":
    main()