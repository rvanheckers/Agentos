"""
Intelligent Content Type Detection
Priority: User Intent > YouTube Metadata > Audio Analysis > Default
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SmartContentDetector:
    """Top 0.1% approach: Layered detection with clear priority"""

    MUSIC_INDICATORS = [
        'music', 'song', 'album', 'artist', 'lyrics',
        'official video', 'music video', 'feat.', 'prod.',
        'remix', 'cover', 'acoustic', 'live performance'
    ]

    PODCAST_INDICATORS = [
        'podcast', 'episode', 'interview', 'discussion',
        'talk', 'conversation', 'ep.', 'guest', 'host'
    ]

    @classmethod
    def detect_content_type(
        cls,
        user_intent: Optional[str] = None,
        youtube_metadata: Optional[Dict[str, Any]] = None,
        audio_analysis: Optional[Dict[str, Any]] = None,
        transcript: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detect content type with layered priority system"""

        # Layer 1: User Intent (Highest Priority)
        if user_intent and user_intent != 'auto':
            logger.info(f'🎯 Using user intent: {user_intent}')
            return cls._format_result(
                content_type=user_intent,
                confidence=1.0,
                method='user_intent'
            )

        # Layer 2: YouTube Metadata Analysis
        if youtube_metadata:
            metadata_result = cls._analyze_metadata(youtube_metadata)
            if metadata_result['confidence'] > 0.7:
                logger.info(f'📊 Using metadata detection: {metadata_result}')
                return metadata_result

        # Layer 3: Audio Analysis (if available)
        if audio_analysis and audio_analysis.get('is_music_confidence', 0) > 0.7:
            logger.info(f'🎵 Audio analysis detected music')
            return cls._format_result(
                content_type='music',
                confidence=audio_analysis['is_music_confidence'],
                method='audio_analysis'
            )

        # Layer 4: Default Fallback
        logger.info('📌 Using default: spoken content')
        return cls._format_result(
            content_type='spoken',
            confidence=0.5,
            method='default'
        )

    @classmethod
    def _analyze_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze YouTube metadata for content type"""
        title = metadata.get('title', '').lower()
        description = metadata.get('description', '').lower()

        combined_text = f'{title} {description}'

        # Check music indicators
        music_score = sum(1 for indicator in cls.MUSIC_INDICATORS if indicator in combined_text)
        podcast_score = sum(1 for indicator in cls.PODCAST_INDICATORS if indicator in combined_text)

        if music_score >= 2:
            return cls._format_result('music', 0.8, 'metadata')
        elif podcast_score >= 2:
            return cls._format_result('spoken', 0.8, 'metadata')

        return cls._format_result('spoken', 0.6, 'metadata')

    @classmethod
    def _format_result(
        cls,
        content_type: str,
        confidence: float,
        method: str
    ) -> Dict[str, Any]:
        """Format detection result"""

        if content_type == 'music':
            analysis_mode = 'ai_song_lyrics'
        else:
            analysis_mode = 'ai_viral_analysis'

        return {
            'content_type': content_type,
            'analysis_mode': analysis_mode,
            'confidence': round(confidence, 2),
            'detection_method': method
        }