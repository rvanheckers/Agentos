"""
Media Source - Abstractie layer voor media opslag in AgentOS

Uniforme interface voor verschillende storage backends (local, S3, Azure).
Ondersteunt video uploads, downloads en path management.
Factory pattern voor flexibele media source instantiatie.
Gebruikt door upload/download services voor storage abstractie.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import os
import json
import subprocess
import time
from core.logging_config import get_logger

logger = get_logger("api_server")

@dataclass
class MediaMetadata:
    """Industry standard media metadata"""
    duration: float = 0.0
    size: int = 0
    format: str = "unknown"
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate: int = 0
    codec: str = "unknown"
    title: str = "Untitled"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'duration': self.duration,
            'size': self.size,
            'format': self.format,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'codec': self.codec,
            'title': self.title
        }

class MediaSource(ABC):
    """Abstract base class voor alle media sources"""
    
    @abstractmethod
    def get_local_path(self) -> str:
        """Get path naar lokaal bestand (download indien nodig)"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> MediaMetadata:
        """Get media metadata"""
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valideer of source toegankelijk is
        Returns: (is_valid, error_message)
        """
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return 'url', 'local', 's3', etc."""
        pass
    
    @property
    @abstractmethod
    def original_source(self) -> str:
        """Return originele source locatie"""
        pass

class URLMediaSource(MediaSource):
    """Handle YouTube, Vimeo, andere video platforms"""
    
    def __init__(self, url: str, download_path: str = "./downloads/"):
        self.url = url
        self.download_path = download_path
        self._local_path: Optional[str] = None
        self._metadata: Optional[MediaMetadata] = None
        
    def get_local_path(self) -> str:
        """Download video indien nodig en return lokaal pad"""
        if not self._local_path:
            logger.info(f"🌐 Downloading from URL: {self.url}")
            self._local_path = self._download()
        return self._local_path
        
    def _download(self) -> str:
        """Download video via video_downloader agent"""
        # Prepare input voor video_downloader agent
        agent_input = {
            'url': self.url,
            'output_path': self.download_path,
            'quality': 'best',
            'format': 'mp4'
        }
        
        # Execute video_downloader agent
        agent_path = os.path.join(os.path.dirname(__file__), '..', 'agents2', 'video_downloader.py')
        cmd = ['python', agent_path, json.dumps(agent_input)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                output = json.loads(result.stdout)
                if output.get('success'):
                    self._metadata = MediaMetadata(
                        duration=output.get('duration', 0),
                        size=output.get('size', 0),
                        title=output.get('title', 'Downloaded Video')
                    )
                    return output['video_path']
                else:
                    raise Exception(f"Download failed: {output.get('error', 'Unknown error')}")
            else:
                raise Exception(f"video_downloader failed with code {result.returncode}: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            raise
    
    def get_metadata(self) -> MediaMetadata:
        """Get metadata (triggers download if needed)"""
        if not self._metadata:
            self.get_local_path()  # This will populate metadata
        return self._metadata or MediaMetadata()
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate URL format and accessibility"""
        try:
            parsed = urlparse(self.url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format"
            
            # Check if yt-dlp can handle this URL
            check_cmd = ['yt-dlp', '--simulate', '--quiet', self.url]
            result = subprocess.run(check_cmd, capture_output=True, timeout=10)
            
            if result.returncode != 0:
                return False, "URL not supported or not accessible"
                
            return True, None
        except Exception as e:
            return False, str(e)
    
    @property
    def source_type(self) -> str:
        return 'url'
    
    @property
    def original_source(self) -> str:
        return self.url

class LocalMediaSource(MediaSource):
    """Handle lokale video bestanden"""
    
    def __init__(self, file_path: str):
        # Industry standard: resolve relative paths from project root
        if not os.path.isabs(file_path):
            # Clean up relative path (remove ./ prefix if present)
            if file_path.startswith('./'):
                file_path = file_path[2:]
            
            # Find project root by looking for a marker file (agentos_fabriek.db)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # Walk up directory tree to find project root
            for _ in range(5):  # Max 5 levels up
                if os.path.exists(os.path.join(project_root, 'agentos_fabriek.db')):
                    break
                parent = os.path.dirname(project_root)
                if parent == project_root:  # Reached filesystem root
                    break
                project_root = parent
            
            # If we couldn't find the marker, use working directory
            if not os.path.exists(os.path.join(project_root, 'agentos_fabriek.db')):
                project_root = os.getcwd()
                
            self.file_path = os.path.join(project_root, file_path)
        else:
            self.file_path = file_path
            
        self._metadata: Optional[MediaMetadata] = None
        logger.info(f"📁 LocalMediaSource initialized with path: {self.file_path}")
        
    def get_local_path(self) -> str:
        """Return direct pad naar lokaal bestand"""
        return self.file_path
    
    def get_metadata(self) -> MediaMetadata:
        """Extract metadata via ffprobe"""
        if not self._metadata:
            self._metadata = self._extract_metadata()
        return self._metadata
    
    def _parse_frame_rate(self, frame_rate_str: str) -> float:
        """Safely parse frame rate from ffprobe output
        
        Args:
            frame_rate_str: Frame rate string like "30/1", "29.97", "0/0"
            
        Returns:
            Frame rate as float, 0 if invalid
        """
        if not frame_rate_str or frame_rate_str == "0/0":
            return 0.0
            
        try:
            if '/' in frame_rate_str:
                numerator, denominator = frame_rate_str.split('/', 1)
                num = float(numerator)
                den = float(denominator)
                if den == 0:
                    return 0.0
                return num / den
            else:
                return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            logger.warning(f"Invalid frame rate format: {frame_rate_str}")
            return 0.0
    
    def _extract_metadata(self) -> MediaMetadata:
        """Use ffprobe to extract metadata"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', self.file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Extract video stream info
                video_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'video'), {})
                
                return MediaMetadata(
                    duration=float(data.get('format', {}).get('duration', 0)),
                    size=int(data.get('format', {}).get('size', 0)),
                    format=data.get('format', {}).get('format_name', 'unknown'),
                    width=int(video_stream.get('width', 0)),
                    height=int(video_stream.get('height', 0)),
                    fps=self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                    bitrate=int(data.get('format', {}).get('bit_rate', 0)),
                    codec=video_stream.get('codec_name', 'unknown'),
                    title=os.path.basename(self.file_path)
                )
            else:
                logger.warning(f"ffprobe failed for {self.file_path}")
                return MediaMetadata(title=os.path.basename(self.file_path))
                
        except Exception as e:
            logger.error(f"❌ Metadata extraction failed: {e}")
            return MediaMetadata(title=os.path.basename(self.file_path))
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate bestand bestaat en is leesbaar"""
        if not os.path.exists(self.file_path):
            return False, f"❌ Bestand niet gevonden: {os.path.basename(self.file_path)}"
        
        if not os.access(self.file_path, os.R_OK):
            return False, f"❌ Bestand niet leesbaar: {os.path.basename(self.file_path)}"
        
        # Check if it's a video file
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
        ext = os.path.splitext(self.file_path)[1].lower()
        
        if ext not in valid_extensions:
            if ext:
                return False, f"❌ Bestandstype '{ext}' wordt niet ondersteund. Gebruik: MP4, AVI, MOV, MKV, WebM"
            else:
                return False, f"❌ Geen geldig bestandstype gevonden. Upload een video bestand (MP4, AVI, MOV, etc.)"
        
        # Additional check: verify it's actually a video file with ffprobe
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', self.file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0 or 'video' not in result.stdout:
                return False, f"❌ Bestand lijkt beschadigd of is geen geldige video. Probeer een ander bestand."
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # ffprobe not available or timeout - skip validation but warn
            logger.warning(f"Could not validate video format for {self.file_path} - ffprobe unavailable")
        except Exception as e:
            logger.warning(f"Video validation failed for {self.file_path}: {e}")
            
        return True, None
    
    @property
    def source_type(self) -> str:
        return 'local'
    
    @property
    def original_source(self) -> str:
        return self.file_path

class MediaSourceFactory:
    """Factory pattern voor media source creation - Industry Standard"""
    
    @staticmethod
    def create(input_source: str, **kwargs) -> MediaSource:
        """Create appropriate MediaSource based on input
        
        Args:
            input_source: URL, file path, or file:// URI
            **kwargs: Additional parameters (e.g., download_path)
            
        Returns:
            MediaSource instance
            
        Raises:
            ValueError: If source type cannot be determined
        """
        # Validate input
        if input_source is None:
            raise ValueError("❌ Geen video input opgegeven. Upload een bestand of voer een URL in.")
        
        # Normalize input
        input_source = input_source.strip()
        
        # Check for empty input after stripping
        if not input_source:
            raise ValueError("❌ Geen video input opgegeven. Upload een bestand of voer een URL in.")
        
        # Check for file:// URI (reference to local file)
        if input_source.startswith('file://'):
            # Extract local path from file URI
            local_path = input_source[7:]  # Remove 'file://'
            # Handle Windows paths that might have file:///C:/
            if local_path.startswith('/') and len(local_path) > 2 and local_path[2] == ':':
                local_path = local_path[1:]  # Remove leading slash for Windows
            return LocalMediaSource(local_path)
        
        # Check for URL patterns
        elif any(input_source.startswith(prefix) for prefix in ['http://', 'https://', 'www.', 'youtube.com']):
            # Ensure proper URL format
            if input_source.startswith('www.'):
                input_source = 'https://' + input_source
            elif input_source.startswith('youtube.com'):
                input_source = 'https://' + input_source
                
            return URLMediaSource(input_source, kwargs.get('download_path', './io/downloads/'))
        
        # Check for local file (absolute or relative path)
        elif os.path.exists(input_source) or input_source.startswith(('./','/', 'C:\\', 'D:\\', 'E:\\')):
            return LocalMediaSource(input_source)
        
        # S3 support can be added here in future
        # elif input_source.startswith('s3://'):
        #     return S3MediaSource(input_source)
        
        else:
            # Try to interpret as local file path
            logger.warning(f"Unknown source type, attempting as local file: {input_source}")
            return LocalMediaSource(input_source)
    
    @staticmethod
    def is_supported(input_source: str) -> bool:
        """Check if input source is supported"""
        try:
            MediaSourceFactory.create(input_source)
            return True
        except ValueError:
            return False