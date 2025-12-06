"""
Audio Analysis Agent - Music vs Speech Detection
Industry-standard approach using audio signal processing.
"""

import os
import logging
import time
from typing import Dict, Any, Tuple
import numpy as np

try:
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    logging.warning("Audio analysis libraries not available. Install librosa and soundfile.")

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """
    Industry-standard audio content type detection agent.
    Uses signal processing techniques to distinguish music from speech.
    
    Based on research from audio fingerprinting and MIR (Music Information Retrieval).
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.sample_rate = 22050  # Standard for music analysis
        
    def analyze_content_type(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze audio file to detect content type: music vs speech.
        
        Args:
            input_data: {
                "audio_path": str,  # Path to audio file (.mp3, .wav, etc.)
                "video_path": str   # Optional: path to source video
            }
            
        Returns:
            {
                "success": bool,
                "content_type": str,        # "music" or "spoken" 
                "confidence": float,        # 0-1 confidence score
                "music_score": float,       # 0-1 raw music likelihood
                "spoken_score": float,      # 0-1 raw speech likelihood
                "features": {
                    "tempo": float,         # BPM if music detected
                    "spectral_centroid": float,
                    "spectral_rolloff": float,
                    "zero_crossing_rate": float,
                    "mfcc_variance": float
                },
                "analysis_duration": float,
                "agent_version": str
            }
        """
        
        start_time = time.time()
        
        if not AUDIO_LIBS_AVAILABLE:
            return self._error("Audio analysis libraries not available")
            
        try:
            # Validate input
            audio_path = input_data.get("audio_path")
            if not audio_path or not os.path.exists(audio_path):
                return self._error(f"Audio file not found: {audio_path}")
                
            logger.info(f"🎵 Analyzing audio content: {os.path.basename(audio_path)}")
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate, duration=30)  # Analyze first 30 seconds
            
            if len(y) == 0:
                return self._error("Could not load audio data")
                
            # Extract audio features
            features = self._extract_features(y, sr)
            
            # Classify content type
            music_score, spoken_score, content_type, confidence = self._classify_content(features)
            
            processing_time = time.time() - start_time
            
            logger.info(f"🎯 Audio Analysis: {content_type.upper()} (confidence: {confidence:.2f})")
            logger.info(f"📊 Scores - Music: {music_score:.2f}, Speech: {spoken_score:.2f}")
            
            return {
                "success": True,
                "content_type": content_type,
                "confidence": confidence,
                "music_score": music_score,
                "spoken_score": spoken_score,
                "features": features,
                "analysis_duration": processing_time,
                "agent_version": self.version
            }
            
        except Exception as e:
            logger.error(f"🚫 Audio analysis failed: {str(e)}")
            return self._error(f"Audio analysis failed: {str(e)}")
    
    def _extract_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Extract audio features for classification - Robust version."""
        
        features = {}
        
        try:
            # 1. TEMPO ANALYSIS - Strong indicator of music (more robust approach)
            try:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                features['tempo'] = float(tempo) if tempo and tempo > 0 else 0.0
                if len(beats) > 1:
                    features['beat_consistency'] = float(1.0 / (1.0 + np.std(np.diff(beats))))
                else:
                    features['beat_consistency'] = 0.0
            except:
                features['tempo'] = 0.0
                features['beat_consistency'] = 0.0
            
            # 2. SPECTRAL FEATURES - Music vs speech have different spectral signatures
            try:
                spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
                features['spectral_centroid'] = float(np.mean(spectral_centroids))
                features['spectral_centroid_std'] = float(np.std(spectral_centroids))
                
                spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
                features['spectral_rolloff'] = float(np.mean(spectral_rolloff))
            except:
                features['spectral_centroid'] = 0.0
                features['spectral_centroid_std'] = 0.0
                features['spectral_rolloff'] = 0.0
            
            # 3. ZERO CROSSING RATE - Speech has higher ZCR than music
            try:
                zcr = librosa.feature.zero_crossing_rate(y)[0]
                features['zero_crossing_rate'] = float(np.mean(zcr))
                features['zcr_std'] = float(np.std(zcr))
            except:
                features['zero_crossing_rate'] = 0.0
                features['zcr_std'] = 0.0
            
            # 4. MFCC FEATURES - Capture timbral characteristics
            try:
                mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                features['mfcc_variance'] = float(np.var(mfccs))
                features['mfcc_mean'] = float(np.mean(mfccs))
            except:
                features['mfcc_variance'] = 0.0
                features['mfcc_mean'] = 0.0
            
            # 5. HARMONIC vs PERCUSSIVE - Music has more harmonic content (simplified)
            try:
                y_harmonic, y_percussive = librosa.effects.hpss(y)
                features['harmonic_strength'] = float(np.mean(np.abs(y_harmonic)))
                features['percussive_strength'] = float(np.mean(np.abs(y_percussive)))
                features['harmonicity'] = features['harmonic_strength'] / (features['percussive_strength'] + 0.001)
            except:
                features['harmonic_strength'] = 0.0
                features['percussive_strength'] = 0.0
                features['harmonicity'] = 1.0
            
            # 6. CHROMA FEATURES - Strong indicator of musical content
            try:
                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                features['chroma_variance'] = float(np.var(chroma))
                features['chroma_mean'] = float(np.mean(chroma))
                # Music typically has more defined chroma profiles
                features['chroma_strength'] = float(np.max(np.mean(chroma, axis=1)))
            except:
                features['chroma_variance'] = 0.0
                features['chroma_mean'] = 0.0
                features['chroma_strength'] = 0.0
            
            # 7. RMS ENERGY PATTERNS - Music has more dynamic range
            try:
                rms = librosa.feature.rms(y=y)[0]
                features['rms_mean'] = float(np.mean(rms))
                features['rms_std'] = float(np.std(rms))
                features['dynamic_range'] = float(np.max(rms) / (np.min(rms) + 0.001))
            except:
                features['rms_mean'] = 0.0
                features['rms_std'] = 0.0
                features['dynamic_range'] = 1.0
            
        except Exception as e:
            logger.warning(f"Feature extraction error: {e}")
            # Fallback to most basic features
            try:
                zcr = librosa.feature.zero_crossing_rate(y)[0]
                features = {
                    'tempo': 0.0,
                    'spectral_centroid': 0.0,
                    'zero_crossing_rate': float(np.mean(zcr)),
                    'basic_analysis': True
                }
            except:
                features = {'basic_analysis': True, 'error': True}
            
        return features
    
    def _classify_content(self, features: Dict[str, float]) -> Tuple[float, float, str, float]:
        """
        Classify content as music or speech - Improved classification logic.
        Uses multiple weighted features for robust detection.
        """
        
        music_score = 0.0
        speech_score = 0.0
        max_possible_score = 0.0
        
        # 1. TEMPO ANALYSIS (weight: 0.2) - Strong indicator of music
        tempo = features.get('tempo', 0)
        beat_consistency = features.get('beat_consistency', 0)
        if tempo > 50 and tempo < 200:  # Valid music tempo range
            music_score += 0.15
            if beat_consistency > 0.3:  # Consistent beat pattern
                music_score += 0.05
        elif tempo == 0:  # No detectable rhythm suggests speech
            speech_score += 0.1
        max_possible_score += 0.2
        
        # 2. SPECTRAL CENTROID (weight: 0.15) - Timbral characteristics  
        sc = features.get('spectral_centroid', 0)
        if sc > 0:
            if 1000 <= sc <= 3500:  # Music typically in this range
                music_score += 0.1
            elif sc > 4000:  # Speech has higher spectral centroid
                speech_score += 0.1
            
            sc_std = features.get('spectral_centroid_std', 0)
            if sc_std < 800:  # Music has more consistent spectral content
                music_score += 0.05
            elif sc_std > 1200:  # Speech has more variation
                speech_score += 0.05
        max_possible_score += 0.15
        
        # 3. ZERO CROSSING RATE (weight: 0.1) - Speech vs music signature
        zcr = features.get('zero_crossing_rate', 0)
        if zcr > 0:
            if zcr < 0.08:  # Music typically has lower ZCR
                music_score += 0.08
            elif zcr > 0.12:  # Speech has higher ZCR
                speech_score += 0.08
        max_possible_score += 0.1
        
        # 4. HARMONICITY (weight: 0.2) - Key discriminator
        harmonicity = features.get('harmonicity', 1.0)
        harmonic_strength = features.get('harmonic_strength', 0)
        if harmonic_strength > 0:
            if harmonicity > 2.0:  # Strong harmonic content = music
                music_score += 0.15
            elif harmonicity < 1.5 and harmonic_strength < 0.01:  # Low harmonic = speech
                speech_score += 0.1
            
            if harmonic_strength > 0.05:  # Strong harmonic presence
                music_score += 0.05
        max_possible_score += 0.2
        
        # 5. CHROMA FEATURES (weight: 0.15) - Musical note patterns
        chroma_strength = features.get('chroma_strength', 0)
        chroma_var = features.get('chroma_variance', 0)
        if chroma_strength > 0.3:  # Strong chroma = musical notes
            music_score += 0.1
        if chroma_var > 0.001:  # Chroma variation indicates harmony
            music_score += 0.05
        max_possible_score += 0.15
        
        # 6. DYNAMIC RANGE (weight: 0.1) - Music has more dynamic variation
        dynamic_range = features.get('dynamic_range', 1.0)
        if dynamic_range > 5.0:  # High dynamic range typical of music
            music_score += 0.08
        elif dynamic_range < 2.0:  # Speech has lower dynamic range
            speech_score += 0.05
        max_possible_score += 0.1
        
        # 7. MFCC VARIANCE (weight: 0.1) - Timbral complexity
        mfcc_var = features.get('mfcc_variance', 0)
        if mfcc_var > 150:  # High MFCC variance = complex timbre = music
            music_score += 0.07
        elif mfcc_var < 80:  # Low MFCC variance = simple timbre = speech
            speech_score += 0.05
        max_possible_score += 0.1
        
        # Normalize scores
        if max_possible_score > 0:
            music_score = music_score / max_possible_score
            speech_score = speech_score / max_possible_score
        
        # Handle edge case: if both scores are very low, default to slight music bias
        # (most audio content has some musical characteristics)
        if music_score < 0.2 and speech_score < 0.2:
            music_score = 0.4
            speech_score = 0.6
        
        # Ensure scores sum to 1.0
        total_score = music_score + speech_score
        if total_score > 0:
            music_score = music_score / total_score
            speech_score = speech_score / total_score
        else:
            music_score = 0.5
            speech_score = 0.5
        
        # Determine content type and confidence
        if music_score > speech_score:
            content_type = "music"
            confidence = min(0.95, music_score)
        else:
            content_type = "spoken"
            confidence = min(0.95, speech_score)
            
        # Apply minimum confidence
        if confidence < 0.6:
            confidence = 0.6
            
        logger.debug(f"Classification - Music: {music_score:.3f}, Speech: {speech_score:.3f} -> {content_type.upper()}")
        
        return music_score, speech_score, content_type, confidence
    
    def _error(self, message: str) -> Dict[str, Any]:
        """Return error response."""
        return {
            "success": False,
            "error": message,
            "content_type": "unknown",
            "confidence": 0.0,
            "agent_version": self.version
        }