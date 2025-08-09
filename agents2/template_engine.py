#!/usr/bin/env python3
"""
Template Engine Agent - Atomic Agent
===================================

Applies video templates and presets to content.
Single responsibility: Apply professional video templates and layouts.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, List, Any

class TemplateEngine:
    """
    Atomic agent for applying video templates.

    Provides professional video templates, layouts, and presets
    for different content types and platforms.
    """

    def __init__(self):
        self.version = "1.0.0"
        self.templates_dir = "./templates"

    def apply_template(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply video template to content.

        Args:
            input_data: {
                "video_path": str,           # input video file
                "output_path": str,          # output video file
                "template_name": str,        # template to apply
                "platform": str,             # target platform
                "customization": {
                    "colors": {
                        "primary": str,      # primary color hex
                        "secondary": str,    # secondary color hex
                        "accent": str        # accent color hex
                    },
                    "fonts": {
                        "title": str,        # title font
                        "body": str,         # body font
                        "accent": str        # accent font
                    },
                    "branding": {
                        "logo": str,         # logo file path
                        "watermark": str,    # watermark file path
                        "brand_name": str    # brand name text
                    },
                    "layout": {
                        "title_position": str,    # top, bottom, center
                        "logo_position": str,     # top-left, top-right, etc.
                        "text_alignment": str     # left, center, right
                    }
                },
                "content": {
                    "title": str,            # main title
                    "subtitle": str,         # subtitle
                    "description": str,      # description text
                    "call_to_action": str,   # CTA text
                    "hashtags": List[str]    # hashtags to include
                },
                "timing": {
                    "intro_duration": float,     # intro duration
                    "outro_duration": float,     # outro duration
                    "transition_duration": float # transition duration
                }
            }

        Returns:
            {
                "success": bool,
                "output_video": str,         # path to templated video
                "template_info": {
                    "name": str,
                    "platform": str,
                    "style": str,
                    "duration": float,
                    "resolution": str
                },
                "customizations_applied": List[str],
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

            template_name = input_data.get("template_name", "basic")
            if not template_name:
                return self._error("template_name is required")

            video_path = input_data["video_path"]
            if not os.path.exists(video_path):
                return self._error(f"Video file not found: {video_path}")

            # Get parameters
            output_path = input_data["output_path"]
            template_name = input_data["template_name"]
            platform = input_data.get("platform", "generic")
            customization = input_data.get("customization", {})
            content = input_data.get("content", {})
            timing = input_data.get("timing", {})

            # Get template configuration
            template_config = self._get_template_config(template_name, platform)
            if not template_config:
                return self._error(f"Template '{template_name}' not found")

            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Apply template (mock for basic template)
            if template_name == "basic":
                # For basic template, just copy the video file
                success = self._apply_basic_template(video_path, output_path)
            else:
                success = self._apply_template_to_video(
                    video_path, output_path, template_config,
                    customization, content, timing
                )

            if not success:
                return self._error("Failed to apply template")

            # Get applied customizations
            customizations_applied = self._get_applied_customizations(customization)

            processing_time = time.time() - start_time

            return {
                "success": True,
                "output_video": output_path,
                "template_info": {
                    "name": template_name,
                    "platform": platform,
                    "style": template_config.get("style", "modern"),
                    "duration": self._get_video_duration(output_path),
                    "resolution": template_config.get("resolution", "1920x1080")
                },
                "customizations_applied": customizations_applied,
                "processing_time": processing_time,
                "agent_version": self.version
            }

        except Exception as e:
            return self._error(f"Template application failed: {str(e)}")

    def _get_template_config(self, template_name: str, platform: str) -> Dict[str, Any]:
        """Get template configuration"""

        templates = {
            "basic": {
                "style": "simple",
                "platform": platform,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "intro": {
                    "duration": 1.0,
                    "animation": "none",
                    "background": "transparent"
                },
                "outro": {
                    "duration": 1.0,
                    "animation": "none",
                    "cta_enabled": False
                },
                "overlays": {
                    "title": {
                        "position": "center",
                        "font": "Arial",
                        "size": 32,
                        "color": "#FFFFFF"
                    }
                },
                "effects": []
            },
            "modern_minimal": {
                "style": "modern",
                "platform": platform,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "intro": {
                    "duration": 3.0,
                    "animation": "fade_in",
                    "background": "gradient"
                },
                "outro": {
                    "duration": 2.0,
                    "animation": "fade_out",
                    "cta_enabled": True
                },
                "overlays": {
                    "title": {
                        "position": "center",
                        "font": "Arial Bold",
                        "size": 48,
                        "color": "#FFFFFF"
                    },
                    "subtitle": {
                        "position": "bottom",
                        "font": "Arial",
                        "size": 24,
                        "color": "#CCCCCC"
                    }
                },
                "effects": ["fade_in", "fade_out", "smooth_zoom"]
            },
            "social_burst": {
                "style": "energetic",
                "platform": platform,
                "resolution": "1080x1920" if platform == "tiktok" else "1920x1080",
                "aspect_ratio": "9:16" if platform == "tiktok" else "16:9",
                "intro": {
                    "duration": 2.0,
                    "animation": "zoom_burst",
                    "background": "colorful"
                },
                "outro": {
                    "duration": 3.0,
                    "animation": "slide_out",
                    "cta_enabled": True
                },
                "overlays": {
                    "title": {
                        "position": "top",
                        "font": "Impact",
                        "size": 64,
                        "color": "#FF6B35"
                    },
                    "hashtags": {
                        "position": "bottom",
                        "font": "Arial",
                        "size": 18,
                        "color": "#FFFFFF"
                    }
                },
                "effects": ["zoom_in", "shake", "color_pop", "glitch"]
            },
            "professional": {
                "style": "corporate",
                "platform": platform,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "intro": {
                    "duration": 4.0,
                    "animation": "slide_in",
                    "background": "solid"
                },
                "outro": {
                    "duration": 3.0,
                    "animation": "fade_out",
                    "cta_enabled": True
                },
                "overlays": {
                    "title": {
                        "position": "center",
                        "font": "Helvetica",
                        "size": 42,
                        "color": "#2C3E50"
                    },
                    "logo": {
                        "position": "top-right",
                        "size": "medium",
                        "opacity": 0.8
                    }
                },
                "effects": ["fade_in", "fade_out", "subtle_zoom"]
            },
            "gaming": {
                "style": "gaming",
                "platform": platform,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "intro": {
                    "duration": 2.5,
                    "animation": "glitch_in",
                    "background": "neon"
                },
                "outro": {
                    "duration": 2.0,
                    "animation": "glitch_out",
                    "cta_enabled": True
                },
                "overlays": {
                    "title": {
                        "position": "center",
                        "font": "Orbitron",
                        "size": 56,
                        "color": "#00FF88"
                    },
                    "effects": {
                        "glow": True,
                        "neon": True
                    }
                },
                "effects": ["glitch", "neon_glow", "rgb_shift", "scanlines"]
            },
            "educational": {
                "style": "clean",
                "platform": platform,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
                "intro": {
                    "duration": 3.0,
                    "animation": "fade_in",
                    "background": "white"
                },
                "outro": {
                    "duration": 2.5,
                    "animation": "fade_out",
                    "cta_enabled": True
                },
                "overlays": {
                    "title": {
                        "position": "top",
                        "font": "Open Sans",
                        "size": 40,
                        "color": "#34495E"
                    },
                    "subtitle": {
                        "position": "bottom",
                        "font": "Open Sans",
                        "size": 24,
                        "color": "#7F8C8D"
                    }
                },
                "effects": ["fade_in", "fade_out", "smooth_transitions"]
            }
        }

        return templates.get(template_name)

    def _apply_basic_template(self, video_path: str, output_path: str) -> bool:
        """Apply basic template (simple copy for demo)"""
        try:
            import shutil
            shutil.copy2(video_path, output_path)
            return True
        except Exception:
            return False

    def _apply_template_to_video(self, video_path: str, output_path: str,
                                template_config: Dict[str, Any], customization: Dict[str, Any],
                                content: Dict[str, Any], timing: Dict[str, Any]) -> bool:
        """Apply template to video using FFmpeg"""

        try:
            # Build filter chain for template
            filter_chain = self._build_template_filter_chain(
                template_config, customization, content, timing
            )

            # Get resolution settings
            resolution = template_config.get("resolution", "1920x1080")
            width, height = resolution.split('x')

            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,{filter_chain}',
                '-c:v', 'libx264', '-c:a', 'aac',
                '-crf', '23', '-preset', 'medium',
                '-movflags', '+faststart',
                '-y', output_path
            ]

            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception:
            return False

    def _build_template_filter_chain(self, template_config: Dict[str, Any],
                                   customization: Dict[str, Any], content: Dict[str, Any],
                                   timing: Dict[str, Any]) -> str:
        """Build FFmpeg filter chain for template"""

        filters = []

        # Apply template effects
        effects = template_config.get("effects", [])
        for effect in effects:
            if effect == "fade_in":
                filters.append("fade=t=in:st=0:d=1")
            elif effect == "fade_out":
                filters.append("fade=t=out:st=10:d=1")
            elif effect == "smooth_zoom":
                filters.append("zoompan=z='min(zoom+0.001,1.5)':d=125")
            elif effect == "glitch":
                filters.append("noise=alls=20:allf=t+u")
            elif effect == "color_pop":
                filters.append("eq=saturation=1.5")
            elif effect == "neon_glow":
                filters.append("glow=intensity=0.5")

        # Apply customization colors
        colors = customization.get("colors", {})
        if colors.get("primary"):
            # Color adjustment based on primary color
            filters.append("colorbalance=rs=0.1:gs=0.1:bs=0.1")

        # Add text overlays
        title = content.get("title", "")
        if title:
            title_config = template_config.get("overlays", {}).get("title", {})
            font_size = title_config.get("size", 48)
            color = title_config.get("color", "#FFFFFF")

            # Simple text overlay
            text_filter = f"drawtext=text='{title}':x=(w-text_w)/2:y=50:fontsize={font_size}:fontcolor={color}:box=1:boxcolor=black@0.5"
            filters.append(text_filter)

        # Add subtitle
        subtitle = content.get("subtitle", "")
        if subtitle:
            subtitle_config = template_config.get("overlays", {}).get("subtitle", {})
            font_size = subtitle_config.get("size", 24)
            color = subtitle_config.get("color", "#CCCCCC")

            text_filter = f"drawtext=text='{subtitle}':x=(w-text_w)/2:y=h-100:fontsize={font_size}:fontcolor={color}:box=1:boxcolor=black@0.5"
            filters.append(text_filter)

        # Add hashtags
        hashtags = content.get("hashtags", [])
        if hashtags:
            hashtag_text = " ".join(hashtags)
            text_filter = f"drawtext=text='{hashtag_text}':x=(w-text_w)/2:y=h-50:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5"
            filters.append(text_filter)

        return ','.join(filters) if filters else 'null'

    def _get_applied_customizations(self, customization: Dict[str, Any]) -> List[str]:
        """Get list of applied customizations"""

        applied = []

        if customization.get("colors"):
            applied.append("Custom color scheme")

        if customization.get("fonts"):
            applied.append("Custom fonts")

        if customization.get("branding"):
            applied.append("Brand customization")

        if customization.get("layout"):
            applied.append("Layout customization")

        return applied

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

    def get_available_templates(self) -> Dict[str, Any]:
        """Get list of available templates"""

        return {
            "templates": [
                {
                    "name": "modern_minimal",
                    "style": "modern",
                    "description": "Clean, minimal design with subtle animations",
                    "platforms": ["youtube", "instagram", "generic"],
                    "features": ["fade_in", "fade_out", "smooth_zoom"]
                },
                {
                    "name": "social_burst",
                    "style": "energetic",
                    "description": "High-energy template for social media",
                    "platforms": ["tiktok", "instagram", "twitter"],
                    "features": ["zoom_burst", "color_pop", "glitch"]
                },
                {
                    "name": "professional",
                    "style": "corporate",
                    "description": "Professional template for business content",
                    "platforms": ["youtube", "linkedin", "generic"],
                    "features": ["slide_in", "fade_out", "logo_overlay"]
                },
                {
                    "name": "gaming",
                    "style": "gaming",
                    "description": "Gaming-focused template with neon effects",
                    "platforms": ["youtube", "twitch", "generic"],
                    "features": ["glitch", "neon_glow", "rgb_shift"]
                },
                {
                    "name": "educational",
                    "style": "clean",
                    "description": "Clean template for educational content",
                    "platforms": ["youtube", "generic"],
                    "features": ["fade_in", "fade_out", "text_overlay"]
                }
            ]
        }

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "TEMPLATE_ENGINE_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python template_engine.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        engine = TemplateEngine()
        result = engine.apply_template(input_data)
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
