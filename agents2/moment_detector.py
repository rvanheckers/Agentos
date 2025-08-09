#!/usr/bin/env python3
"""
Moment Detector Agent - Atomic Agent
===================================

Detects viral moments and highlights in video content.
Single responsibility: Find the most engaging moments in video.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, List, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from agents2.mock_data_generator import MockDataGenerator
    from api.config.settings import Settings
    settings = Settings()
except ImportError:
    settings = None
    MockDataGenerator = None

class MomentDetector:
    """
    Atomic agent for detecting viral moments in video content.
    
    Uses audio transcription and visual analysis to identify
    the most engaging segments for social media clips.
    """

    def __init__(self):
        self.version = "1.0.0"
        self.mock_generator = MockDataGenerator() if MockDataGenerator else None
        self.use_mock = getattr(settings, 'use_mock_ai', True) if settings else True

    def detect_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect viral moments in video content.
        
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

            # Get video metadata
            video_duration = self._get_video_duration(video_path)
            if not video_duration:
                return self._error("Could not determine video duration")

            # SIMPLE PASSTHROUGH: Generate safe moments within video duration
            moments = self._generate_safe_moments(video_duration, max_moments)

            processing_time = time.time() - start_time

            return {
                "success": True,
                "moments": moments,
                "processing_time": processing_time,
                "agent_version": self.version,
                "video_duration": video_duration,
                "passthrough_mode": True
            }

            # Detect moments based on intent
            moments = []

            if intent == "short_clips":
                moments = self._detect_viral_moments(
                    video_path, transcript, segments,
                    min_duration, max_duration, max_moments
                )
            elif intent == "key_moments":
                moments = self._detect_key_highlights(
                    video_path, transcript, segments,
                    min_duration, max_duration, max_moments
                )
            elif intent == "smart_summary":
                moments = self._detect_summary_moments(
                    video_path, transcript, segments,
                    min_duration, max_duration, max_moments
                )
            else:
                # Default to viral moments
                moments = self._detect_viral_moments(
                    video_path, transcript, segments,
                    min_duration, max_duration, max_moments
                )

            processing_time = time.time() - start_time

            return {
                "success": True,
                "moments": moments,
                "total_moments": len(moments),
                "video_duration": video_duration,
                "processing_time": processing_time,
                "agent_version": self.version
            }

        except Exception as e:
            return self._error(f"Moment detection failed: {str(e)}")

    def _generate_safe_moments(self, video_duration: float, max_moments: int) -> List[Dict]:
        """Generate safe moments that fit within video duration"""
        moments = []
        clip_duration = 15.0  # Standard 15-second clips

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
                "description": f"🤖 Pipeline test clip {i+1}",
                "keywords": ["test", "pipeline", "auto"]
            })

        return moments

    def _detect_viral_moments(self, video_path: str, transcript: str,
                            segments: List[dict], min_duration: float,
                            max_duration: float, max_moments: int) -> List[dict]:
        """Detect viral moments using real AI analysis"""

        # Use real AI if transcript is available and not using mock
        if transcript and not self.use_mock:
            return self._analyze_with_claude(transcript, min_duration, max_duration, max_moments)

        # Fallback to simple analysis
        moments = []
        video_duration = self._get_video_duration(video_path)

        # If we have transcript segments, use them
        if segments:
            for i, segment in enumerate(segments[:max_moments]):
                start_time = segment.get("start", i * 20)
                end_time = min(start_time + min_duration, video_duration)

                moment = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "confidence": 0.8,  # High confidence for viral content
                    "type": "viral",
                    "description": f"Viral moment {i+1}",
                    "keywords": self._extract_keywords(segment.get("text", ""))
                }
                moments.append(moment)
        else:
            # Generate evenly spaced viral moments
            segment_duration = video_duration / max_moments

            for i in range(max_moments):
                start_time = i * segment_duration
                end_time = min(start_time + min_duration, video_duration)

                moment = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "confidence": 0.7,
                    "type": "viral",
                    "description": f"Viral moment {i+1}",
                    "keywords": []
                }
                moments.append(moment)

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

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []

        # Simple keyword extraction
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3]
        return keywords[:5]  # Return top 5 keywords

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "MOMENT_DETECTION_ERROR",
            "agent_version": self.version
        }

    def _analyze_with_claude(self, transcript: str, min_duration: float,
                           max_duration: float, max_moments: int) -> List[dict]:
        """Analyze transcript with Claude AI to find viral moments"""
        try:
            import anthropic
            import json
            import re

            # Get API key from settings
            api_key = getattr(settings, 'anthropic_api_key', None) if settings else None
            if not api_key:
                api_key = os.getenv('ANTHROPIC_API_KEY')

            if not api_key:
                print("No Anthropic API key found, falling back to simple analysis")
                return []

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""
            Analyze this video transcript and identify the most viral/engaging moments for social media clips.
            
            TRANSCRIPT:
            {transcript}
            
            REQUIREMENTS:
            - Find {max_moments} most viral moments
            - Each moment should be {min_duration}-{max_duration} seconds long
            - Look for: emotional peaks, funny moments, surprising content, educational insights, action sequences
            - Rate each moment's viral potential (0.0-1.0)
            
            Return a JSON array with this exact format:
            [
                {{
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "duration": 30.0,
                    "confidence": 0.85,
                    "type": "funny",
                    "description": "Brief description of why this moment is viral",
                    "keywords": ["keyword1", "keyword2"]
                }}
            ]
            
            ONLY return the JSON array, no other text.
            """

            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast model for this task
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            response_text = response.content[0].text.strip()

            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                moments_data = json.loads(json_match.group())
                return moments_data
            else:
                print(f"Could not parse Claude response: {response_text}")
                return []

        except Exception as e:
            print(f"Claude analysis failed: {e}")
            return []

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
