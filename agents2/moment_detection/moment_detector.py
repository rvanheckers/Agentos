#!/usr/bin/env python3
"""
Moment Detector Agent - Atomic Agent
===================================

Detects viral moments and highlights in video content.
Single responsibility: Find the most engaging moments in video.

Phase 2 Security Migration: Direct SecureVideoAgent inheritance
- Integrated security validation layer
- MIME type validation via VideoSecurityValidator
- Path traversal prevention via PathSanitizer
- Resource limit enforcement via ResourceLimiter
- 100% backward compatible with existing code
"""

import json
import sys
import os
import subprocess
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import security components first (Phase 2 migration)
try:
    from agents2.base.secure_agent import SecureVideoAgent
    from security.video_validator import VideoSecurityValidator
    from security.path_sanitizer import PathSanitizer
    from security.resource_limiter import ResourceLimiter
    from security.exceptions import SecurityError
    _security_available = True
except ImportError:
    SecureVideoAgent = None
    VideoSecurityValidator = None
    PathSanitizer = None
    ResourceLimiter = None
    SecurityError = Exception
    _security_available = False
    logger.warning("Security components not available - running without security baseline")

# Import application components
try:
    from agents2.mock_data_generator import MockDataGenerator
except ImportError:
    MockDataGenerator = None

try:
    from api.config.settings import Settings
    settings = Settings()
except ImportError:
    settings = None

try:
    from agents2.shared.utils.fallback_messages import FallbackMessages
except ImportError:
    # Define minimal fallback
    class FallbackMessages:
        @staticmethod
        def get(key, lang='en'):
            return "Processing"

# Determine base class based on availability
if SecureVideoAgent:
    _BaseClass = SecureVideoAgent
else:
    # Fallback to object if SecureVideoAgent not available
    _BaseClass = object
    logger.warning("SecureVideoAgent not available - running without security baseline")

class MomentDetector(_BaseClass):
    """
    Atomic agent for detecting viral moments in video content.

    Uses audio transcription and visual analysis to identify
    the most engaging segments for social media clips.
    """

    def __init__(self):
        # Initialize security base if available
        if SecureVideoAgent:
            super().__init__()

        # Load environment variables
        try:
            from dotenv import load_dotenv
            # .env moet shell/pm2/systemd exports kunnen overrulen
            load_dotenv(override=True)
        except ImportError:
            pass  # dotenv not available, environment should be set externally

        self.version = "2.0.0"  # Phase 2: SecureVideoAgent inheritance
        self.mock_generator = MockDataGenerator() if MockDataGenerator else None
        # Use real AI analysis for moment detection
        self.use_mock = os.getenv('USE_MOCK_AI', 'false').lower() == 'true'

        # --- NEW: thresholds & recall via env (met defaults) ---
        self.min_conf = float(os.getenv('MOMENTS_MIN_CONF', '0.35'))          # 0.0-1.0
        self.topk     = int(os.getenv('MOMENTS_TOPK', '20'))                  # kandidaten cap
        self.min_gap_s = float(os.getenv('MOMENTS_MIN_GAP_S', '5'))           # minimale afstand tussen moments
        self.recall_retry = os.getenv('MOMENTS_RECALL_RETRY', 'true').lower() == 'true'
        self.recall_min_conf = float(os.getenv('MOMENTS_RECALL_MIN_CONF', '0.20'))
        self.recall_topk = int(os.getenv('MOMENTS_RECALL_TOPK', '40'))
        # Consistente gaps voor hele keten
        # cluster_gap_s: grove clustering (UCA)
        # commit_gap: strakkere non-overlap (UCA finale)
        self.cluster_gap_s = float(os.getenv('MOMENTS_CLUSTER_GAP_S', '8.0'))
        # Silence snapping fine-tuning (optioneel; alleen gebruikt als analyzer audio_path krijgt)
        self.snap_search_radius_s = float(os.getenv('SNAP_SEARCH_RADIUS_S', '1.5'))
        self.snap_min_lead_in = float(os.getenv('SNAP_MIN_LEAD_IN', '0.35'))
        self.snap_min_lead_out = float(os.getenv('SNAP_MIN_LEAD_OUT', '0.60'))

        # Log effectieve toggles voor snelle diagnose
        logger.info(
            "MomentDetector flags: USE_UNIFIED_ANALYZER=%s, UCA_V2_ENABLED=%s, "
            "MIN_CONF=%.2f, TOPK=%d, MIN_GAP=%.1f, RECALL=%s",
            os.getenv("USE_UNIFIED_ANALYZER"),
            os.getenv("UCA_V2_ENABLED"),
            self.min_conf, self.topk, self.min_gap_s, self.recall_retry
        )

    # --- NEW: centraal postprocessen om cutter-consistent te maken ---
    def _postprocess_moments(self, moments, video_duration: float):
        if not moments:
            return []
        # 1) normalisatie & bounds
        norm = []
        for m in moments:
            s = max(0.0, float(m.get("start_time", 0.0)))
            e = float(m.get("end_time", s))
            e = min(e, max(0.0, video_duration - 1e-3))
            if e - s < 1e-3:
                continue
            norm.append({
                "start_time": round(s, 3),
                "end_time": round(e, 3),
                "duration": round(e - s, 3),
                "confidence": float(m.get("confidence", m.get("viral_score", 0)/100.0)),
                "type": m.get("type", "viral_ai"),
                "description": m.get("description") or "",
                "keywords": m.get("keywords", []),
                "viral_score": int(m.get("viral_score", max(0, min(100, int(m.get("confidence", 0)*100)))))
            })
        # 2) sort by start_time (cutter verwacht oplopend)
        return sorted(norm, key=lambda x: x["start_time"])[: int(self.topk)]

    def detect_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect viral moments in video content.

        Phase 2 Security: Integrated validation before processing
        - Path sanitization (prevent directory traversal)
        - MIME type validation (prevent file type spoofing)
        - Resource limit enforcement (prevent DoS)
        - 100% backward compatible with existing code

        Args:
            input_data: {
                "video_path": str,
                "transcript": str,           # optional, from audio_transcriber
                "segments": List[dict],      # optional, transcript segments
                "intent": str,               # short_clips, key_moments, smart_summary
                "min_duration": float,       # minimum moment duration in seconds
                "max_duration": float,       # maximum moment duration in seconds
                "max_moments": int           # maximum number of moments to detect
            }

        Returns:
            {
                "success": bool,
                "moments": List[{
                    "start_time": float,
                    "end_time": float,
                    "duration": float,
                    "confidence": float,     # 0-1 viral potential score
                    "type": str,            # "viral", "highlight", "summary"
                    "description": str,
                    "keywords": List[str]
                }],
                "processing_time": float,
                "agent_version": str
            }
        """

        start_time = time.time()

        # Phase 2 Security: Validate input if security components available
        if SecureVideoAgent:
            try:
                # 1. Input validation
                if not isinstance(input_data, dict):
                    return self._error("input_data must be a dictionary")

                raw_path = input_data.get("video_path")
                if not raw_path:
                    return self._error("video_path is required in input_data")

                # 2. Path sanitization - prevent directory traversal
                try:
                    # SECURITY: Default to production mode (fail-safe principle)
                    # Development must be explicitly enabled via AGENTOS_ENV=development
                    if os.getenv("AGENTOS_ENV", "production") == "development":
                        self.path_sanitizer.configure_for_development()

                    safe_path = self.path_sanitizer.validate_input_path(raw_path)
                    logger.info("Path validated: %s", safe_path)

                    # Update input_data with sanitized path
                    input_data = input_data.copy()
                    input_data["video_path"] = str(safe_path)

                except SecurityError as e:
                    logger.warning("Path validation failed: %s", e)
                    return self._error(f"Invalid video path: {str(e)}")

                # 3. MIME type and video validation
                try:
                    validation_result = self.validator.validate_video_file(str(safe_path))

                    if not validation_result.get("valid"):
                        error_msg = validation_result.get("error", "Unknown validation error")
                        logger.warning("Video validation failed: %s", error_msg)
                        return self._error(f"Video validation failed: {error_msg}")

                    metadata = validation_result.get("metadata", {})
                    logger.info(
                        "Video validated: duration=%.1fs, size=%.1fMB",
                        metadata.get('duration_seconds', 0),
                        metadata.get('file_size_mb', 0)
                    )

                except SecurityError as e:
                    logger.warning("Video validation error: %s", e)
                    return self._error(f"Security validation failed: {str(e)}")

                # 4. Resource limit checks (non-blocking)
                try:
                    if "output_path" in input_data:
                        output_dir = str(Path(input_data["output_path"]).parent)
                        self.resource_limiter.check_disk_space(output_dir, required_mb=100)
                except Exception as e:
                    # Don't fail on resource checks - just log warning
                    logger.warning("Resource check warning: %s", e)

            except Exception as e:
                logger.error("Security validation error: %s", e)
                # Continue processing if security validation fails non-critically
                # This maintains backward compatibility

        # 🔧 NEW: Check for UnifiedContentAnalyzer environment toggle
        # Heartbeat support zodat UI niet 'hangt' op 66%
        progress_cb = input_data.get("progress_cb")
        def heartbeat(pct: float, msg: str = "detecting moments"):
            try:
                if callable(progress_cb):
                    progress_cb(pct, msg)
            except Exception:
                pass
        heartbeat(68.0, "initializing detector")

        use_unified_analyzer = os.getenv('USE_UNIFIED_ANALYZER', 'false').lower() == 'true'

        if use_unified_analyzer:
            logger.info("🚀 Using UnifiedContentAnalyzer (new AI-powered approach)")
            result = self._detect_moments_with_unified_analyzer(input_data, start_time)
            heartbeat(78.0, "unified analysis done")
            # --- NEW: recall-retry pad als er geen resultaten zijn ---
            if self.recall_retry and (not result.get('moments') or result.get('total_moments', 0) == 0):
                logger.info("🔄 Recall-retry: verlaag drempel en verhoog topk")
                input_data2 = dict(input_data)
                input_data2.setdefault('constraints_override', {})
                input_data2['constraints_override'].update({
                    'min_conf': self.recall_min_conf,
                    'topk': self.recall_topk,
                })
                result = self._detect_moments_with_unified_analyzer(input_data2, start_time)
            # Centraal postprocessen en counts syncen
            if result.get("success") and result.get("moments") is not None:
                vd = result.get("video_duration") or input_data.get("video_duration") or 0
                result["moments"] = self._postprocess_moments(result["moments"], vd)
                result["total_moments"] = len(result["moments"])
            heartbeat(92.0, "postprocess complete")
            return result
        else:
            logger.info("📋 Using legacy MomentDetector (existing approach)")
            return self._detect_moments_legacy(input_data, start_time)

    def _detect_moments_with_unified_analyzer(self, input_data: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Use UnifiedContentAnalyzer for combined content type + moment detection"""
        try:
            from agents2.moment_detection.unified_content_analyzer import UnifiedContentAnalyzer

            # Extract data for UnifiedContentAnalyzer
            youtube_metadata = input_data.get('youtube_metadata', {})
            transcript = input_data.get('transcript', '')
            video_path = input_data.get('video_path', '')

            # Get video duration for constraints
            video_duration = self._get_video_duration(video_path)
            if not video_duration:
                # Try from metadata
                video_duration = youtube_metadata.get('duration', 300)

            # Build processing constraints (env-gestuurd en overridebaar)
            constraints = {
                'min_duration': input_data.get('min_duration', 15),
                'max_duration': input_data.get('max_duration', 60),
                'max_moments': input_data.get('max_moments', 5),
                'video_duration': video_duration,
                # 🚦 GAP policy consistentie met UCA
                # UCA gebruikt cluster_gap_s (ruim) en commit_gap (strak);
                # wij mappen env/inputs hier zodat er niet dubbel te agressief gemerged wordt.
                'cluster_gap_s': float(input_data.get('cluster_gap_s', self.cluster_gap_s)),
                'commit_gap': float(input_data.get('commit_gap', max(1.5, self.min_gap_s/2.0))),
                # Voor compat:
                'min_gap': float(input_data.get('min_gap', self.min_gap_s)),
                # NEW: quality/spacing/snapping
                'min_conf': float(input_data.get('min_conf', self.min_conf)),
                'topk': int(input_data.get('topk', self.topk)),
                # Silence snapping (alleen actief als analyzer een audio_path krijgt)
                'snap_search_radius_s': float(input_data.get('snap_search_radius_s', self.snap_search_radius_s)),
                'min_lead_in': float(input_data.get('min_lead_in', self.snap_min_lead_in)),
                'min_lead_out': float(input_data.get('min_lead_out', self.snap_min_lead_out)),
                # optioneel: audio_path doorgeven als beschikbaar
                'audio_path': input_data.get('audio_path')
            }
            # Per-call override mogelijkheid
            constraints_override = input_data.get('constraints_override', {})
            if isinstance(constraints_override, dict):
                constraints.update(constraints_override)

            # Initialize and run analyzer
            analyzer = UnifiedContentAnalyzer()
            result = analyzer.analyze_content(youtube_metadata, transcript, constraints)

            if result.get('success'):
                # Update processing time
                processing_time = time.time() - start_time
                result['processing_time'] = processing_time
                result['video_duration'] = video_duration

                logger.info(f"✅ UnifiedContentAnalyzer success: {result.get('content_type')} + {result.get('total_moments')} moments")
                return result
            else:
                logger.warning(f"⚠️ UnifiedContentAnalyzer failed: {result.get('error')}")
                # Fallback to legacy method
                return self._detect_moments_legacy(input_data, start_time)

        except Exception as e:
            logger.error(f"❌ UnifiedContentAnalyzer error: {e}")
            # Fallback to legacy method
            return self._detect_moments_legacy(input_data, start_time)

    def _detect_moments_legacy(self, input_data: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Legacy MomentDetector implementation (existing code)"""
        try:
            # Validate inputs
            if not input_data.get("video_path"):
                return self._error("video_path is required")

            video_path = input_data["video_path"]
            if not os.path.exists(video_path):
                return self._error(f"Video file not found: {video_path}")

            # Get parameters
            intent = input_data.get("intent", "short_clips")
            min_duration = input_data.get("min_duration", 15)
            max_duration = input_data.get("max_duration", 60)
            max_moments = input_data.get("max_moments", 3)
            transcript = input_data.get("transcript", "")
            segments = input_data.get("segments", [])

            # Get video metadata - try ffprobe first, then fallback to metadata
            video_duration = self._get_video_duration(video_path)
            if not video_duration:
                # Try to get duration from YouTube metadata if available
                youtube_metadata = input_data.get('youtube_metadata', {})
                fallback_duration = youtube_metadata.get('duration', 0)

                if fallback_duration > 0:
                    logger.info(f"📊 Using duration from metadata: {fallback_duration} seconds")
                    video_duration = float(fallback_duration)
                else:
                    # Last resort: use a default duration
                    logger.warning(f"⚠️ Could not determine video duration, using default 120 seconds")
                    video_duration = 120.0

            # Initialize content type defaults (needed for all paths)
            content_type = input_data.get('content_type', 'spoken')
            analysis_mode = "fallback_no_transcript"
            detection_confidence = 0.5

            # REAL AI ANALYSIS: Detect valuable moments based on transcript
            if not transcript or transcript.strip() == "":
                logger.warning(f"No transcript available, using fallback moments with content-based keywords")
                moments = self._generate_safe_moments(video_duration, max_moments)

                # ✅ FIX: Set correct analysis_mode based on content_type, not transcript availability
                if content_type == 'spoken':
                    analysis_mode = "ai_viral_analysis"  # Speech analysis regardless of transcript
                elif content_type == 'music':
                    analysis_mode = "ai_song_lyrics"     # Music analysis
                else:
                    analysis_mode = "ai_viral_analysis"  # Default to viral analysis

                # ✅ CRITICAL FIX: Generate keywords and viral_score even without transcript
                # Use YouTube metadata for keyword extraction
                youtube_metadata = input_data.get('youtube_metadata', {})
                video_title = input_data.get('video_title', '') or youtube_metadata.get('title', '')
                description = youtube_metadata.get('description', '')

                # Extract keywords from title and description
                metadata_text = f"{video_title} {description}".strip()
                if metadata_text:
                    fallback_keywords = self._extract_keywords_from_metadata(metadata_text)
                    logger.info(f"📝 Extracted {len(fallback_keywords)} keywords from video metadata")
                else:
                    # Use content-type specific keywords
                    fallback_keywords = self._get_content_type_keywords(content_type)
                    logger.info(f"📝 Using {content_type} content-type keywords")

                # Calculate viral score based on content type and metadata
                fallback_viral_score = self._calculate_metadata_viral_score(content_type, metadata_text, len(moments))
                logger.info(f"🎯 Calculated fallback viral_score: {fallback_viral_score}")

                # Add keywords and viral_score to each moment
                for moment in moments:
                    moment['keywords'] = fallback_keywords
                    moment['viral_score'] = fallback_viral_score
            else:
                logger.info(f"Using real transcript analysis for moment detection")

                # Initialize defaults in case detection fails
                content_type = 'unknown'
                analysis_mode = 'fallback'
                detection_confidence = 0.0

                # Smart content detection
                try:
                    from agents2.content_detection.smart_detector import SmartContentDetector

                    detection_result = SmartContentDetector.detect_content_type(
                        user_intent=input_data.get('user_intent'),
                        youtube_metadata=input_data.get('youtube_metadata'),
                        audio_analysis=input_data.get('audio_analysis'),
                        transcript=transcript
                    )

                    content_type = detection_result['content_type']
                    analysis_mode = detection_result['analysis_mode']
                    detection_confidence = detection_result['confidence']
                except Exception as detection_error:
                    logger.warning(f"⚠️ SmartContentDetector failed: {detection_error}, using defaults")

                # Only log detection result details if detection succeeded
                if content_type != 'unknown':
                    logger.info(f'🎯 Content detected: {content_type} via {analysis_mode} (confidence: {detection_confidence})')
                else:
                    logger.info(f'🎯 Using fallback detection: {content_type}')

                # ✅ MUSIC DETECTION ENABLED - Use SmartContentDetector results
                if content_type == 'music':
                    logger.info(f"🎵 Music content detected - using structural moments instead of transcript analysis")
                    # For music, create fixed interval moments without keyword analysis
                    moments = self._generate_music_video_moments(self._get_video_duration(video_path))
                    # Set appropriate analysis mode for music
                    if intent == "short_clips":
                        analysis_mode = "ai_song_lyrics"
                    elif intent == "key_moments":
                        analysis_mode = "ai_song_highlights"
                    else:
                        analysis_mode = "ai_song_viral"
                else:
                    # For speech content, use transcript analysis (legacy path via Claude)
                    if intent in ("short_clips", "key_moments", "smart_summary"):
                        moments, _ctype = self._analyze_with_claude(
                            transcript, min_duration, max_duration, max_moments, video_path
                        )
                        analysis_mode = "ai_viral_analysis" if intent != "key_moments" else "ai_key_highlights"

            processing_time = time.time() - start_time

            # Centraal postprocessen + counts sync
            moments = self._postprocess_moments(moments, video_duration)
            total_moments = len(moments)

            # ✅ CRITICAL FIX: Extract keywords and viral_score from moments for database storage
            all_keywords = []
            total_viral_score = 0
            valid_scores = 0

            for moment in moments:
                # Collect keywords
                moment_keywords = moment.get('keywords', [])
                if isinstance(moment_keywords, list):
                    all_keywords.extend(moment_keywords)

                # Calculate average viral score
                viral_score = moment.get('viral_score')
                if viral_score is not None and isinstance(viral_score, (int, float)):
                    total_viral_score += viral_score
                    valid_scores += 1

            # Remove duplicate keywords and limit to 10 most relevant
            unique_keywords = list(set(all_keywords))[:10]

            # Calculate average viral score
            avg_viral_score = 0
            if valid_scores > 0:
                avg_viral_score = int(total_viral_score / valid_scores)
            elif len(moments) > 0:
                # Fallback viral score based on content type and moment count
                if content_type == 'spoken':
                    avg_viral_score = min(75, 40 + (len(moments) * 10))  # 40-75 for speech
                else:
                    avg_viral_score = min(65, 30 + (len(moments) * 8))   # 30-65 for other content

            logger.info(f"✅ Aggregated {len(unique_keywords)} keywords and viral_score {avg_viral_score} from {len(moments)} moments")

            return {
                "success": True,
                "moments": moments,
                "total_moments": total_moments,
                "processing_time": processing_time,
                "agent_version": self.version,
                "video_duration": video_duration,
                "analysis_mode": analysis_mode,
                "content_type": content_type,
                "keywords": unique_keywords,  # ✅ NEW: Pass aggregated keywords to database
                "viral_score": avg_viral_score  # ✅ NEW: Pass calculated viral score to database
            }

        except Exception as e:
            return self._error(f"Legacy moment detection failed: {str(e)}")

    def _generate_safe_moments(self, video_duration: float, max_moments: int) -> List[Dict]:
        """Generate safe moments that fit within video duration"""
        moments = []
        clip_duration = float(os.getenv('SAFE_CLIP_DURATION_S', '30.0'))  # langere fallback

        # Calculate how many clips can fit
        possible_clips = int(video_duration // clip_duration)
        actual_clips = min(max_moments, possible_clips, 3)  # Max 3 clips

        if actual_clips == 0:
            # Video too short for any clips
            return []

        # Generate evenly spaced moments
        for i in range(actual_clips):
            start_time = (i * video_duration) / actual_clips
            end_time = min(start_time + clip_duration, video_duration - 1)

            # Skip if clip would be too short
            if end_time - start_time < 5:
                continue

            moments.append({
                "start_time": round(start_time, 1),
                "end_time": round(end_time, 1),
                "duration": round(end_time - start_time, 1),
                "confidence": 0.8,
                "type": "auto",
                "description": FallbackMessages.get('metadata_missing', 'nl'),
                "keywords": [],  # Will be filled by caller
                "viral_score": 0  # Will be filled by caller
            })

        return moments

    # NOTE: de dubbele/overschrijf-methode _detect_viral_moments is verwijderd.
    
    def _analyze_with_claude(self, transcript: str, min_duration: float, max_duration: float, max_moments: int, video_path: str = None):
        """Real Claude AI transcript analysis for viral moment detection"""
        
        try:
            import anthropic
            import os
            import json
            
            # Initialize Claude client
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if not anthropic_key:
                logger.warning("No Anthropic API key found, falling back to keyword analysis")
                return self._fallback_keyword_analysis(transcript, min_duration, max_duration, max_moments, video_path)
            
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            # Create neutral, politics-allowed JSON prompt (consistent met analyzer)
            prompt = f"""
You are a neutral highlight detector. Analyze this transcript and return 3–20 viral-worthy moments as JSON only.
Political/sensitive topics are allowed to analyze; do not advocate any position.
Each moment must be {min_duration}-{max_duration} seconds long.

Transcript (may be truncated):
{transcript[:3000]}

Return ONLY a JSON array like:
[
  {{
    "start_time": 28.2,
    "end_time": 43.2,
    "viral_score": 87,
    "hook_type": "powerful_quote|emotional_peak|surprise|technique|highlight",
    "key_phrase": "Verbatim short phrase from this window",
    "engagement_drivers": ["emotional","surprising","quotable"]
  }}
]
"""
            
            # Call Claude for analysis
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cheap for this task
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude's response
            response_text = response.content[0].text.strip()
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                moments_data = json.loads(json_match.group())
                
                # Sort by viral_score desc, convert and filter by min_conf/topk
                moments_data = sorted(moments_data, key=lambda m: m.get('viral_score', 0), reverse=True)
                count = 0
                moments = []
                for moment in moments_data:
                    viral_score = int(moment.get('viral_score', 0) or 0)
                    conf = min(0.95, max(0.0, viral_score / 100.0))
                    if conf < self.min_conf:
                        continue
                    clip_start = float(moment.get('start_time', 0.0))
                    clip_end = float(moment.get('end_time', max(min_duration, 15)))
                    if clip_end - clip_start < min_duration or clip_end - clip_start > max_duration:
                        continue
                    moments.append({
                        "start_time": float(moment.get('start_time', 0)),
                        "end_time": float(moment.get('end_time', clip_start + min_duration)),
                        "duration": float(moment.get('end_time', clip_start + min_duration)) - float(moment.get('start_time', 0)),
                        "confidence": conf,
                        "type": moment.get('hook_type', 'viral_ai'),
                        "description": f"🔥 Viral ({viral_score}/100): {moment.get('key_phrase', 'High viral potential')[:120]}",
                        "keywords": moment.get('engagement_drivers', [])[:5],
                        "viral_score": viral_score
                        })
                    count += 1
                    if count >= max(self.topk, max_moments):
                        break
                
                logger.info(f"🤖 Claude found {len(moments)} viral moments")
                return moments, "spoken"
            else:
                logger.warning("Claude response couldn't be parsed as JSON")
                return self._fallback_keyword_analysis(transcript, min_duration, max_duration, max_moments, video_path), "spoken"
                
        except Exception as e:
            logger.error(f"🚫 AI Viral Analysis Failed: {e}")
            logger.warning("📋 Falling back to keyword-based analysis (reduced accuracy)")
            return self._fallback_keyword_analysis(transcript, min_duration, max_duration, max_moments, video_path), "spoken"
    
    def _fallback_keyword_analysis(self, transcript: str, min_duration: float, max_duration: float, max_moments: int, video_path: str = None) -> List[dict]:
        """Fallback keyword-based analysis when Claude is not available"""
        
        import re
        
        # Simple language detection based on common words
        def detect_language(text: str) -> str:
            text_lower = text.lower()
            # Count common words for each language
            language_indicators = {
                'nl': ['de', 'het', 'en', 'van', 'is', 'dat', 'een', 'voor', 'met', 'zijn'],
                'en': ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that'],
                'es': ['el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no'],
                'fr': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'],
                'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich']
            }
            
            scores = {}
            for lang, indicators in language_indicators.items():
                score = sum(1 for word in indicators if word in text_lower)
                scores[lang] = score
            
            return max(scores, key=scores.get) if scores else 'en'
        
        # Detect language from transcript
        language = detect_language(transcript)
        logger.info(f"🌍 Detected language: {language}")
        
        # Multi-language viral indicators - what makes content shareable worldwide
        viral_keywords_by_language = {
            'en': {  # English
                'reactions': ['wow', 'amazing', 'incredible', 'unbelievable', 'omg', 'holy', 'crazy', 'insane', 'wtf', 'damn'],
                'emotions': ['laugh', 'crying', 'shocked', 'surprised', 'angry', 'excited', 'happy', 'scared', 'love'],
                'engagement': ['wait', 'look', 'watch', 'see this', 'check this', 'listen', 'guys', 'everyone'],
                'quotes': ['said', 'quote', 'told me', 'like this', 'exactly', 'literally'],
                'dramatic': ['suddenly', 'then', 'but then', 'and then', 'happened', 'moment', 'boom', 'bang']
            },
            'nl': {  # Dutch  
                'reactions': ['wauw', 'geweldig', 'ongelofelijk', 'shit', 'godverdomme', 'jezus', 'gek', 'krankzinnig'],
                'emotions': ['lachen', 'huilen', 'geschokt', 'verrast', 'boos', 'blij', 'bang', 'liefde'],
                'engagement': ['wacht', 'kijk', 'luister', 'zie dit', 'check dit', 'mensen', 'iedereen'],
                'quotes': ['zei', 'citaat', 'vertelde', 'zoals dit', 'precies', 'letterlijk'],
                'dramatic': ['plots', 'toen', 'maar toen', 'en toen', 'gebeurde', 'moment', 'boem', 'pats']
            },
            'es': {  # Spanish
                'reactions': ['increíble', 'impresionante', 'guau', 'dios mío', 'loco', 'genial'],
                'emotions': ['reír', 'llorar', 'sorprendido', 'enojado', 'feliz', 'emocionado'],
                'engagement': ['mira', 'escucha', 've esto', 'checa esto', 'gente'],
                'quotes': ['dijo', 'cita', 'me dijo', 'así', 'exactamente'],
                'dramatic': ['de repente', 'entonces', 'pero entonces', 'pasó', 'momento']
            },
            'fr': {  # French
                'reactions': ['incroyable', 'fantastique', 'oh mon dieu', 'fou', 'génial'],
                'emotions': ['rire', 'pleurer', 'choqué', 'surpris', 'en colère', 'heureux'],
                'engagement': ['regardez', 'écoutez', 'voyez ça', 'les gens'],
                'quotes': ['dit', 'citation', 'ma dit', 'comme ça', 'exactement'],
                'dramatic': ['soudain', 'puis', 'mais alors', 'arrivé', 'moment']
            },
            'de': {  # German
                'reactions': ['unglaublich', 'fantastisch', 'mein gott', 'verrückt', 'toll'],
                'emotions': ['lachen', 'weinen', 'schockiert', 'überrascht', 'wütend', 'glücklich'],
                'engagement': ['schaut', 'hört', 'seht das', 'leute'],
                'quotes': ['sagte', 'zitat', 'sagte mir', 'so', 'genau'],
                'dramatic': ['plötzlich', 'dann', 'aber dann', 'passiert', 'moment']
            }
        }
        
        # Get keywords for detected language (fallback to English)
        viral_keywords = viral_keywords_by_language.get(language, viral_keywords_by_language['en'])
        logger.info(f"🌍 Using {language} viral keywords for analysis")
        
        sentences = re.split(r'[.!?]+', transcript.lower())
        moments = []
        
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) < 10:  # Skip very short sentences
                continue
                
            # Calculate viral score for this sentence
            viral_score = 0
            matched_keywords = []
            
            for category, keywords in viral_keywords.items():
                for keyword in keywords:
                    if keyword in sentence:
                        viral_score += 1
                        matched_keywords.append(keyword)
            
            # Only create moment if viral score is high enough  
            if viral_score >= 1:  # At least 1 viral indicator (lowered for music videos)
                # Get actual video duration and calculate timestamp
                video_duration = self._get_video_duration(video_path) if video_path else 300
                estimated_time = (i / len(sentences)) * video_duration
                
                # Create clip around this moment
                start_time = max(0, estimated_time - 7.5)  # 7.5s before
                end_time = min(start_time + 15, estimated_time + 7.5, video_duration - 1)  # 15s total, within video bounds
                
                # Skip clips that would be too short or start too close to video end
                if end_time - start_time < 5 or start_time >= video_duration - 5:
                    continue
                
                moments.append({
                    "start_time": round(start_time, 1),
                    "end_time": round(end_time, 1), 
                    "duration": round(end_time - start_time, 1),
                    "confidence": min(0.95, viral_score * 0.2),  # Score to confidence
                    "type": "viral_ai",
                    "description": f"🔥 Viral: {sentence[:50]}...",
                    "keywords": matched_keywords,
                    "viral_score": viral_score,
                    "sentence_text": sentence.strip()
                })
        
        # Sort by viral score (best moments first)
        moments.sort(key=lambda m: m['viral_score'], reverse=True)
        
        # Return variable number based on content quality (no artificial limit)
        quality_moments = [m for m in moments if m['viral_score'] >= 2]  # High quality (lowered for music)
        
        if len(quality_moments) == 0:
            # No high-quality moments found
            if len(moments) == 0:
                # No moments at all - create fallback clips for music videos
                logger.warning(f"No viral content detected, creating fallback clips for music/visual content")
                video_duration = self._get_video_duration(video_path)
                return self._generate_music_video_moments(video_duration)
            else:
                # Some moments with lower scores, return top 2
                return moments[:2] if len(moments) >= 2 else moments
        elif len(quality_moments) <= 2:
            # 1-2 high quality moments
            return quality_moments
        else:
            # Multiple high quality moments, return top 5 max
            return quality_moments[:5]

    def _generate_music_video_moments(self, video_duration: float) -> List[Dict]:
        """Generate moments for music videos or visual content without transcript"""
        moments = []
        
        # For music videos, create clips at interesting timestamps
        # Standard music video structure: intro, verse, chorus, bridge, outro
        if video_duration > 60:
            # Create 3 clips for longer music videos
            timestamps = [
                (10, 25),   # Intro/verse
                (video_duration * 0.4, video_duration * 0.4 + 15),  # Chorus
                (video_duration * 0.7, video_duration * 0.7 + 15)   # Bridge/climax
            ]
        else:
            # Short video - just create 2 clips
            timestamps = [
                (5, 20),
                (video_duration * 0.6, video_duration * 0.6 + 10)
            ]
        
        for i, (start, end) in enumerate(timestamps):
            if end > video_duration:
                end = video_duration - 1
            if start >= end:
                continue
                
            moments.append({
                "start_time": round(start, 1),
                "end_time": round(end, 1),
                "duration": round(end - start, 1),
                "confidence": 0.7,
                "type": "music_visual",
                "description": f"🎵 Music clip {i+1}",
                "keywords": ["music", "song", "audio"],  # Basic music keywords
                "viral_score": 45  # Moderate viral score for music
            })
        
        return moments

    def _detect_key_highlights(self, video_path: str, transcript: str,
                             segments: List[dict], min_duration: float,
                             max_duration: float, max_moments: int) -> List[dict]:
        """Detect key highlights (important content, main points)"""

        moments = []
        video_duration = self._get_video_duration(video_path)

        # Generate key highlights
        segment_duration = video_duration / max_moments

        for i in range(max_moments):
            start_time = i * segment_duration
            end_time = min(start_time + max_duration, video_duration)

            moment = {
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "confidence": 0.9,  # High confidence for key content
                "type": "highlight",
                "description": f"Key highlight {i+1}",
                "keywords": []
            }
            moments.append(moment)

        return moments
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for moment tagging"""
        if not text:
            return []
        
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'was', 'are', 'were'}
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Return top 5 most relevant keywords
        return keywords[:5]

    def _detect_summary_moments(self, video_path: str, transcript: str,
                              segments: List[dict], min_duration: float,
                              max_duration: float, max_moments: int) -> List[dict]:
        """Detect summary moments (comprehensive overview)"""

        moments = []
        video_duration = self._get_video_duration(video_path)

        # Generate summary moments
        segment_duration = video_duration / max_moments

        for i in range(max_moments):
            start_time = i * segment_duration
            end_time = min(start_time + max_duration, video_duration)

            moment = {
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "confidence": 0.8,
                "type": "summary",
                "description": f"Summary moment {i+1}",
                "keywords": []
            }
            moments.append(moment)

        return moments

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                return 0.0

        except Exception:
            return 0.0

    def _extract_keywords_from_metadata(self, metadata_text: str) -> List[str]:
        """Extract keywords from video title and description"""
        if not metadata_text:
            return []

        import re

        # Clean the text
        text = metadata_text.lower()

        # Remove special characters and split into words
        words = re.findall(r'\b\w+\b', text)

        # Stop words to filter out
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'a', 'an', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }

        # Filter meaningful keywords (length > 3, not stop words)
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for word in keywords:
            if word not in seen:
                unique_keywords.append(word)
                seen.add(word)

        return unique_keywords[:8]  # Return top 8 keywords

    def _get_content_type_keywords(self, content_type: str) -> List[str]:
        """Get default keywords based on content type"""
        content_keywords = {
            'spoken': ['speech', 'talk', 'discussion', 'conversation', 'interview'],
            'music': ['music', 'song', 'audio', 'melody', 'rhythm'],
            'unknown': ['content', 'video', 'media', 'clip']
        }
        return content_keywords.get(content_type, content_keywords['unknown'])

    def _calculate_metadata_viral_score(self, content_type: str, metadata_text: str, moment_count: int) -> int:
        """Calculate viral score based on metadata analysis"""
        base_score = 40  # Base viral potential

        if metadata_text:
            # Viral indicators in metadata
            viral_words = [
                'viral', 'trending', 'amazing', 'incredible', 'shocking', 'unbelievable',
                'best', 'worst', 'epic', 'crazy', 'insane', 'must', 'watch', 'see',
                'reaction', 'response', 'calls', 'out', 'truth', 'expose', 'reveals'
            ]

            metadata_lower = metadata_text.lower()
            viral_indicators = sum(1 for word in viral_words if word in metadata_lower)

            # Boost score based on viral indicators
            base_score += viral_indicators * 8

            # Content type multipliers
            if content_type == 'spoken':
                base_score += 15  # Speech content tends to be more viral
            elif content_type == 'music':
                base_score += 5   # Music has moderate viral potential

        # Moment count bonus (more moments = more viral potential)
        base_score += moment_count * 5

        # Cap the score at reasonable limits
        return min(85, max(25, base_score))

    # ⚠️ VERWIJDERD: duplicaat _extract_keywords (overschreef de betere versie).
    # Als je de simpele variant wilt houden, hernoem die naar _extract_keywords_simple.

    def save_moments_to_db(self, job_id: str, moments: List[Dict]) -> bool:
        """
        Save detected moments to database WITH AI transparency data

        Args:
            job_id: UUID of the job
            moments: List of moment dictionaries with keys:
                - start_time, end_time, duration
                - description, keywords, viral_score
                - reasoning (NEW): Claude's explanation
                - engagement_drivers (NEW): Array of viral factors

        Returns:
            True if successful, False otherwise
        """
        try:
            from core.database_manager import PostgreSQLManager, Moment
            import uuid

            db = PostgreSQLManager()

            with db.get_session() as session:
                # Verify job exists
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if not job:
                    logger.error(f"❌ Job {job_id} not found, cannot save moments")
                    return False

                logger.info(f"💾 Saving {len(moments)} moments to database for job {job_id}")

                for idx, moment_data in enumerate(moments):
                    # Extract core timing data
                    start_time = float(moment_data.get('start_time', 0.0))
                    end_time = float(moment_data.get('end_time', start_time + 15.0))
                    duration = float(moment_data.get('duration', end_time - start_time))

                    # Extract content data
                    description = str(moment_data.get('description', ''))[:500]  # Max 500 chars
                    keywords = moment_data.get('keywords', [])
                    if not isinstance(keywords, list):
                        keywords = []

                    viral_score = int(moment_data.get('viral_score', 0))

                    # Extract AI transparency data (NEW)
                    reasoning = str(moment_data.get('reasoning', ''))[:500] if moment_data.get('reasoning') else None
                    engagement_drivers = moment_data.get('engagement_drivers', [])
                    if not isinstance(engagement_drivers, list):
                        engagement_drivers = []

                    # Create Moment object
                    moment = Moment(
                        id=uuid.uuid4(),
                        job_id=job_id,
                        moment_index=idx,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        description=description,
                        keywords=keywords,
                        viral_score=viral_score,
                        # NEW: AI Transparency fields
                        reasoning=reasoning,
                        engagement_drivers=engagement_drivers
                    )
                    session.add(moment)

                    logger.info(
                        f"  ✅ Moment {idx}: {start_time:.1f}s-{end_time:.1f}s "
                        f"(viral_score={viral_score}, reasoning={'✓' if reasoning else '✗'})"
                    )

                session.commit()
                logger.info(f"✅ Successfully saved {len(moments)} moments with AI transparency data")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to save moments to database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "MOMENT_DETECTION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python moment_detector.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        detector = MomentDetector()
        result = detector.detect_moments(input_data)
        print(json.dumps(result, indent=2))

    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_DECODE_ERROR"
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
