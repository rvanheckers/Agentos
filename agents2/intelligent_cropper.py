#!/usr/bin/env python3
"""
Intelligent Cropper Agent - Atomic Agent
=======================================

Calculates smart crop coordinates for optimal video framing.
Single responsibility: Determine the best crop area for video content.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, List, Any, Tuple

class IntelligentCropper:
    """
    Atomic agent for calculating intelligent crop coordinates.

    Uses face detection data and content analysis to determine
    optimal crop areas for different aspect ratios.
    """

    def __init__(self):
        self.version = "1.0.0"

    def calculate_crop(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate intelligent crop coordinates.

        Args:
            input_data: {
                "video_path": str,
                "faces": List[dict],         # optional, from face_detector
                "moments": List[dict],       # optional, from moment_detector
                "target_aspect_ratio": str,  # "9:16", "16:9", "1:1", etc.
                "padding": float,            # optional, padding around subjects (0.0-0.5)
                "priority": str              # "faces", "center", "content"
            }

        Returns:
            {
                "success": bool,
                "crop_coordinates": {
                    "x": int,                # left position
                    "y": int,                # top position
                    "width": int,            # crop width
                    "height": int            # crop height
                },
                "original_resolution": {
                    "width": int,
                    "height": int
                },
                "crop_info": {
                    "aspect_ratio": str,
                    "scale_factor": float,
                    "faces_included": int,
                    "crop_method": str
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

            video_path = input_data["video_path"]
            if not os.path.exists(video_path):
                return self._error(f"Video file not found: {video_path}")

            # Get parameters
            faces = input_data.get("faces", [])
            moments = input_data.get("moments", [])
            target_aspect_ratio = input_data.get("target_aspect_ratio", "9:16")
            padding = input_data.get("padding", 0.1)
            priority = input_data.get("priority", "faces")

            # Get video resolution
            resolution = self._get_video_resolution(video_path)
            if not resolution:
                return self._error("Could not determine video resolution")

            original_width, original_height = resolution

            # Parse target aspect ratio
            target_ratio = self._parse_aspect_ratio(target_aspect_ratio)
            if not target_ratio:
                return self._error(f"Invalid aspect ratio: {target_aspect_ratio}")

            # Calculate crop coordinates
            crop_coords = self._calculate_optimal_crop(
                original_width, original_height,
                target_ratio, faces, moments, padding, priority
            )

            # Calculate additional info
            crop_info = self._calculate_crop_info(
                original_width, original_height,
                crop_coords, target_aspect_ratio, faces
            )

            processing_time = time.time() - start_time

            return {
                "success": True,
                "crop_coordinates": crop_coords,
                "original_resolution": {
                    "width": original_width,
                    "height": original_height
                },
                "crop_info": crop_info,
                "processing_time": processing_time,
                "agent_version": self.version
            }

        except Exception as e:
            return self._error(f"Crop calculation failed: {str(e)}")

    def _calculate_optimal_crop(self, orig_width: int, orig_height: int,
                               target_ratio: float, faces: List[dict],
                               moments: List[dict], padding: float,
                               priority: str) -> Dict[str, int]:
        """Calculate optimal crop coordinates"""

        # Calculate target dimensions
        if target_ratio > (orig_width / orig_height):
            # Target is wider than original
            crop_width = orig_width
            crop_height = int(orig_width / target_ratio)
        else:
            # Target is taller than original
            crop_height = orig_height
            crop_width = int(orig_height * target_ratio)

        # Ensure crop dimensions don't exceed original
        crop_width = min(crop_width, orig_width)
        crop_height = min(crop_height, orig_height)

        # Calculate crop position based on priority
        if priority == "faces" and faces:
            x, y = self._calculate_face_based_crop(
                orig_width, orig_height, crop_width, crop_height,
                faces, padding
            )
        elif priority == "content" and moments:
            x, y = self._calculate_content_based_crop(
                orig_width, orig_height, crop_width, crop_height,
                moments, padding
            )
        else:
            # Default to center crop
            x = (orig_width - crop_width) // 2
            y = (orig_height - crop_height) // 2

        # Ensure crop stays within bounds
        x = max(0, min(x, orig_width - crop_width))
        y = max(0, min(y, orig_height - crop_height))

        return {
            "x": x,
            "y": y,
            "width": crop_width,
            "height": crop_height
        }

    def _calculate_face_based_crop(self, orig_width: int, orig_height: int,
                                  crop_width: int, crop_height: int,
                                  faces: List[dict], padding: float) -> Tuple[int, int]:
        """Calculate crop position based on face locations"""

        if not faces:
            return (orig_width - crop_width) // 2, (orig_height - crop_height) // 2

        # Find average face position
        total_x = 0
        total_y = 0
        face_count = 0

        for face in faces:
            bbox = face.get("bbox", {})
            if bbox:
                # Face bbox typically has x, y, width, height
                face_x = bbox.get("x", 0) + bbox.get("width", 0) / 2
                face_y = bbox.get("y", 0) + bbox.get("height", 0) / 2

                total_x += face_x
                total_y += face_y
                face_count += 1

        if face_count > 0:
            avg_face_x = total_x / face_count
            avg_face_y = total_y / face_count

            # Position crop to center on average face position
            x = int(avg_face_x - crop_width / 2)
            y = int(avg_face_y - crop_height / 2)

            # Apply padding
            padding_x = int(crop_width * padding)
            padding_y = int(crop_height * padding)

            x = max(padding_x, min(x, orig_width - crop_width - padding_x))
            y = max(padding_y, min(y, orig_height - crop_height - padding_y))

            return x, y

        # Fallback to center
        return (orig_width - crop_width) // 2, (orig_height - crop_height) // 2

    def _calculate_content_based_crop(self, orig_width: int, orig_height: int,
                                     crop_width: int, crop_height: int,
                                     moments: List[dict], padding: float) -> Tuple[int, int]:
        """Calculate crop position based on content moments"""

        # For now, use center crop for content-based
        # This could be enhanced with actual content analysis
        return (orig_width - crop_width) // 2, (orig_height - crop_height) // 2

    def _get_video_resolution(self, video_path: str) -> Tuple[int, int]:
        """Get video resolution using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=p=0', video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                width, height = result.stdout.strip().split(',')
                return int(width), int(height)
            else:
                return None

        except Exception:
            return None

    def _parse_aspect_ratio(self, ratio_str: str) -> float:
        """Parse aspect ratio string to float"""
        try:
            if ':' in ratio_str:
                width, height = ratio_str.split(':')
                return float(width) / float(height)
            else:
                return float(ratio_str)
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def _calculate_crop_info(self, orig_width: int, orig_height: int,
                           crop_coords: Dict[str, int], target_aspect_ratio: str,
                           faces: List[dict]) -> Dict[str, Any]:
        """Calculate additional crop information"""

        crop_width = crop_coords["width"]
        crop_height = crop_coords["height"]

        # Calculate scale factor
        scale_factor = min(crop_width / orig_width, crop_height / orig_height)

        # Count faces included in crop
        faces_included = 0
        crop_x = crop_coords["x"]
        crop_y = crop_coords["y"]

        for face in faces:
            bbox = face.get("bbox", {})
            if bbox:
                face_x = bbox.get("x", 0)
                face_y = bbox.get("y", 0)
                face_w = bbox.get("width", 0)
                face_h = bbox.get("height", 0)

                # Check if face center is within crop area
                face_center_x = face_x + face_w / 2
                face_center_y = face_y + face_h / 2

                if (crop_x <= face_center_x <= crop_x + crop_width and
                    crop_y <= face_center_y <= crop_y + crop_height):
                    faces_included += 1

        # Determine crop method
        if faces_included > 0:
            crop_method = "face_based"
        elif crop_x == (orig_width - crop_width) // 2 and crop_y == (orig_height - crop_height) // 2:
            crop_method = "center"
        else:
            crop_method = "content_based"

        return {
            "aspect_ratio": target_aspect_ratio,
            "scale_factor": scale_factor,
            "faces_included": faces_included,
            "crop_method": crop_method
        }

    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "CROP_CALCULATION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python intelligent_cropper.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        cropper = IntelligentCropper()
        result = cropper.calculate_crop(input_data)
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
