#!/usr/bin/env python3
"""
Video Cutter Agent - Atomic Agent
=================================

Specializes ONLY in cutting video at specific timestamps.
No effects, no analysis, no face detection - just cutting.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, Any
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class VideoCutter:
    """
    Atomic agent for cutting video at specific timestamps.
    
    Single responsibility: Cut video segments using FFmpeg.
    """
    
    def __init__(self):
        self.agent_name = "video_cutter"
        self.ffmpeg_available = self._check_ffmpeg()
    
    def cut_video(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cut video at specified timestamps - Celery compatible (no database logging).
        
        Args:
            input_data: {
                "job_id": str,           # Optional for Celery compatibility
                "video_path": str,
                "output_path": str,
                "cuts": List[{
                    "start_time": float,  # seconds
                    "end_time": float,    # seconds
                    "output_name": str    # optional
                }],
                "format": str,           # optional, default: mp4
                "copy_streams": bool     # optional, default: False (faster)
            }
            
        Returns:
            {
                "success": bool,
                "cut_videos": List[{
                    "path": str,
                    "duration": float,
                    "size": int,
                    "start_time": float,
                    "end_time": float
                }],
                "total_cuts": int,
                "successful_cuts": int,
                "processing_time": float
            }
        """
        # Direct execution without problematic database logging
        return self._execute_cutting(input_data)
    
    def _execute_cutting(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method that does the actual cutting work"""
        start_time = time.time()
        
        try:
            # Validate input
            if not self._validate_input(input_data):
                return self._error_response("Invalid input data")
            
            if not self.ffmpeg_available:
                return self._error_response("FFmpeg not available")
            
            video_path = input_data["video_path"]
            output_path = input_data["output_path"]
            cuts = input_data["cuts"]
            format_type = input_data.get("format", "mp4")
            copy_streams = input_data.get("copy_streams", False)
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Process each cut
            cut_results = []
            for i, cut in enumerate(cuts):
                result = self._cut_segment(
                    video_path, cut, output_path, format_type, copy_streams, i + 1
                )
                cut_results.append(result)
            
            # Calculate statistics
            successful_cuts = [r for r in cut_results if r.get("success", False)]
            processing_time = time.time() - start_time
            
            return {
                "success": len(successful_cuts) > 0,
                "cut_videos": successful_cuts,
                "total_cuts": len(cuts),
                "successful_cuts": len(successful_cuts),
                "processing_time": processing_time,
                "agent_version": "1.0.0"
            }
            
        except Exception as e:
            return self._error_response(f"Video cutting failed: {str(e)}")
    
    def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data structure."""
        required_fields = ["video_path", "output_path", "cuts"]
        for field in required_fields:
            if field not in input_data:
                return False
        
        if not os.path.exists(input_data["video_path"]):
            return False
        
        if not input_data["cuts"]:
            return False
        
        # Validate each cut
        for cut in input_data["cuts"]:
            if "start_time" not in cut or "end_time" not in cut:
                return False
            if cut["start_time"] >= cut["end_time"]:
                return False
        
        return True
    
    def _cut_segment(self, video_path: str, cut: Dict[str, Any], output_path: str, 
                    format_type: str, copy_streams: bool, cut_number: int) -> Dict[str, Any]:
        """Cut a single video segment."""
        try:
            start_time = cut["start_time"]
            end_time = cut["end_time"]
            duration = end_time - start_time
            
            # Generate output filename
            output_name = cut.get("output_name", f"cut_{cut_number:03d}")
            if not output_name.endswith(f".{format_type}"):
                output_name += f".{format_type}"
            
            output_file = os.path.join(output_path, output_name)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-i', video_path,
                '-ss', str(start_time),  # Start time
                '-t', str(duration),     # Duration
            ]
            
            if copy_streams:
                # Copy streams (faster but less precise)
                cmd.extend(['-c', 'copy'])
            else:
                # Re-encode (slower but more precise)
                cmd.extend([
                    '-c:v', 'libx264',  # Video codec
                    '-c:a', 'aac',      # Audio codec
                    '-preset', 'fast'   # Encoding speed
                ])
            
            cmd.append(output_file)
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                
                return {
                    "success": True,
                    "path": output_file,
                    "duration": duration,
                    "size": file_size,
                    "start_time": start_time,
                    "end_time": end_time,
                    "cut_number": cut_number
                }
            else:
                return {
                    "success": False,
                    "error": f"FFmpeg failed: {result.stderr}",
                    "cut_number": cut_number
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "FFmpeg timeout",
                "cut_number": cut_number
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cut_number": cut_number
            }
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate standardized error response."""
        return {
            "success": False,
            "error": error_message,
            "error_code": "VIDEO_CUTTING_ERROR",
            "cut_videos": [],
            "total_cuts": 0,
            "successful_cuts": 0,
            "processing_time": 0,
            "agent_version": "1.0.0"
        }

def main():
    """Main entry point for atomic video cutting agent."""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python video_cutter.py '<json_input>'",
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
    
    # Process video cutting
    cutter = VideoCutter()
    result = cutter.cut_video(input_data)
    
    # Output result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)

if __name__ == "__main__":
    main()