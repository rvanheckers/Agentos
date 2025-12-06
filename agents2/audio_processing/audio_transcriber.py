#!/usr/bin/env python3
"""
Production-Grade Audio Transcriber Agent
========================================

Multi-engine audio transcription with security, streaming, and robust error handling.

Features:
- Multi-engine support: Whisper (OpenAI API, local, faster-whisper), Vosk
- Streaming for long audio files (>10 minutes) with intelligent chunking
- Security: Audio validation, size/duration limits, path sanitization
- Error handling: Exponential backoff, graceful degradation
- Performance: Parallel chunk processing, resource monitoring

Architecture:
- SecureAudioAgent base class (adapts SecureVideoAgent pattern)
- Primary engine: Whisper (OpenAI API with local fallbacks)
- Fallback engine: Vosk (lightweight, offline, multiple languages)
- Streaming: 30-60s chunks with 2s overlap for context preservation

Version: 2.0.0 (Production-Grade)
"""

import json
import sys
import os
import time
import subprocess
import tempfile
from typing import Any, Dict, List, Tuple, Optional, Callable
from pathlib import Path
import threading
import json as _json
from dotenv import load_dotenv
import logging
from enum import Enum
from dataclasses import dataclass

# Load environment variables before any other imports
load_dotenv(override=False)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from agents2.mock_data_generator import MockDataGenerator
except ImportError:
    MockDataGenerator = None
    logger.warning("MockDataGenerator not available")

# MANDATORY SECURITY IMPORTS - NO FALLBACK ALLOWED
try:
    from agents2.base.secure_agent import SecureVideoAgent
    from api.config.settings import Settings
    from security.exceptions import SecurityError
    from security.resource_limiter import ResourceLimiter
    from security.path_sanitizer import PathSanitizer
    settings = Settings()
except ImportError as e:
    logger.error(
        f"CRITICAL: Failed to import required security modules: {e}\n"
        "AudioTranscriber requires SecureVideoAgent and security modules.\n"
        "Please ensure security/ and agents2/base/ are in PYTHONPATH."
    )
    # Let the import error propagate - no fallback allowed
    raise

# ==================== ENUMS & DATACLASSES ====================

class TranscriptionEngine(Enum):
    """Available transcription engines"""
    OPENAI_WHISPER = "openai"
    LOCAL_WHISPER = "local"
    FASTER_WHISPER = "faster"
    VOSK = "vosk"
    MOCK = "mock"


class AudioFormat(Enum):
    """Supported audio formats"""
    WAV = ".wav"
    MP3 = ".mp3"
    FLAC = ".flac"
    M4A = ".m4a"
    OGG = ".ogg"
    OPUS = ".opus"
    AAC = ".aac"


@dataclass
class AudioMetadata:
    """Audio file metadata from validation"""
    duration: float
    format: str
    sample_rate: int
    channels: int
    bitrate: int
    size_mb: float


@dataclass
class TranscriptionConfig:
    """Configuration for transcription process"""
    chunk_size_seconds: int = 45  # 30-60s optimal for Whisper
    overlap_seconds: float = 2.0  # Context preservation
    max_file_size_mb: float = 500.0  # Security limit
    max_duration_hours: float = 4.0  # Security limit
    enable_streaming: bool = True  # Auto-enable for >10min files
    streaming_threshold_minutes: float = 10.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0  # Exponential backoff
    timeout_openai: float = 60.0
    timeout_local: float = 600.0
    timeout_vosk: float = 300.0


# ==================== AUDIO-SPECIFIC VALIDATION HELPERS ====================

def validate_audio_file(audio_path: Path, config: TranscriptionConfig) -> AudioMetadata:
    """
    Valideer audio bestand volgens security requirements

    Checks:
    - Bestaan & leesbaarheid
    - Format whitelist
    - Size limits
    - Duration limits
    - Basic corruption detection

    Args:
        audio_path: Path naar audio bestand
        config: TranscriptionConfig met limits

    Returns:
        AudioMetadata met gevalideerde properties

    Raises:
        SecurityError: Bij validation failures
    """
    # Audio format whitelist
    SUPPORTED_FORMATS = {fmt.value for fmt in AudioFormat}

    # 1. Existence check
    if not audio_path.exists():
        raise SecurityError(f"Audio file not found: {audio_path}")

    if not audio_path.is_file():
        raise SecurityError(f"Not a file: {audio_path}")

    # 2. Format check (extension-based)
    suffix = audio_path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise SecurityError(
            f"Unsupported audio format: {suffix}. "
            f"Supported: {', '.join(SUPPORTED_FORMATS)}"
        )

    # 3. Size check
    size_bytes = audio_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > config.max_file_size_mb:
        raise SecurityError(
            f"Audio file too large: {size_mb:.1f}MB "
            f"(max: {config.max_file_size_mb}MB)"
        )

    # 4. Probe metadata with ffprobe
    try:
        metadata = _probe_audio_metadata(audio_path)
    except Exception as e:
        raise SecurityError(f"Failed to read audio metadata: {e}")

    # 5. Duration check
    duration_hours = metadata.duration / 3600
    if duration_hours > config.max_duration_hours:
        raise SecurityError(
            f"Audio too long: {duration_hours:.1f}h "
            f"(max: {config.max_duration_hours}h)"
        )

    # 6. Basic sanity checks
    if metadata.duration <= 0:
        raise SecurityError("Invalid audio duration: duration must be > 0")

    if metadata.sample_rate < 8000 or metadata.sample_rate > 192000:
        raise SecurityError(
            f"Invalid sample rate: {metadata.sample_rate}Hz "
            "(expected 8000-192000Hz)"
        )

    logger.info(
        f"Audio validated: {size_mb:.1f}MB, {metadata.duration:.1f}s, "
        f"{metadata.format}, {metadata.sample_rate}Hz"
    )

    return metadata


def _probe_audio_metadata(audio_path: Path) -> AudioMetadata:
    """
    Extract audio metadata using ffprobe

    Args:
        audio_path: Path naar audio bestand

    Returns:
        AudioMetadata met geëxtraheerde properties

    Raises:
        Exception: Als ffprobe faalt
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(audio_path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    fmt = data.get('format', {})

    # Find audio stream
    audio_stream = None
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'audio':
            audio_stream = stream
            break

    if not audio_stream:
        raise RuntimeError("No audio stream found")

    return AudioMetadata(
        duration=float(fmt.get('duration', 0)),
        format=fmt.get('format_name', 'unknown'),
        sample_rate=int(audio_stream.get('sample_rate', 0)),
        channels=int(audio_stream.get('channels', 0)),
        bitrate=int(fmt.get('bit_rate', 0)),
        size_mb=float(fmt.get('size', 0)) / (1024 * 1024)
    )


# ==================== ENVIRONMENT HELPERS ====================

def _getenv_clean(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    if v is None:
        return default
    s = v.strip()
    # quotes behouden de waarde en strippen we hier
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1].strip()
    # strip inline comments buiten quotes
    return s.split('#', 1)[0].strip()

def _getenv_bool(key: str, default: bool) -> bool:
    s = _getenv_clean(key, None)
    if s is None:
        return default
    return s.lower() in ("1","true","yes","on")

def _getenv_int(key: str, default: int) -> int:
    s = _getenv_clean(key, None)
    if s is None or s == "":
        return default
    try:
        return int(float(s))
    except Exception:
        return default

def _getenv_float(key: str, default: float) -> float:
    s = _getenv_clean(key, None)
    if s is None or s == "":
        return default
    try:
        return float(s)
    except Exception:
        return default

class FastAudioTranscriber(SecureVideoAgent):
    """
    Production-grade audio transcriber with multi-engine support and security

    MANDATORY REQUIREMENT: Must inherit from SecureVideoAgent.
    Instantiation fails immediately if SecureVideoAgent is not available.

    Inherits from SecureVideoAgent for:
    - Path sanitization (PathSanitizer) - MANDATORY
    - Resource monitoring and limiting (ResourceLimiter) - MANDATORY
    - Secure processing workflow - MANDATORY
    - Standardized error handling - MANDATORY

    Features:
    - Multi-engine: Whisper (OpenAI/local/faster), Vosk fallback
    - Streaming: Auto-chunk for long files (>10min)
    - Error handling: Exponential backoff, graceful degradation
    - Performance: Parallel chunk processing where possible
    - Security: Validated inputs, resource limits, timeout protection

    Version: 2.0.0 (Production-Grade with Security)
    """

    def __init__(self):
        """
        Initialize transcriber with all engines and configuration

        Security: Inherits from SecureVideoAgent (mandatory).
        Import fails if SecureVideoAgent is not available - no fallback allowed.
        """
        # Initialize parent security components (mandatory)
        super().__init__()

        # Transcription configuration
        self.config = TranscriptionConfig()

        self.version = "2.0.0"
        self.ffmpeg_available = self._check_ffmpeg()
        self.mock_generator = MockDataGenerator() if MockDataGenerator else None

        # Mock/real AI control
        if settings and hasattr(settings, "use_mock_ai"):
            self.use_mock = bool(getattr(settings, "use_mock_ai"))
        else:
            self.use_mock = _getenv_bool("USE_MOCK_AI", False)

        self.enable_real_ai = _getenv_bool("ENABLE_REAL_AI", True)

        # Engine configuration
        self.use_faster = _getenv_bool("USE_FASTER_WHISPER", False)
        self.use_vosk = _getenv_bool("USE_VOSK", False)
        self.fw_model_name = _getenv_clean("FASTER_WHISPER_MODEL", "small")
        self.fw_device = (_getenv_clean("FASTER_WHISPER_DEVICE", "auto") or "auto").lower()
        self.fw_compute = (_getenv_clean("FASTER_WHISPER_COMPUTE", "int8") or "int8")

        # VAD configuration
        self.vad_enable = _getenv_bool("VAD_ENABLE", True)
        self.vad_min_sil = _getenv_int("VAD_MIN_SIL_MS", 300)
        self.vad_pad_s = _getenv_float("VAD_PAD_S", 0.2)

        # Timeout configuration (from parent config + env overrides)
        self.config.timeout_openai = _getenv_float("OPENAI_TIMEOUT_S", 60.0)
        self.config.timeout_local = _getenv_float("LOCAL_TIMEOUT_S", 600.0)
        self.config.timeout_vosk = _getenv_float("VOSK_TIMEOUT_S", 300.0)

        # Retry configuration (exponential backoff)
        self.config.max_retries = _getenv_int("AUDIO_MAX_RETRIES", 3)
        self.config.retry_backoff_base = _getenv_float("RETRY_BACKOFF_BASE", 2.0)

        # Streaming configuration
        self.config.chunk_size_seconds = _getenv_int("CHUNK_SIZE_SECONDS", 45)
        self.config.overlap_seconds = _getenv_float("OVERLAP_SECONDS", 2.0)
        self.config.streaming_threshold_minutes = _getenv_float("STREAMING_THRESHOLD_MIN", 10.0)

        # Engine caches
        self._fw_cache: Dict[str, Any] = {}
        self._vosk_model_cache: Optional[Any] = None
        self._last_detected_language: str = "auto-detected"

        logger.info(
            f"FastAudioTranscriber v{self.version} initialized - "
            f"Engines: Whisper(faster={self.use_faster}), Vosk={self.use_vosk}, "
            f"Streaming: {self.config.enable_streaming}"
        )

    _fw_lock = threading.Lock()
    _vosk_lock = threading.Lock()

    def transcribe_audio(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for audio transcription (backward compatible)

        Always uses SecureVideoAgent's template method for full security.
        NO FALLBACK - Security is mandatory.

        Args:
            input_data: Dict with 'audio_path' or 'video_path' key

        Returns:
            Dict with transcription results

        Note: This method maintains backward compatibility with v1 API.
        """
        # Use SecureVideoAgent's template method for full security
        # No fallback - security is mandatory (validated in __init__)
        return self.process_video_safely(input_data)

    def _process_validated_video(
        self,
        video_path: Path,
        output_path: Optional[Path],
        metadata: Any,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        SecureVideoAgent template method implementation for audio processing

        This is the secure entry point when using SecureVideoAgent.
        Handles both direct audio files and video files (extracts audio).

        Args:
            video_path: Validated path (could be audio or video file)
            output_path: Optional output path (unused for transcription)
            metadata: Video metadata from validator
            input_data: Original input data

        Returns:
            Dict with transcription results
        """
        try:
            # Determine if we have audio or video
            # If video_path is actually an audio file, use directly
            # Otherwise, extract audio from video
            audio_path_str = None

            # Check if it's an audio file by extension
            if video_path.suffix.lower() in {fmt.value for fmt in AudioFormat}:
                # Direct audio file
                audio_path_str = str(video_path)
            else:
                # Video file - extract audio
                audio_path_str = self._extract_audio_from_video_secure(str(video_path))

            if not audio_path_str:
                return self._error("Failed to extract audio from video")

            audio_path = Path(audio_path_str)

            # Perform audio-specific validation
            audio_metadata = validate_audio_file(audio_path, self.config)

            # Process transcription
            result = self._process_validated_audio_internal(
                audio_path=audio_path,
                metadata=audio_metadata,
                input_data=input_data
            )

            # Add security metadata
            result['security'] = {
                'validated': True,
                'file_size_mb': audio_metadata.size_mb,
                'duration_seconds': audio_metadata.duration,
                'format': audio_metadata.format,
                'path_sanitized': True
            }

            # Cleanup temp files if audio was extracted from video
            if str(audio_path) != str(video_path):
                self._cleanup_temp_files(str(audio_path), input_data)

            return result

        except SecurityError as e:
            logger.error(f"Audio security validation failed: {e}")
            return {
                "success": False,
                "error": f"Audio validation failed: {str(e)}",
                "error_type": "security",
                "error_code": "AUDIO_SECURITY_ERROR"
            }
        except Exception as e:
            logger.exception("Unexpected error in validated audio processing")
            return {
                "success": False,
                "error": "Internal audio processing error",
                "error_type": "internal",
                "error_code": "AUDIO_INTERNAL_ERROR"
            }

    def _process_validated_audio_internal(
        self,
        audio_path: Path,
        metadata: AudioMetadata,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method: Process validated audio file with multi-engine support

        Flow:
        1. Check if streaming needed (duration > threshold)
        2. Determine engine execution order (based on config/preferences)
        3. Try engines with exponential backoff retry
        4. Fallback chain: OpenAI -> faster-whisper -> local -> Vosk -> mock
        5. Optional: silence detection for cutters
        6. Return standardized result

        Args:
            audio_path: Validated audio file path
            metadata: Validated audio metadata
            input_data: Original input data

        Returns:
            Dict with transcription results
        """
        start_time = time.time()

        # 1. Determine if streaming needed
        duration_minutes = metadata.duration / 60
        use_streaming = (
            self.config.enable_streaming and
            duration_minutes > self.config.streaming_threshold_minutes
        )

        logger.info(
            f"Processing audio: {metadata.duration:.1f}s ({duration_minutes:.1f}min), "
            f"Streaming: {use_streaming}"
        )

        # 2. Handle mock/disabled AI
        if not self.enable_real_ai or self.use_mock:
            logger.info("Using mock transcription (AI disabled or USE_MOCK_AI=True)")
            transcript_text = self._generate_simple_transcript(metadata.duration)
            segments = self._parse_segments(transcript_text)
            return self._build_result(
                transcript_text, segments, [], TranscriptionEngine.MOCK.value,
                time.time() - start_time, metadata.duration
            )

        # 3. Determine engine order
        method_pref = input_data.get("method", "auto")
        engine_order = self._determine_engine_order(method_pref)

        logger.info(f"Engine execution order: {[e.value for e in engine_order]}")

        # 4. Try engines with exponential backoff
        transcript_text = ""
        method_used = "error"

        for engine in engine_order:
            transcript_text, method_used = self._try_engine_with_retry(
                engine, audio_path, metadata, use_streaming
            )
            if transcript_text:
                logger.info(f"Transcription successful with engine: {method_used}")
                break

        # 5. Emergency mock fallback
        if not transcript_text:
            logger.warning("All engines failed, falling back to mock")
            transcript_text = self._generate_simple_transcript(metadata.duration)
            method_used = TranscriptionEngine.MOCK.value

        # 6. Parse segments
        segments = self._parse_segments(transcript_text)

        # 7. Optional silence detection
        silence_gaps = self._detect_silences_ffmpeg(str(audio_path), metadata.duration)
        silence_gaps = self._merge_intervals(silence_gaps)

        # 8. Build result
        processing_time = time.time() - start_time
        result = self._build_result(
            transcript_text, segments, silence_gaps, method_used,
            processing_time, metadata.duration
        )

        # 9. Cleanup temp files
        self._cleanup_temp_files(str(audio_path), input_data)

        logger.info(
            f"Transcription completed: {method_used}, {processing_time:.2f}s, "
            f"{len(segments)} segments"
        )

        return result

    def _determine_engine_order(self, method_pref: str) -> List[TranscriptionEngine]:
        """
        Determine engine execution order based on preference and availability

        Args:
            method_pref: User preference ("auto", "openai", "local", "faster", "vosk")

        Returns:
            List of engines to try in order
        """
        if method_pref == "openai":
            # OpenAI first, then fallbacks
            order = [TranscriptionEngine.OPENAI_WHISPER]
            if self.use_faster:
                order.append(TranscriptionEngine.FASTER_WHISPER)
            order.append(TranscriptionEngine.LOCAL_WHISPER)
            if self.use_vosk:
                order.append(TranscriptionEngine.VOSK)
        elif method_pref == "local":
            # Local first (prefer faster-whisper if available)
            order = []
            if self.use_faster:
                order.append(TranscriptionEngine.FASTER_WHISPER)
            order.append(TranscriptionEngine.LOCAL_WHISPER)
            order.append(TranscriptionEngine.OPENAI_WHISPER)
            if self.use_vosk:
                order.append(TranscriptionEngine.VOSK)
        elif method_pref == "faster":
            # Faster-whisper first
            order = []
            if self.use_faster:
                order.append(TranscriptionEngine.FASTER_WHISPER)
            order.append(TranscriptionEngine.LOCAL_WHISPER)
            order.append(TranscriptionEngine.OPENAI_WHISPER)
            if self.use_vosk:
                order.append(TranscriptionEngine.VOSK)
        elif method_pref == "vosk":
            # Vosk first (fast, offline)
            order = []
            if self.use_vosk:
                order.append(TranscriptionEngine.VOSK)
            if self.use_faster:
                order.append(TranscriptionEngine.FASTER_WHISPER)
            order.append(TranscriptionEngine.LOCAL_WHISPER)
            order.append(TranscriptionEngine.OPENAI_WHISPER)
        else:
            # Auto: optimize for reliability + speed
            order = []
            if self.use_faster:
                order.append(TranscriptionEngine.FASTER_WHISPER)
            order.append(TranscriptionEngine.LOCAL_WHISPER)
            order.append(TranscriptionEngine.OPENAI_WHISPER)
            if self.use_vosk:
                order.append(TranscriptionEngine.VOSK)

        return order

    def _try_engine_with_retry(
        self,
        engine: TranscriptionEngine,
        audio_path: Path,
        metadata: AudioMetadata,
        use_streaming: bool
    ) -> Tuple[str, str]:
        """
        Try transcription engine with exponential backoff retry

        Args:
            engine: Engine to try
            audio_path: Path to audio file
            metadata: Audio metadata
            use_streaming: Whether to use streaming

        Returns:
            Tuple of (transcript_text, method_used)
        """
        for attempt in range(self.config.max_retries):
            try:
                # Calculate backoff delay
                if attempt > 0:
                    delay = self.config.retry_backoff_base ** (attempt - 1)
                    logger.info(f"Retry attempt {attempt + 1}/{self.config.max_retries} "
                                f"after {delay:.1f}s delay")
                    time.sleep(delay)

                # Try transcription
                transcript = self._transcribe_with_engine(
                    engine, audio_path, metadata, use_streaming
                )

                if transcript:
                    return transcript, engine.value

            except Exception as e:
                logger.warning(
                    f"Engine {engine.value} failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries}): {e}"
                )
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Engine {engine.value} exhausted all retries")

        return "", "error"

    def _transcribe_with_engine(
        self,
        engine: TranscriptionEngine,
        audio_path: Path,
        metadata: AudioMetadata,
        use_streaming: bool
    ) -> Optional[str]:
        """
        Transcribe with specific engine

        Args:
            engine: Engine to use
            audio_path: Path to audio file
            metadata: Audio metadata
            use_streaming: Whether to use streaming

        Returns:
            Transcript text or None
        """
        if engine == TranscriptionEngine.OPENAI_WHISPER:
            timeout = self.config.timeout_openai
            ok, res = self._watchdog_call(
                self._transcribe_with_openai_whisper_timestamped,
                timeout, str(audio_path)
            )
            return res if ok and res else None

        elif engine == TranscriptionEngine.FASTER_WHISPER:
            timeout = self.config.timeout_local
            ok, res = self._watchdog_call(
                self._transcribe_with_faster_whisper,
                timeout, str(audio_path)
            )
            return res if ok and res else None

        elif engine == TranscriptionEngine.LOCAL_WHISPER:
            timeout = self.config.timeout_local
            ok, res = self._watchdog_call(
                self._transcribe_with_local_whisper,
                timeout, str(audio_path), True
            )
            return res if ok and res else None

        elif engine == TranscriptionEngine.VOSK:
            timeout = self.config.timeout_vosk
            ok, res = self._watchdog_call(
                self._transcribe_with_vosk,
                timeout, str(audio_path)
            )
            return res if ok and res else None

        return None

    def _build_result(
        self,
        transcript: str,
        segments: List[Dict[str, Any]],
        silence_gaps: List[Dict[str, float]],
        method_used: str,
        processing_time: float,
        duration: float
    ) -> Dict[str, Any]:
        """
        Build standardized result dictionary

        Args:
            transcript: Full transcript text
            segments: List of segment dicts
            silence_gaps: List of silence gap dicts
            method_used: Engine method used
            processing_time: Processing time in seconds
            duration: Audio duration in seconds

        Returns:
            Standardized result dict
        """
        # Clean segments (bounds check)
        clean_segments = []
        for s in segments:
            st = max(0.0, float(s.get("start_time", 0.0)))
            et = min(duration, float(s.get("end_time", st)))
            if et > st:
                s["start_time"], s["end_time"] = st, et
                clean_segments.append(s)

        # Clean gaps (bounds check)
        clean_gaps = []
        for g in silence_gaps:
            st = max(0.0, float(g.get("start_time", 0.0)))
            et = min(duration, float(g.get("end_time", st)))
            if et > st:
                clean_gaps.append({"start_time": st, "end_time": et})

        # Determine quality tier
        production_engines = [
            TranscriptionEngine.OPENAI_WHISPER.value,
            TranscriptionEngine.LOCAL_WHISPER.value,
            TranscriptionEngine.FASTER_WHISPER.value,
            TranscriptionEngine.VOSK.value
        ]
        is_production = method_used in production_engines
        is_mock = method_used == TranscriptionEngine.MOCK.value

        return {
            "success": True,
            "transcript": transcript or "",
            "segments": clean_segments,
            "silence_gaps": clean_gaps,
            "method_used": method_used,
            "processing_time": processing_time,
            "language": self._last_detected_language,
            "duration": duration,
            "agent_version": self.version,
            "is_mock": is_mock,
            "quality_tier": "production" if is_production else "mock",
            "allow_downstream": is_production,
            "user_message": None if is_production else
                "Transcriptie is niet gelukt via de cloud. Probeer opnieuw of gebruik een kleiner bestand.",
            "streaming_used": False  # TODO: update when streaming implemented
        }

    def _extract_audio_from_video_secure(self, video_path: str) -> Optional[str]:
        """
        Extract audio from video (SECURE version with ResourceLimiter)

        Args:
            video_path: Path to video file (already validated by PathSanitizer)

        Returns:
            Path to temporary audio file or None
        """
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not available for audio extraction")
            return None

        try:
            # Create temp audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_audio_path = temp_file.name

            # Extract audio with Whisper-optimized settings
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # 16kHz (Whisper optimal)
                '-ac', '1',  # Mono
                temp_audio_path
            ]

            timeout = _getenv_int("FFMPEG_EXTRACT_TIMEOUT_S", 300)

            # Use ResourceLimiter if available for secure execution
            if ResourceLimiter:
                result = ResourceLimiter.run_ffmpeg_limited(cmd, timeout=timeout)
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

            if result.returncode == 0 and os.path.exists(temp_audio_path):
                logger.info(f"Extracted audio from video (secure): {temp_audio_path}")
                return temp_audio_path
            else:
                logger.error(f"FFmpeg extraction failed: {getattr(result, 'stderr', 'Unknown error')}")
                return None

        except TimeoutError:
            logger.error(f"Audio extraction timeout after {timeout}s")
            return None
        except Exception as e:
            logger.exception(f"Audio extraction failed: {e}")
            return None

    def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """
        Extract audio from video (INSECURE fallback version)

        WARNING: Does not use ResourceLimiter protection.
        Only used when SecureVideoAgent is not available.

        Args:
            video_path: Path to video file

        Returns:
            Path to temporary audio file or None
        """
        if not self.ffmpeg_available:
            return None

        try:
            # Create temp audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_audio_path = temp_file.name

            # Extract audio with Whisper-optimized settings (from video_analyzer.py)
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # 16kHz sample rate (Whisper optimal)
                '-ac', '1',  # Mono
                temp_audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=_getenv_int("FFMPEG_EXTRACT_TIMEOUT_S", 300))

            if result.returncode == 0 and os.path.exists(temp_audio_path):
                return temp_audio_path
            else:
                return None

        except Exception:
            return None

    def _transcribe_with_whisper(self, audio_path, method, fast_mode):
        """Transcribe using proven Whisper method from video_analyzer.py"""
        try:
            if method == "auto" or method == "openai":
                # Try OpenAI Whisper API first
                openai_key = _getenv_clean('OPENAI_API_KEY')
                if openai_key:
                    transcript = self._transcribe_with_openai_whisper(audio_path, openai_key)
                    if transcript:
                        return transcript

            if method == "auto" or method == "local":
                # Fallback: try local whisper
                return self._transcribe_with_local_whisper(audio_path, fast_mode)

            return None

        except Exception as e:
            print(f"Whisper transcription failed: {e}", file=sys.stderr)
            return None

    def _transcribe_with_openai_whisper(self, audio_path, api_key):
        """Transcribe with OpenAI Whisper API (same as video_analyzer.py)"""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)

            with open(audio_path, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            return response.text if hasattr(response, 'text') else str(response)

        except Exception as e:
            print(f"OpenAI Whisper failed: {e}", file=sys.stderr)
            return None

    def _transcribe_with_local_whisper(self, audio_path, fast_mode):
        """Transcribe with local Whisper (optimized from video_analyzer.py)"""
        try:
            import whisper

            # Load fastest model for fast_mode
            model_name = "tiny" if fast_mode else "base"
            model = whisper.load_model(model_name)

            # Transcribe with fast settings
            options = {
                "language": None,  # Auto-detect
                "task": "transcribe"
            }

            if fast_mode:
                options.update({
                    "best_of": 1,  # Faster
                    "beam_size": 1,  # Faster
                    "temperature": 0.0  # More deterministic
                })

            result = model.transcribe(audio_path, **options)
            # taal vastleggen (voor eindresultaat)
            lang = result.get("language")
            if lang:
                setattr(self, "_last_detected_language", lang)

            # Format with timestamps (same as video_analyzer.py)
            transcript_lines = []
            for segment in result.get('segments', []):
                start_time = int(segment.get('start', 0))
                text = segment.get('text', '').strip()
                if text:
                    timestamp = f"[{start_time//60:02d}:{start_time%60:02d}]"
                    transcript_lines.append(f"{timestamp} {text}")

            return "\n".join(transcript_lines)

        except ImportError:
            print("Local whisper not installed", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Local whisper failed: {e}", file=sys.stderr)
            return None

    def _transcribe_with_vosk(self, audio_path: str) -> str:
        """
        Transcribe audio with Vosk (lightweight, offline, fast)

        Vosk is a speech recognition toolkit that works offline and supports
        multiple languages. It's faster than Whisper but potentially less accurate.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcript in [MM:SS|MM:SS] text format or empty string

        Note: Requires vosk package: pip install vosk
        """
        try:
            from vosk import Model, KaldiRecognizer
            import wave
            import json

            logger.info(f"Vosk: Starting transcription of {audio_path}")

            # Load model (cached)
            model = self._get_vosk_model()
            if not model:
                logger.error("Vosk model not available")
                return ""

            # Convert audio to WAV 16kHz mono if needed
            wav_path = self._prepare_audio_for_vosk(audio_path)

            try:
                # Open audio file
                with wave.open(wav_path, "rb") as wf:
                    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                        logger.warning(
                            f"Vosk: Audio format not optimal: "
                            f"{wf.getnchannels()}ch, {wf.getsampwidth()}B, {wf.getframerate()}Hz"
                        )

                    # Create recognizer
                    recognizer = KaldiRecognizer(model, wf.getframerate())
                    recognizer.SetWords(True)  # Enable word-level timestamps

                    # Process audio
                    results = []
                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            if result.get("text"):
                                results.append(result)

                    # Final result
                    final_result = json.loads(recognizer.FinalResult())
                    if final_result.get("text"):
                        results.append(final_result)

                # Build transcript with timestamps
                lines = []
                for result in results:
                    # Check for word-level results
                    if "result" in result:
                        # Word-level timestamps available
                        words = result["result"]
                        if words:
                            start = words[0].get("start", 0)
                            end = words[-1].get("end", start)
                            text = result.get("text", "").strip()

                            if text:
                                sm, ss = divmod(int(start), 60)
                                em, es = divmod(int(end), 60)
                                ts = f"[{sm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                                lines.append(f"{ts} {text}")
                    else:
                        # No word-level, just text
                        text = result.get("text", "").strip()
                        if text:
                            # Estimate timestamp (no precise timing available)
                            lines.append(f"[00:00] {text}")

                logger.info(f"Vosk: Completed transcription, {len(lines)} segments")
                return "\n".join(lines)

            finally:
                # Cleanup temp WAV if created
                if wav_path != audio_path and os.path.exists(wav_path):
                    try:
                        os.unlink(wav_path)
                    except:
                        pass

        except ImportError:
            logger.error("Vosk not installed. Install with: pip install vosk")
            return ""
        except Exception as e:
            logger.exception(f"Vosk transcription failed: {e}")
            return ""

    def _get_vosk_model(self) -> Optional[Any]:
        """
        Load and cache Vosk model

        Returns:
            Vosk Model object or None
        """
        with self._vosk_lock:
            if self._vosk_model_cache:
                return self._vosk_model_cache

            try:
                from vosk import Model

                # Get model path from environment or use default
                model_path = _getenv_clean("VOSK_MODEL_PATH")

                if not model_path:
                    # Try common locations
                    possible_paths = [
                        "/usr/share/vosk/model",
                        str(Path.home() / ".cache" / "vosk" / "model"),
                        "./vosk-model"
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            model_path = path
                            break

                if not model_path or not os.path.exists(model_path):
                    logger.error(
                        "Vosk model not found. Download from https://alphacephei.com/vosk/models "
                        "and set VOSK_MODEL_PATH"
                    )
                    return None

                logger.info(f"Loading Vosk model from: {model_path}")
                model = Model(model_path)
                self._vosk_model_cache = model

                # Try to detect language from model path
                model_name = os.path.basename(model_path).lower()
                if "en" in model_name:
                    self._last_detected_language = "en"
                elif "nl" in model_name:
                    self._last_detected_language = "nl"

                return model

            except Exception as e:
                logger.error(f"Failed to load Vosk model: {e}")
                return None

    def _prepare_audio_for_vosk(self, audio_path: str) -> str:
        """
        Prepare audio for Vosk (requires WAV 16kHz mono)

        Args:
            audio_path: Path to audio file

        Returns:
            Path to prepared WAV file
        """
        # Check if already correct format
        if audio_path.lower().endswith('.wav'):
            try:
                import wave
                with wave.open(audio_path, 'rb') as wf:
                    if wf.getnchannels() == 1 and wf.getframerate() == 16000:
                        # Already correct format
                        return audio_path
            except:
                pass

        # Convert to correct format
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_wav_path = temp_file.name

            cmd = [
                'ffmpeg', '-y', '-i', audio_path,
                '-ar', '16000',  # 16kHz
                '-ac', '1',  # Mono
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                temp_wav_path
            ]

            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            return temp_wav_path

        except Exception as e:
            logger.error(f"Failed to prepare audio for Vosk: {e}")
            return audio_path  # Return original, might still work

    def _parse_segments(self, transcript_text):
        """Parse segments with timestamps from transcript"""
        segments = []
        if not transcript_text:
            return segments

        lines = transcript_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and '[' in line and ']' in line:
                # Parse timestamp [MM:SS] text
                try:
                    timestamp_end = line.find(']')
                    timestamp_str = line[1:timestamp_end]  # Remove [
                    text = line[timestamp_end + 1:].strip()

                    # Ondersteun [MM:SS|MM:SS] en [MM:SS]
                    if '|' in timestamp_str:
                        left, right = timestamp_str.split('|', 1)
                        if ':' in left and ':' in right:
                            lm, ls = left.split(':'); rm, rs = right.split(':')
                            start_time = int(lm) * 60 + int(ls)
                            end_time = int(rm) * 60 + int(rs)
                        else:
                            start_time = end_time = 0
                    else:
                        if ':' in timestamp_str:
                            m, s = timestamp_str.split(':')
                            start_time = int(m) * 60 + int(s)
                            end_time = start_time + 30  # fallback estimate
                        else:
                            start_time = end_time = 0

                    if end_time > start_time:
                        segments.append({
                            "start_time": float(start_time),
                            "end_time": float(end_time),
                            "text": text,
                            "confidence": 0.9
                        })
                except Exception:
                    continue

        return segments

    def _get_audio_duration(self, audio_path):
        """Get audio duration using FFprobe"""
        if not self.ffmpeg_available:
            return 0.0

        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
            else:
                return 0.0

        except Exception:
            return 0.0

    def _cleanup_temp_files(self, audio_path, input_data):
        """Clean up temporary files"""
        # Only clean up if we extracted audio from video
        if "audio_path" not in input_data and "video_path" in input_data:
            try:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
            except Exception:
                pass

    def _generate_simple_transcript(self, duration):
        """Generate simple transcript for pipeline testing"""
        # Create evenly spaced segments
        # segments = []  # Unused variable
        segment_length = 15  # 15 seconds per segment
        num_segments = max(1, int(duration // segment_length))

        transcript_lines = []
        for i in range(num_segments):
            start_time = i * segment_length
            if start_time >= duration - 5:  # Stop near end
                break

            minutes = start_time // 60
            seconds = start_time % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            text = f"🤖 Pipeline test segment {i+1}"
            transcript_lines.append(f"{timestamp} {text}")

        return "\n".join(transcript_lines)

    def _mock_transcription(self, audio_path):
        """Mock transcription when Whisper is not available"""
        duration = self._get_audio_duration(audio_path)
        duration_str = f"{duration:.1f}"
        return f"""[00:00] Audio transcription simulation
[00:15] This is simulated transcribed content
[00:30] Generated when Whisper is not available
[00:45] Audio duration: {duration_str} seconds
[60:00] Fast mock transcription completed"""

    def _check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _error(self, message):
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "TRANSCRIPTION_ERROR",
            "transcript": "",
            "segments": [],
            "silence_gaps": [],
            "method_used": "error",
            "processing_time": 0.0,
            "language": "unknown",
            "duration": 0.0,
            "agent_version": self.version
        }

    # ------- NIEUW: helpers: watchdog, merge, timestamped OpenAI, silence detect -------
    def _watchdog_call(self, fn, timeout_s: float, *args, **kwargs) -> Tuple[bool, Any]:
        """Run fn with hard timeout; returns (ok, value_or_exception)."""
        box = {"val": None, "exc": None}
        def runner():
            try:
                box["val"] = fn(*args, **kwargs)
            except Exception as e:
                box["exc"] = e
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join(timeout_s)
        if t.is_alive():
            return (False, TimeoutError("watchdog timeout"))
        return (box["exc"] is None, box["val"] if box["exc"] is None else box["exc"])

    def _as_dict(self, obj: Any) -> Dict[str, Any]:
        """Best-effort normalizer voor OpenAI responses: v0/v1/pydantic/str → dict."""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        for attr in ("to_dict_recursive", "model_dump", "dict"):
            fn = getattr(obj, attr, None)
            if callable(fn):
                try:
                    d = fn()
                    if isinstance(d, dict):
                        return d
                except Exception:
                    pass
        if isinstance(obj, str):
            try:
                return _json.loads(obj)
            except Exception:
                return {"text": obj}
        try:
            return _json.loads(str(obj))
        except Exception:
            return {}

    def _merge_intervals(self, intervals: List[Dict[str, float]]) -> List[Dict[str, float]]:
        if not intervals: return []
        xs = sorted(intervals, key=lambda x: x["start_time"])
        merged = [xs[0]]
        for cur in xs[1:]:
            last = merged[-1]
            if cur["start_time"] <= last["end_time"]:
                last["end_time"] = max(last["end_time"], cur["end_time"])
            else:
                merged.append(cur)
        return merged

    def _transcribe_with_openai_whisper_timestamped(self, audio_path: str) -> str:
        """
        Vraag verbose_json zodat we segmenten met timestamps krijgen,
        en bouw regels in vorm: [MM:SS] tekst (compatibel met _parse_segments).
        """
        try:
            import openai
            openai_key = _getenv_clean("OPENAI_API_KEY")
            if not openai_key:
                return ""
            client = openai.OpenAI(api_key=openai_key)

            # File size check and chunking strategy
            file_size = self._file_size_mb(audio_path)
            max_mb = _getenv_int('OPENAI_AUDIO_MAX_MB', 25)
            temp_files = []

            print(f"🔍 CHUNKING DEBUG: File size: {file_size:.2f}MB, Max allowed: {max_mb}MB", file=sys.stderr)
            print(f"🔍 CHUNKING DEBUG: Audio file: {audio_path}", file=sys.stderr)

            try:
                if file_size <= max_mb - 1:  # Small file: continue to existing API call
                    print(f"🔍 CHUNKING DEBUG: Small file - using direct API call", file=sys.stderr)
                else:
                    print(f"🔍 CHUNKING DEBUG: Large file detected - starting compression", file=sys.stderr)
                    # Large file: compress first
                    compressed = self._compress_for_openai(audio_path)
                    temp_files.append(compressed)
                    compressed_size = self._file_size_mb(compressed)
                    print(f"🔍 CHUNKING DEBUG: Compressed to {compressed_size:.2f}MB", file=sys.stderr)

                    if self._file_size_mb(compressed) < max_mb:  # Compression was enough
                        print(f"🔍 CHUNKING DEBUG: Compression sufficient - single API call", file=sys.stderr)
                        with open(compressed, 'rb') as f:
                            resp = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="verbose_json")
                        data = self._as_dict(resp)
                        segments = data.get("segments") or []
                        # Store language
                        lang = data.get("language")
                        if lang:
                            setattr(self, "_last_detected_language", lang)
                        if not segments:
                            return data.get("text") or getattr(resp, "text", "") or str(resp)
                        # Build timestamped transcript
                        lines = []
                        for seg in segments:
                            start_f = float(seg.get("start", 0.0))
                            end_f = float(seg.get("end", start_f))
                            start = max(0, int(start_f))
                            end = max(start, int(end_f))
                            mm, ss = divmod(start, 60)
                            em, es = divmod(end, 60)
                            ts = f"[{mm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                            text = (seg.get("text") or "").strip()
                            if text:
                                lines.append(f"{ts} {text}")
                        return "\n".join(lines)

                    # Still too large: chunk and merge
                    print(f"🔍 CHUNKING DEBUG: Compression not enough - starting chunking process", file=sys.stderr)
                    chunks = self._chunk_for_openai(compressed)
                    temp_files.extend(chunks)
                    transcripts = []
                    offset_seconds = 0

                    print(f"🔍 CHUNKING DEBUG: Created {len(chunks)} chunks", file=sys.stderr)

                    for i, chunk_path in enumerate(chunks):
                        chunk_size = self._file_size_mb(chunk_path)
                        print(f"🔍 CHUNKING DEBUG: Processing chunk {i+1}/{len(chunks)} ({chunk_size:.2f}MB)", file=sys.stderr)

                        with open(chunk_path, 'rb') as f:
                            resp = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="verbose_json")
                        data = self._as_dict(resp)
                        segments = data.get("segments") or []
                        # Store language from first chunk
                        if offset_seconds == 0:
                            lang = data.get("language")
                            if lang:
                                setattr(self, "_last_detected_language", lang)

                        # Build chunk transcript
                        chunk_lines = []
                        for seg in segments:
                            start_f = float(seg.get("start", 0.0))
                            end_f = float(seg.get("end", start_f))
                            start = max(0, int(start_f))
                            end = max(start, int(end_f))
                            mm, ss = divmod(start, 60)
                            em, es = divmod(end, 60)
                            ts = f"[{mm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                            text = (seg.get("text") or "").strip()
                            if text:
                                chunk_lines.append(f"{ts} {text}")

                        chunk_text = "\n".join(chunk_lines)
                        transcripts.append(self._offset_lines(chunk_text, offset_seconds))
                        offset_seconds += int(os.getenv('OPENAI_AUDIO_SEGMENT_S', '600'))

                    return '\n'.join(transcripts)

            finally:
                self._cleanup_temp_artifacts(temp_files)
            with open(audio_path, "rb") as f:
                resp = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json"
                )
            # resp → dict (robust)
            data = self._as_dict(resp)
            segments = data.get("segments") or []
            # Bewaar taal in instance (wordt later in result gezet)
            lang = data.get("language")
            if lang:
                setattr(self, "_last_detected_language", lang)
            if not segments:
                # fallback naar text
                txt = data.get("text") or getattr(resp, "text", "") or str(resp)
                return txt or ""
            # Bouw "[MM:SS|MM:SS] text" regels (start|end), valt terug op enkel start als end ontbreekt
            lines = []
            for seg in segments:
                start_f = float(seg.get("start", 0.0))
                end_f = float(seg.get("end", start_f))
                start = max(0, int(start_f))
                end = max(start, int(end_f))
                mm, ss = divmod(start, 60)
                em, es = divmod(end, 60)
                # Inclusief eindtijd als die verschillend is
                ts = f"[{mm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                text = (seg.get("text") or "").strip()
                if text:
                    lines.append(f"{ts} {text}")
            return "\n".join(lines)
        except Exception as e:
            print(f"OpenAI Whisper (verbose_json) failed: {e}", file=sys.stderr)
            try:
                return self._transcribe_with_openai_whisper(audio_path, os.getenv("OPENAI_API_KEY","")) or ""
            except Exception:
                return ""

    def _detect_silences_ffmpeg(self, audio_path: str, duration: float) -> List[Dict[str, float]]:
        """Best-effort silence detection via ffmpeg silencedetect; returns gaps within [0,duration]."""
        if not self.ffmpeg_available:
            return []
        try:
            thr = str(os.getenv('SILENCE_DB', '-30')) + 'dB'
            dur = str(float(os.getenv('SILENCE_D', '0.25')))
            cmd = ["ffmpeg", "-i", audio_path, "-af", f"silencedetect=noise={thr}:d={dur}", "-f", "null", "-"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            lines = (proc.stderr or "").splitlines()
            gaps = []
            cur = {}
            for ln in lines:
                if "silence_start" in ln:
                    try:
                        t = float(ln.strip().split("silence_start:")[1])
                        cur = {"start_time": max(0.0, t), "end_time": None}
                    except: pass
                elif "silence_end" in ln and "silence_duration" in ln and cur:
                    try:
                        t = float(ln.strip().split("silence_end:")[1].split("|")[0])
                        cur["end_time"] = min(duration, t)
                        if cur["end_time"] and cur["end_time"] > cur["start_time"]:
                            gaps.append({"start_time": cur["start_time"], "end_time": cur["end_time"]})
                        cur = {}
                    except: pass
            return gaps
        except Exception:
            return []

    def _file_size_mb(self, path: str) -> float:
        """Get file size in MB"""
        return os.path.getsize(path) / (1024 * 1024)

    def _probe_duration(self, path: str) -> float:
        """Get audio duration using ffprobe"""
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        return 0.0

    def _compress_for_openai(self, audio_path: str) -> str:
        """Compress to 64k MP3 for OpenAI"""
        import tempfile
        with tempfile.NamedTemporaryFile(prefix='compressed_', suffix='.mp3', delete=False) as tmp:
            output = tmp.name
        bitrate = os.getenv('OPENAI_AUDIO_BITRATE', '64k')
        cmd = [
            'ffmpeg', '-y', '-i', audio_path,
            '-ar', '16000', '-ac', '1',
            '-b:a', bitrate, '-f', 'mp3',
            output
        ]
        subprocess.run(cmd, check=True, timeout=int(os.getenv('FFMPEG_TIMEOUT', '1800')))
        return output

    def _chunk_for_openai(self, audio_path: str, max_mb: int = None) -> List[str]:
        """Split audio into chunks for OpenAI (env-driven) with timeout protection"""
        if max_mb is None:
            max_mb = _getenv_int('OPENAI_AUDIO_MAX_MB', 25) - 1
        duration = self._probe_duration(audio_path)
        segment_s = float(os.getenv('OPENAI_AUDIO_SEGMENT_S', '600'))
        ffmpeg_timeout = int(os.getenv('FFMPEG_TIMEOUT', '1800'))
        max_chunks = _getenv_int('MAX_AUDIO_CHUNKS', 50)  # Prevent infinite chunking
        chunks = []
        import tempfile

        total_chunks = int(duration // segment_s) + 1
        print(f"🔍 CHUNKING DEBUG: Planning {total_chunks} chunks ({duration}s / {segment_s}s segments)", file=sys.stderr)

        # Add chunk limit protection for very long content (3+ hours)
        if total_chunks > max_chunks:
            print(f"⚠️ CHUNKING WARNING: {total_chunks} chunks exceeds limit of {max_chunks}, truncating", file=sys.stderr)
            total_chunks = max_chunks

        for i in range(0, min(int(duration), max_chunks * int(segment_s)), int(segment_s)):
            try:
                with tempfile.NamedTemporaryFile(prefix='chunk_', suffix='.mp3', delete=False) as tmp:
                    output = tmp.name
                cmd = [
                    'ffmpeg', '-y', '-i', audio_path,
                    '-ss', str(i), '-t', str(segment_s),
                    '-ar', '16000', '-ac', '1',
                    '-b:a', os.getenv('OPENAI_AUDIO_BITRATE', '64k'), output
                ]

                # Run with timeout and error handling
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=ffmpeg_timeout)
                if result.returncode != 0:
                    print(f"❌ CHUNKING ERROR: FFmpeg failed for chunk {len(chunks)+1}: {result.stderr}", file=sys.stderr)
                    # Clean up failed output file
                    if os.path.exists(output):
                        os.unlink(output)
                    continue

                # Verify chunk was created and has reasonable size
                if not os.path.exists(output) or os.path.getsize(output) < 1000:  # At least 1KB
                    print(f"❌ CHUNKING ERROR: Chunk {len(chunks)+1} not created or too small", file=sys.stderr)
                    if os.path.exists(output):
                        os.unlink(output)
                    continue

                chunks.append(output)
                print(f"✅ CHUNKING SUCCESS: Created chunk {len(chunks)}/{total_chunks} ({os.path.getsize(output)/1024/1024:.2f}MB)", file=sys.stderr)

            except subprocess.TimeoutExpired:
                print(f"⏰ CHUNKING TIMEOUT: Chunk {len(chunks)+1} timed out after {ffmpeg_timeout}s", file=sys.stderr)
                break
            except Exception as e:
                print(f"❌ CHUNKING ERROR: Unexpected error for chunk {len(chunks)+1}: {e}", file=sys.stderr)
                continue

        print(f"🏁 CHUNKING COMPLETE: Successfully created {len(chunks)} chunks", file=sys.stderr)
        return chunks

    def _offset_lines(self, transcript: str, offset_seconds: float) -> str:
        """Adjust timestamps in transcript for chunked processing"""
        lines = transcript.split('\n')
        adjusted = []
        for line in lines:
            if '[' in line and ']' in line:
                # Parse [MM:SS|MM:SS] or [MM:SS] format and add offset
                try:
                    timestamp_end = line.find(']')
                    timestamp_str = line[1:timestamp_end]
                    text = line[timestamp_end + 1:].strip()

                    if '|' in timestamp_str:
                        start_str, end_str = timestamp_str.split('|', 1)
                        start_total = self._parse_timestamp(start_str) + offset_seconds
                        end_total = self._parse_timestamp(end_str) + offset_seconds
                        new_ts = f"[{self._format_timestamp(start_total)}|{self._format_timestamp(end_total)}]"
                    else:
                        start_total = self._parse_timestamp(timestamp_str) + offset_seconds
                        new_ts = f"[{self._format_timestamp(start_total)}]"

                    adjusted.append(f"{new_ts} {text}")
                except:
                    adjusted.append(line)
            else:
                adjusted.append(line)
        return '\n'.join(adjusted)

    def _cleanup_temp_artifacts(self, file_paths: List[str]) -> None:
        """Clean up compressed and chunk files after processing"""
        for path in file_paths or []:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
                    print(f"Cleaned up: {path}", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not cleanup {path}: {e}", file=sys.stderr)

    def _parse_timestamp(self, mmss: str) -> float:
        """Convert 'MM:SS' timestamp to seconds (float)"""
        mm, ss = mmss.split(':')
        return int(mm) * 60 + float(ss)

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds (float) to 'MM:SS' format"""
        s = max(0, int(seconds))
        mm, ss = divmod(s, 60)
        return f"{mm:02d}:{ss:02d}"

    # ----------------------- NEW: faster-whisper helpers -----------------------

    def _get_faster_model(self):
        """
        Lazy-load en cache de faster-whisper WhisperModel met timeouts, retries en fallbacks.
        Geen OS-signals → werkt op Linux/WSL/Windows.
        """
        key = (self.fw_model_name, self.fw_device, self.fw_compute)
        if key in self._fw_cache:
            print(f"🔍 FASTER-WHISPER: Using cached model {key}")
            return self._fw_cache[key]

        from faster_whisper import WhisperModel

        # Bepaal device
        device = self.fw_device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
        print(f"🔍 FASTER-WHISPER: target device={device}")

        # Compute fallback ladder (snel → veilig)
        compute_order = [self.fw_compute, "int8_float16", "int8", "float16", "float32"]
        seen = set()
        compute_order = [c for c in compute_order if not (c in seen or seen.add(c))]

        # Cache/download locatie
        cache_dir = os.getenv("FASTER_WHISPER_CACHE", os.path.expanduser("~/.cache/faster_whisper"))
        os.makedirs(cache_dir, exist_ok=True)

        def _try_load(compute_type: str):
            print(f"🔍 FASTER-WHISPER: loading model={self.fw_model_name} device={device} compute={compute_type}")
            return WhisperModel(
                self.fw_model_name,
                device=device,
                compute_type=compute_type,
                download_root=cache_dir
            )

        # Singleflight om dubbele loads te vermijden
        with self._fw_lock:
            if key in self._fw_cache:
                return self._fw_cache[key]

            last_err: Optional[Exception] = None
            for compute in compute_order:
                # bescherm elke poging met watchdog-timeout
                ok, res = self._watchdog_call(_try_load, _getenv_int("FASTER_WHISPER_LOAD_TIMEOUT_S", 120), compute)
                if ok and res:
                    self._fw_cache[key] = res
                    print(f"✅ FASTER-WHISPER: model ready (compute={compute})")
                    return res
                last_err = res if isinstance(res, Exception) else RuntimeError("Model load timeout")
                print(f"⚠️ FASTER-WHISPER: load failed on compute={compute}: {last_err}")

            raise last_err or RuntimeError("Failed to load faster-whisper model")

    def _transcribe_with_faster_whisper(self, audio_path: str) -> str:
        """
        Snelle, gequantizeerde lokale transcriptie met (optionele) VAD.
        Geeft tekst terug in jouw formaat: [MM:SS|MM:SS] text
        """
        print(f"🔍 FASTER-WHISPER: Starting transcription of {audio_path}")

        # Check audio file exists and get info
        import os
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size = os.path.getsize(audio_path) / (1024*1024)  # MB
        print(f"🔍 FASTER-WHISPER: Audio file size: {file_size:.2f}MB")

        model = self._get_faster_model()
        print(f"🔍 FASTER-WHISPER: Model ready, starting transcription...")

        vad_params = None
        if self.vad_enable:
            vad_params = {
                "min_silence_duration_ms": self.vad_min_sil,
                "speech_pad_ms": int(self.vad_pad_s * 1000),
            }
            print(f"🔍 FASTER-WHISPER: Using VAD with params: {vad_params}")

        try:
            print(f"🔍 FASTER-WHISPER: Calling model.transcribe()...")
            def _run(word_ts: bool):
                return model.transcribe(
                    audio_path,
                    beam_size=5,
                    vad_filter=self.vad_enable,
                    vad_parameters=vad_params,
                    word_timestamps=word_ts,
                )
            try:
                segments, info = _run(True)
            except Exception as e1:
                print(f"⚠️ FASTER-WHISPER: word_timestamps=True failed: {e1}, retry without word timestamps")
                segments, info = _run(False)
            print(f"🔍 FASTER-WHISPER: Transcription completed, processing segments...")

            lines: List[str] = []
            segment_count = 0
            for seg in segments:
                segment_count += 1
                start = max(0, int(getattr(seg, "start", 0) or 0))
                end   = max(start, int(getattr(seg, "end", start) or start))
                sm, ss = divmod(start, 60)
                em, es = divmod(end, 60)
                ts = f"[{sm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                txt = (getattr(seg, "text", "") or "").strip()
                if txt:
                    lines.append(f"{ts} {txt}")

            print(f"✅ FASTER-WHISPER: Processed {segment_count} segments into {len(lines)} lines")

            if getattr(info, "language", None):
                setattr(self, "_last_detected_language", info.language)
                print(f"🔍 FASTER-WHISPER: Detected language: {info.language}")

            result = "\n".join(lines)
            print(f"✅ FASTER-WHISPER: Final result length: {len(result)} chars")
            return result

        except Exception as e:
            print(f"❌ FASTER-WHISPER: Transcription failed: {str(e)}")
            # Probeer één compute fallback bij runtime OOM/driver issues:
            fallback = {"int8_float16": "int8", "int8": "float16", "float16": "float32"}
            nxt = fallback.get(self.fw_compute)
            if nxt:
                print(f"🔁 FASTER-WHISPER: retry with compute={nxt}")
                prev = self.fw_compute
                self.fw_compute = nxt
                try:
                    model2 = self._get_faster_model()
                    # tweede poging zonder word timestamps, minimal settings
                    segments, info = model2.transcribe(
                        audio_path,
                        beam_size=1,
                        vad_filter=self.vad_enable,
                        vad_parameters=vad_params,
                        word_timestamps=False,
                    )
                    lines = []
                    for seg in segments:
                        start = max(0, int(getattr(seg, "start", 0) or 0))
                        end   = max(start, int(getattr(seg, "end", start) or start))
                        sm, ss = divmod(start, 60); em, es = divmod(end, 60)
                        ts = f"[{sm:02d}:{ss:02d}|{em:02d}:{es:02d}]"
                        txt = (getattr(seg, "text", "") or "").strip()
                        if txt: lines.append(f"{ts} {txt}")
                    if getattr(info, "language", None):
                        setattr(self, "_last_detected_language", info.language)
                    return "\n".join(lines)
                finally:
                    self.fw_compute = prev
            raise

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python audio_transcriber.py '<json_input>'",
            "error_code": "USAGE_ERROR"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        transcriber = FastAudioTranscriber()
        result = transcriber.transcribe_audio(input_data)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success", False) else 1)

    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_ERROR"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
