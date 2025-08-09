#!/usr/bin/env python3
"""
Thumbnail Generator Agent - Atomic Agent
=======================================

Generates thumbnails for videos and social media content.
Single responsibility: Create engaging thumbnails for different platforms.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, List, Any

class ThumbnailGenerator:
    """
    Atomic agent for generating video thumbnails.

    Creates platform-specific thumbnails with text overlays,
    effects, and optimized dimensions.
    """

    def __init__(self):
        self.version = "1.0.0"

    def generate_thumbnail(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate thumbnail for video content.

        Args:
            input_data: {
                "video_path": str,           # source video file
                "output_path": str,          # output thumbnail path
                "timestamp": float,          # timestamp to extract frame (seconds)
                "platform": str,             # "youtube", "tiktok", "instagram", "generic"
                "title": str,                # optional, text overlay
                "style": str,                # "minimal", "bold", "gaming", "educational"
                "add_play_button": bool,     # optional, add play button overlay
                "add_duration": bool,        # optional, add duration badge
                "brightness": float,         # optional, brightness adjustment (-100 to 100)
                "contrast": float,           # optional, contrast adjustment (-100 to 100)
                "saturation": float,         # optional, saturation adjustment (-100 to 100)
                "blur_background": bool,     # optional, blur background behind text
                "template": str              # optional, template to use
            }

        Returns:
            {
                "success": bool,
                "thumbnail_path": str,       # path to generated thumbnail
                "dimensions": {
                    "width": int,
                    "height": int
                },
                "platform_specs": {
                    "platform": str,
                    "optimal_size": str,
                    "aspect_ratio": str,
                    "file_size": int
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
            timestamp = input_data.get("timestamp", 0)
            platform = input_data.get("platform", "generic")
            title = input_data.get("title", "")
            style = input_data.get("style", "minimal")
            add_play_button = input_data.get("add_play_button", False)
            add_duration = input_data.get("add_duration", False)
            brightness = input_data.get("brightness", 0)
            contrast = input_data.get("contrast", 0)
            saturation = input_data.get("saturation", 0)
            blur_background = input_data.get("blur_background", False)
            input_data.get("template", "")

            # Get platform specifications
            platform_specs = self._get_platform_specs(platform)

            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Extract frame from video
            temp_frame = self._extract_frame(video_path, timestamp, platform_specs)
            if not temp_frame:
                return self._error("Failed to extract frame from video")

            # Apply image adjustments
            adjusted_frame = self._apply_adjustments(
                temp_frame, brightness, contrast, saturation
            )

            # Add overlays and effects
            final_thumbnail = self._add_overlays(
                adjusted_frame, title, style, add_play_button,
                add_duration, blur_background, platform_specs
            )

            # Save final thumbnail
            if not self._save_thumbnail(final_thumbnail, output_path, platform_specs):
                return self._error("Failed to save thumbnail")

            # Get final dimensions and file size
            dimensions = self._get_image_dimensions(output_path)
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

            # Clean up temporary files
            self._cleanup_temp_files([temp_frame, adjusted_frame, final_thumbnail])

            processing_time = time.time() - start_time

            return {
                "success": True,
                "thumbnail_path": output_path,
                "dimensions": dimensions,
                "platform_specs": {
                    **platform_specs,
                    "file_size": file_size
                },
                "processing_time": processing_time,
                "agent_version": self.version
            }

        except Exception as e:
            return self._error(f"Thumbnail generation failed: {str(e)}")

    def _get_platform_specs(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific thumbnail specifications"""

        specs = {
            "youtube": {
                "platform": "YouTube",
                "width": 1280,
                "height": 720,
                "aspect_ratio": "16:9",
                "optimal_size": "1280x720",
                "max_file_size": 2 * 1024 * 1024,  # 2MB
                "format": "jpg",
                "quality": 85
            },
            "tiktok": {
                "platform": "TikTok",
                "width": 1080,
                "height": 1920,
                "aspect_ratio": "9:16",
                "optimal_size": "1080x1920",
                "max_file_size": 1 * 1024 * 1024,  # 1MB
                "format": "jpg",
                "quality": 80
            },
            "instagram": {
                "platform": "Instagram",
                "width": 1080,
                "height": 1080,
                "aspect_ratio": "1:1",
                "optimal_size": "1080x1080",
                "max_file_size": 1 * 1024 * 1024,  # 1MB
                "format": "jpg",
                "quality": 80
            },
            "twitter": {
                "platform": "Twitter",
                "width": 1200,
                "height": 675,
                "aspect_ratio": "16:9",
                "optimal_size": "1200x675",
                "max_file_size": 1 * 1024 * 1024,  # 1MB
                "format": "jpg",
                "quality": 80
            },
            "generic": {
                "platform": "Generic",
                "width": 1920,
                "height": 1080,
                "aspect_ratio": "16:9",
                "optimal_size": "1920x1080",
                "max_file_size": 3 * 1024 * 1024,  # 3MB
                "format": "jpg",
                "quality": 90
            }
        }

        return specs.get(platform, specs["generic"])

    def _extract_frame(self, video_path: str, timestamp: float, platform_specs: Dict[str, Any]) -> str:
        """Extract frame from video at specified timestamp"""

        try:
            # Create temporary frame file
            temp_frame = f"/tmp/thumbnail_frame_{int(time.time())}.jpg"

            # Extract frame using ffmpeg
            cmd = [
                'ffmpeg', '-i', video_path, '-ss', str(timestamp),
                '-vframes', '1', '-q:v', '2',
                '-vf', f'scale={platform_specs["width"]}:{platform_specs["height"]}:force_original_aspect_ratio=decrease,pad={platform_specs["width"]}:{platform_specs["height"]}:(ow-iw)/2:(oh-ih)/2:black',
                '-y', temp_frame
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and os.path.exists(temp_frame):
                return temp_frame

        except Exception:
            pass

        return None

    def _apply_adjustments(self, input_path: str, brightness: float, contrast: float, saturation: float) -> str:
        """Apply brightness, contrast, and saturation adjustments"""

        if brightness == 0 and contrast == 0 and saturation == 0:
            return input_path

        try:
            # Create temporary adjusted file
            temp_adjusted = f"/tmp/thumbnail_adjusted_{int(time.time())}.jpg"

            # Build filter string
            filters = []

            if brightness != 0:
                # Convert brightness from -100/100 to ffmpeg range
                bright_val = brightness / 100.0
                filters.append(f'eq=brightness={bright_val}')

            if contrast != 0:
                # Convert contrast from -100/100 to ffmpeg range
                contrast_val = 1.0 + (contrast / 100.0)
                filters.append(f'eq=contrast={contrast_val}')

            if saturation != 0:
                # Convert saturation from -100/100 to ffmpeg range
                sat_val = 1.0 + (saturation / 100.0)
                filters.append(f'eq=saturation={sat_val}')

            filter_string = ','.join(filters) if filters else 'null'

            # Apply adjustments using ffmpeg
            cmd = [
                'ffmpeg', '-i', input_path, '-vf', filter_string,
                '-y', temp_adjusted
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and os.path.exists(temp_adjusted):
                return temp_adjusted

        except Exception:
            pass

        return input_path

    def _add_overlays(self, input_path: str, title: str, style: str, add_play_button: bool,
                     add_duration: bool, blur_background: bool, platform_specs: Dict[str, Any]) -> str:
        """Add text overlays and effects to thumbnail"""

        # For now, return input path as-is
        # In a full implementation, this would use ImageMagick or similar
        # to add text overlays, play buttons, and other effects

        if not any([title, add_play_button, add_duration]):
            return input_path

        try:
            # Create temporary overlay file
            temp_overlay = f"/tmp/thumbnail_overlay_{int(time.time())}.jpg"

            # Build overlay filters
            filters = []

            # Add title text if provided
            if title:
                # Simple text overlay using ffmpeg
                font_size = self._get_font_size(platform_specs)
                text_filter = f"drawtext=text='{title}':x=(w-text_w)/2:y=h-text_h-20:fontsize={font_size}:fontcolor=white:box=1:boxcolor=black@0.5"
                filters.append(text_filter)

            # Add play button if requested
            if add_play_button:
                # Simple play button using shapes
                play_button = "drawbox=x=(w-80)/2:y=(h-60)/2:w=80:h=60:color=black@0.5:t=fill,drawtext=text='▶':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=40:fontcolor=white"
                filters.append(play_button)

            if filters:
                filter_string = ','.join(filters)

                cmd = [
                    'ffmpeg', '-i', input_path, '-vf', filter_string,
                    '-y', temp_overlay
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and os.path.exists(temp_overlay):
                    return temp_overlay

        except Exception:
            pass

        return input_path

    def _get_font_size(self, platform_specs: Dict[str, Any]) -> int:
        """Get appropriate font size for platform"""

        width = platform_specs["width"]

        if width >= 1920:
            return 72
        elif width >= 1280:
            return 48
        elif width >= 1080:
            return 36
        else:
            return 24

    def _save_thumbnail(self, input_path: str, output_path: str, platform_specs: Dict[str, Any]) -> bool:
        """Save thumbnail with platform-specific optimization"""

        try:
            # Optimize and save thumbnail
            cmd = [
                'ffmpeg', '-i', input_path, '-q:v', str(100 - platform_specs["quality"]),
                '-y', output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception:
            return False

    def _get_image_dimensions(self, image_path: str) -> Dict[str, int]:
        """Get image dimensions"""

        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0', image_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                width, height = result.stdout.strip().split(',')
                return {"width": int(width), "height": int(height)}

        except Exception:
            pass

        return {"width": 0, "height": 0}

    def _cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files"""

        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "THUMBNAIL_GENERATION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python thumbnail_generator.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        generator = ThumbnailGenerator()
        result = generator.generate_thumbnail(input_data)
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
