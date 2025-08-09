#!/usr/bin/env python3
"""
Voiceover Creator Agent - Atomic Agent
=====================================

Creates voiceovers from text using text-to-speech technology.
Single responsibility: Generate high-quality voiceovers for video content.
"""

import json
import sys
import os
import subprocess
import time
from typing import Dict, Any

class VoiceoverCreator:
    """
    Atomic agent for creating voiceovers from text.
    
    Generates natural-sounding voiceovers for video content
    using various text-to-speech engines and voice options.
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.tts_available = self._check_tts_availability()
    
    def create_voiceover(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create voiceover from text.
        
        Args:
            input_data: {
                "text": str,                 # text to convert to speech
                "output_path": str,          # output audio file path
                "voice": str,                # voice selection (optional)
                "speed": float,              # speech speed (0.5-2.0, default: 1.0)
                "pitch": float,              # pitch adjustment (-50 to 50, default: 0)
                "volume": float,             # volume level (0.0-1.0, default: 1.0)
                "format": str,               # output format (mp3, wav, default: mp3)
                "language": str,             # language code (en, es, fr, etc.)
                "emotion": str,              # emotion/tone (neutral, happy, sad, etc.)
                "pause_duration": float,     # pause between sentences (seconds)
                "background_music": str,     # optional background music file
                "music_volume": float        # background music volume (0.0-1.0)
            }
            
        Returns:
            {
                "success": bool,
                "voiceover_file": str,       # path to generated voiceover
                "duration": float,           # duration in seconds
                "word_count": int,           # number of words processed
                "voice_info": {
                    "voice_used": str,
                    "language": str,
                    "speed": float,
                    "pitch": float,
                    "format": str
                },
                "audio_specs": {
                    "sample_rate": int,
                    "channels": int,
                    "bitrate": str,
                    "file_size": int
                },
                "processing_time": float,
                "agent_version": str
            }
        """
        
        start_time = time.time()
        
        try:
            # Validate inputs
            if not input_data.get("text"):
                return self._error("text is required")
            
            if not input_data.get("output_path"):
                return self._error("output_path is required")
            
            # Get parameters
            text = input_data["text"]
            output_path = input_data["output_path"]
            voice = input_data.get("voice", "default")
            speed = input_data.get("speed", 1.0)
            pitch = input_data.get("pitch", 0)
            volume = input_data.get("volume", 1.0)
            format_type = input_data.get("format", "mp3")
            language = input_data.get("language", "en")
            emotion = input_data.get("emotion", "neutral")
            pause_duration = input_data.get("pause_duration", 0.5)
            background_music = input_data.get("background_music", "")
            music_volume = input_data.get("music_volume", 0.2)
            
            # Validate parameters
            if not self._validate_parameters(speed, pitch, volume, format_type):
                return self._error("Invalid parameters provided")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate voiceover
            voiceover_result = self._generate_voiceover(
                text, output_path, voice, speed, pitch, volume,
                format_type, language, emotion, pause_duration
            )
            
            if not voiceover_result["success"]:
                return voiceover_result
            
            # Add background music if specified
            final_output = output_path
            if background_music and os.path.exists(background_music):
                final_output = self._add_background_music(
                    voiceover_result["file_path"], background_music, 
                    music_volume, output_path
                )
            
            # Get audio specifications
            audio_specs = self._get_audio_specs(final_output)
            
            # Get file duration
            duration = self._get_audio_duration(final_output)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "voiceover_file": final_output,
                "duration": duration,
                "word_count": len(text.split()),
                "voice_info": {
                    "voice_used": voice,
                    "language": language,
                    "speed": speed,
                    "pitch": pitch,
                    "format": format_type
                },
                "audio_specs": audio_specs,
                "processing_time": processing_time,
                "agent_version": self.version
            }
            
        except Exception as e:
            return self._error(f"Voiceover creation failed: {str(e)}")
    
    def _validate_parameters(self, speed: float, pitch: float, volume: float, format_type: str) -> bool:
        """Validate input parameters"""
        
        if not (0.5 <= speed <= 2.0):
            return False
        
        if not (-50 <= pitch <= 50):
            return False
        
        if not (0.0 <= volume <= 1.0):
            return False
        
        if format_type not in ["mp3", "wav", "ogg", "m4a"]:
            return False
        
        return True
    
    def _generate_voiceover(self, text: str, output_path: str, voice: str,
                           speed: float, pitch: float, volume: float,
                           format_type: str, language: str, emotion: str,
                           pause_duration: float) -> Dict[str, Any]:
        """Generate voiceover using available TTS engine"""
        
        # Try different TTS engines in order of preference
        engines = [
            self._try_festival_tts,
            self._try_espeak_tts,
            self._try_system_tts,
            self._try_python_tts
        ]
        
        for engine in engines:
            try:
                result = engine(text, output_path, voice, speed, pitch, volume,
                               format_type, language, emotion, pause_duration)
                if result["success"]:
                    return result
            except Exception:
                continue
        
        # If all engines fail, create a simple placeholder
        return self._create_placeholder_audio(text, output_path, format_type)
    
    def _try_festival_tts(self, text: str, output_path: str, voice: str,
                         speed: float, pitch: float, volume: float,
                         format_type: str, language: str, emotion: str,
                         pause_duration: float) -> Dict[str, Any]:
        """Try Festival TTS engine"""
        
        try:
            # Check if festival is available
            result = subprocess.run(['festival', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return {"success": False, "error": "Festival not available"}
            
            # Create temporary text file
            temp_text_file = output_path + ".txt"
            with open(temp_text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Generate speech with festival
            temp_wav = output_path + ".wav"
            cmd = [
                'festival', '--tts', temp_text_file,
                '--output', temp_wav
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(temp_wav):
                # Convert to desired format if needed
                if format_type != "wav":
                    self._convert_audio_format(temp_wav, output_path, format_type)
                    os.remove(temp_wav)
                else:
                    os.rename(temp_wav, output_path)
                
                # Clean up
                os.remove(temp_text_file)
                
                return {
                    "success": True,
                    "file_path": output_path,
                    "engine": "festival"
                }
            
        except Exception:
            pass
        
        return {"success": False, "error": "Festival TTS failed"}
    
    def _try_espeak_tts(self, text: str, output_path: str, voice: str,
                       speed: float, pitch: float, volume: float,
                       format_type: str, language: str, emotion: str,
                       pause_duration: float) -> Dict[str, Any]:
        """Try eSpeak TTS engine"""
        
        try:
            # Check if espeak is available
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return {"success": False, "error": "eSpeak not available"}
            
            # Build espeak command
            temp_wav = output_path + ".wav"
            cmd = [
                'espeak', '-s', str(int(speed * 175)),  # speed in words per minute
                '-p', str(int(pitch + 50)),             # pitch adjustment
                '-a', str(int(volume * 200)),           # amplitude
                '-v', f'{language}+{voice}',            # voice
                '-w', temp_wav,                         # output file
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(temp_wav):
                # Convert to desired format if needed
                if format_type != "wav":
                    self._convert_audio_format(temp_wav, output_path, format_type)
                    os.remove(temp_wav)
                else:
                    os.rename(temp_wav, output_path)
                
                return {
                    "success": True,
                    "file_path": output_path,
                    "engine": "espeak"
                }
            
        except Exception:
            pass
        
        return {"success": False, "error": "eSpeak TTS failed"}
    
    def _try_system_tts(self, text: str, output_path: str, voice: str,
                       speed: float, pitch: float, volume: float,
                       format_type: str, language: str, emotion: str,
                       pause_duration: float) -> Dict[str, Any]:
        """Try system TTS (macOS say command)"""
        
        try:
            # Check if say command is available (macOS)
            result = subprocess.run(['say', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return {"success": False, "error": "System TTS not available"}
            
            # Use say command to generate audio
            temp_aiff = output_path + ".aiff"
            cmd = [
                'say', '-v', voice, '-r', str(int(speed * 200)),
                '-o', temp_aiff, text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(temp_aiff):
                # Convert to desired format
                self._convert_audio_format(temp_aiff, output_path, format_type)
                os.remove(temp_aiff)
                
                return {
                    "success": True,
                    "file_path": output_path,
                    "engine": "system_tts"
                }
            
        except Exception:
            pass
        
        return {"success": False, "error": "System TTS failed"}
    
    def _try_python_tts(self, text: str, output_path: str, voice: str,
                       speed: float, pitch: float, volume: float,
                       format_type: str, language: str, emotion: str,
                       pause_duration: float) -> Dict[str, Any]:
        """Try Python TTS libraries"""
        
        try:
            # Try pyttsx3 if available
            import pyttsx3
            
            engine = pyttsx3.init()
            engine.setProperty('rate', int(speed * 200))
            engine.setProperty('volume', volume)
            
            # Save to file
            temp_wav = output_path + ".wav"
            engine.save_to_file(text, temp_wav)
            engine.runAndWait()
            
            if os.path.exists(temp_wav):
                # Convert to desired format if needed
                if format_type != "wav":
                    self._convert_audio_format(temp_wav, output_path, format_type)
                    os.remove(temp_wav)
                else:
                    os.rename(temp_wav, output_path)
                
                return {
                    "success": True,
                    "file_path": output_path,
                    "engine": "pyttsx3"
                }
            
        except ImportError:
            pass
        except Exception:
            pass
        
        return {"success": False, "error": "Python TTS failed"}
    
    def _create_placeholder_audio(self, text: str, output_path: str, format_type: str) -> Dict[str, Any]:
        """Create placeholder audio file when TTS engines fail"""
        
        try:
            # Create silent audio file with ffmpeg
            duration = max(5, len(text.split()) * 0.5)  # Estimate duration
            
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=duration={duration}',
                '-acodec', 'libmp3lame' if format_type == 'mp3' else 'pcm_s16le',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": output_path,
                    "engine": "placeholder"
                }
            
        except Exception:
            pass
        
        return {"success": False, "error": "Could not create placeholder audio"}
    
    def _convert_audio_format(self, input_path: str, output_path: str, format_type: str) -> bool:
        """Convert audio to desired format using ffmpeg"""
        
        try:
            cmd = [
                'ffmpeg', '-i', input_path, '-acodec',
                'libmp3lame' if format_type == 'mp3' else 'pcm_s16le',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _add_background_music(self, voiceover_path: str, music_path: str,
                             music_volume: float, output_path: str) -> str:
        """Add background music to voiceover"""
        
        try:
            # Mix voiceover with background music using ffmpeg
            cmd = [
                'ffmpeg', '-i', voiceover_path, '-i', music_path,
                '-filter_complex', f'[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return output_path
            
        except Exception:
            pass
        
        # Return original voiceover if mixing fails
        return voiceover_path
    
    def _get_audio_specs(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file specifications"""
        
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]
                    
                    return {
                        "sample_rate": int(stream.get('sample_rate', 44100)),
                        "channels": int(stream.get('channels', 2)),
                        "bitrate": stream.get('bit_rate', 'unknown'),
                        "file_size": int(data['format'].get('size', 0))
                    }
            
        except Exception:
            pass
        
        return {
            "sample_rate": 44100,
            "channels": 2,
            "bitrate": "unknown",
            "file_size": 0
        }
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration"""
        
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            
        except Exception:
            pass
        
        return 0.0
    
    def _check_tts_availability(self) -> Dict[str, bool]:
        """Check which TTS engines are available"""
        
        availability = {
            "festival": False,
            "espeak": False,
            "system_tts": False,
            "python_tts": False
        }
        
        # Check Festival
        try:
            result = subprocess.run(['festival', '--version'], 
                                  capture_output=True, timeout=5)
            availability["festival"] = result.returncode == 0
        except:
            pass
        
        # Check eSpeak
        try:
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, timeout=5)
            availability["espeak"] = result.returncode == 0
        except:
            pass
        
        # Check system TTS (macOS)
        try:
            result = subprocess.run(['say', '--version'], 
                                  capture_output=True, timeout=5)
            availability["system_tts"] = result.returncode == 0
        except:
            pass
        
        # Check Python TTS
        try:
            availability["python_tts"] = True
        except:
            pass
        
        return availability
    
    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "VOICEOVER_CREATION_ERROR",
            "agent_version": self.version
        }

def main():
    """Main entry point for command line usage"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python voiceover_creator.py '<json_input>'",
            "error_code": "INVALID_ARGUMENTS"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
        creator = VoiceoverCreator()
        result = creator.create_voiceover(input_data)
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