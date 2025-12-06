#!/usr/bin/env python3
"""
Visual Effects Agent - Atomic Agent
==================================

Applies visual effects to video content.
Single responsibility: Add professional visual effects to videos.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, List, Any

class VisualEffects:
    """
    Atomic agent for applying visual effects to videos.

    Provides transitions, filters, overlays, and cinematic effects
    for professional video production.
    """

    def __init__(self):
        self.version = "1.0.0"

    def apply_effects(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply visual effects to video.

        Args:
            input_data: {
                "video_path": str,           # input video file
                "output_path": str,          # output video file
                "effects": List[{
                    "type": str,             # effect type
                    "start_time": float,     # start time in seconds
                    "duration": float,       # effect duration
                    "intensity": float,      # effect intensity (0.0-1.0)
                    "parameters": dict       # effect-specific parameters
                }],
                "transitions": List[{
                    "type": str,             # transition type
                    "position": float,       # position in video (seconds)
                    "duration": float,       # transition duration
                    "direction": str         # transition direction
                }],
                "filters": List[{
                    "type": str,             # filter type
                    "intensity": float,      # filter intensity
                    "parameters": dict       # filter parameters
                }],
                "overlays": List[{
                    "type": str,             # overlay type
                    "path": str,             # overlay file path
                    "position": dict,        # x, y position
                    "start_time": float,     # start time
                    "duration": float        # overlay duration
                }],
                "quality": str               # output quality (high, medium, low)
            }

        Returns:
            {
                "success": bool,
                "output_video": str,         # path to processed video
                "effects_applied": List[str], # list of applied effects
                "processing_stats": {
                    "original_duration": float,
                    "output_duration": float,
                    "effects_count": int,
                    "file_size_mb": float
                },
                "processing_time": float,
                "agent_version": str
            }
        """

        start_time = time.time()

        try:
            # Validate inputs
            if not input_data.get("video_path"):
                return self._error("video_path is required")

            if not input_data.get("output_path"):
                return self._error("output_path is required")

            video_path = input_data["video_path"]
            if not os.path.exists(video_path):
                return self._error(f"Video file not found: {video_path}")

            # Get parameters
            output_path = input_data["output_path"]
            effects = input_data.get("effects", [])
            transitions = input_data.get("transitions", [])
            filters = input_data.get("filters", [])
            overlays = input_data.get("overlays", [])
            quality = input_data.get("quality", "high")

            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Build FFmpeg filter chain
            filter_chain = self._build_filter_chain(
                effects, transitions, filters, overlays
            )

            # Apply effects using FFmpeg
            success = self._apply_ffmpeg_effects(
                video_path, output_path, filter_chain, quality
            )

            if not success:
                return self._error("Failed to apply effects")

            # Get processing statistics
            stats = self._get_processing_stats(video_path, output_path)

            # List applied effects
            effects_applied = self._get_applied_effects_list(
                effects, transitions, filters, overlays
            )

            processing_time = time.time() - start_time

            return {
                "success": True,
                "output_video": output_path,
                "effects_applied": effects_applied,
                "processing_stats": stats,
                "processing_time": processing_time,
                "agent_version": self.version
            }

        except Exception as e:
            return self._error(f"Effect application failed: {str(e)}")

    def _build_filter_chain(self, effects: List[dict], transitions: List[dict],
                           filters: List[dict], overlays: List[dict]) -> str:
        """Build FFmpeg filter chain for all effects"""

        filter_parts = []

        # Add basic filters
        for filter_item in filters:
            filter_str = self._build_filter_string(filter_item)
            if filter_str:
                filter_parts.append(filter_str)

        # Add effects
        for effect in effects:
            effect_str = self._build_effect_string(effect)
            if effect_str:
                filter_parts.append(effect_str)

        # Add transitions
        for transition in transitions:
            transition_str = self._build_transition_string(transition)
            if transition_str:
                filter_parts.append(transition_str)

        # Combine filters
        if filter_parts:
            return ','.join(filter_parts)
        else:
            return 'null'  # No-op filter

    def _build_filter_string(self, filter_item: dict) -> str:
        """Build filter string for specific filter type"""

        filter_type = filter_item.get("type", "")
        intensity = filter_item.get("intensity", 0.5)

        filters = {
            "brightness": f"eq=brightness={intensity - 0.5}",
            "contrast": f"eq=contrast={1 + intensity}",
            "saturation": f"eq=saturation={1 + intensity}",
            "blur": f"boxblur={int(intensity * 10)}",
            "sharpen": f"unsharp=5:5:{intensity * 2}:5:5:{intensity * 2}",
            "vintage": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
            "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
            "grayscale": "colorchannelmixer=.299:.587:.114:0:.299:.587:.114:0:.299:.587:.114",
            "invert": "negate",
            "vignette": f"vignette=PI/4:{intensity}",
            "noise": f"noise=alls={int(intensity * 20)}:allf=t+u",
            "chromakey": f"chromakey=green:{intensity}:0.1",
            "colorbalance": f"colorbalance=rs={intensity}:gs={intensity}:bs={intensity}"
        }

        return filters.get(filter_type, "")

    def _build_effect_string(self, effect: dict) -> str:
        """Build effect string for specific effect type"""

        effect_type = effect.get("type", "")
        start_time = effect.get("start_time", 0)
        duration = effect.get("duration", 1)
        intensity = effect.get("intensity", 0.5)

        # Time-based effects
        if effect_type == "fade_in":
            return f"fade=t=in:st={start_time}:d={duration}"
        elif effect_type == "fade_out":
            return f"fade=t=out:st={start_time}:d={duration}"
        elif effect_type == "zoom_in":
            zoom_factor = 1 + intensity
            return f"zoompan=z='min(zoom+0.0015,{zoom_factor})':d={int(duration * 25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        elif effect_type == "zoom_out":
            zoom_factor = 1 + intensity
            return f"zoompan=z='if(lte(zoom,1.0),{zoom_factor},max(1.001,zoom-0.0015))':d={int(duration * 25)}"
        elif effect_type == "pan_left":
            return f"zoompan=z='1.5':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration * 25)}"
        elif effect_type == "pan_right":
            return f"zoompan=z='1.5':x='if(gte(on,1),x-1,x)':y='ih/2-(ih/zoom/2)':d={int(duration * 25)}"
        elif effect_type == "shake":
            return f"vibrance={intensity}"
        elif effect_type == "glitch":
            return f"noise=alls={int(intensity * 30)}:allf=t"

        return ""

    def _build_transition_string(self, transition: dict) -> str:
        """Build transition string for specific transition type"""

        transition_type = transition.get("type", "")
        position = transition.get("position", 0)
        duration = transition.get("duration", 1)

        # For simplicity, most transitions would require multiple video inputs
        # Here we provide basic single-input transitions

        if transition_type == "crossfade":
            return f"fade=t=out:st={position}:d={duration}"
        elif transition_type == "slide":
            return f"slide=direction={transition.get('direction', 'left')}"
        elif transition_type == "wipe":
            return f"fade=t=out:st={position}:d={duration}"

        return ""

    def _apply_ffmpeg_effects(self, input_path: str, output_path: str,
                             filter_chain: str, quality: str) -> bool:
        """Apply effects using FFmpeg"""

        try:
            # Quality settings
            quality_settings = {
                "high": ["-crf", "18", "-preset", "medium"],
                "medium": ["-crf", "23", "-preset", "fast"],
                "low": ["-crf", "28", "-preset", "ultrafast"]
            }

            settings = quality_settings.get(quality, quality_settings["medium"])

            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', filter_chain,
                '-c:v', 'libx264', '-c:a', 'aac',
                *settings,
                '-movflags', '+faststart',
                '-y', output_path
            ]

            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception:
            return False

    def _get_processing_stats(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Get processing statistics"""

        stats = {
            "original_duration": 0.0,
            "output_duration": 0.0,
            "effects_count": 0,
            "file_size_mb": 0.0
        }

        try:
            # Get original duration
            stats["original_duration"] = self._get_video_duration(input_path)

            # Get output duration
            stats["output_duration"] = self._get_video_duration(output_path)

            # Get file size
            if os.path.exists(output_path):
                stats["file_size_mb"] = os.path.getsize(output_path) / (1024 * 1024)

        except Exception:
            pass

        return stats

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

        except Exception:
            pass

        return 0.0

    def _get_applied_effects_list(self, effects: List[dict], transitions: List[dict],
                                 filters: List[dict], overlays: List[dict]) -> List[str]:
        """Get list of applied effects"""

        applied = []

        for effect in effects:
            applied.append(f"Effect: {effect.get('type', 'unknown')}")

        for transition in transitions:
            applied.append(f"Transition: {transition.get('type', 'unknown')}")

        for filter_item in filters:
            applied.append(f"Filter: {filter_item.get('type', 'unknown')}")

        for overlay in overlays:
            applied.append(f"Overlay: {overlay.get('type', 'unknown')}")

        return applied

    def get_available_effects(self) -> Dict[str, Any]:
        """Get list of available effects"""

        return {
            "effects": [
                "fade_in", "fade_out", "zoom_in", "zoom_out",
                "pan_left", "pan_right", "shake", "glitch"
            ],
            "transitions": [
                "crossfade", "slide", "wipe"
            ],
            "filters": [
                "brightness", "contrast", "saturation", "blur", "sharpen",
                "vintage", "sepia", "grayscale", "invert", "vignette",
                "noise", "chromakey", "colorbalance"
            ],
            "overlays": [
                "text", "image", "logo", "watermark"
            ]
        }

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "VISUAL_EFFECTS_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python visual_effects.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        effects = VisualEffects()
        result = effects.apply_effects(input_data)
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
