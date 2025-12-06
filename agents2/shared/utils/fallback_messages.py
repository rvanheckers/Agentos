"""
Professional Fallback Message System
Replaces mock data with honest user communication
"""

class FallbackMessages:
    """Proper fallback messages instead of fake data"""

    MESSAGES = {
        'transcription_unavailable': {
            'nl': 'Audio analyse tijdelijk niet beschikbaar - visuele analyse actief',
            'en': 'Audio analysis temporarily unavailable - visual analysis active'
        },
        'metadata_missing': {
            'nl': 'Video informatie wordt verwerkt...',
            'en': 'Video information being processed...'
        },
        'queue_delayed': {
            'nl': 'Hoge wachtrij volume - geschatte wachttijd: {time}',
            'en': 'High queue volume - estimated wait: {time}'
        },
        'audio_disabled': {
            'nl': 'Audio analyse uitgeschakeld - metadata detectie actief',
            'en': 'Audio analysis disabled - metadata detection active'
        },
        'processing_temporary': {
            'nl': 'Clips zijn tijdelijk beschikbaar (7 dagen)',
            'en': 'Clips available temporarily (7 days)'
        }
    }

    @staticmethod
    def get(key: str, language: str = 'nl', **kwargs) -> str:
        """Get fallback message in specified language"""
        message = FallbackMessages.MESSAGES.get(key, {}).get(language, '')
        return message.format(**kwargs) if kwargs else message

    @staticmethod
    def get_processing_status(step: str, language: str = 'nl') -> str:
        """Get proper status message for processing step"""
        status_messages = {
            'downloading': {'nl': 'Video downloaden...', 'en': 'Downloading video...'},
            'transcribing': {'nl': 'Audio analyseren...', 'en': 'Analyzing audio...'},
            'detecting': {'nl': 'Virale momenten detecteren...', 'en': 'Detecting viral moments...'},
            'creating': {'nl': 'Clips genereren...', 'en': 'Generating clips...'}
        }
        return status_messages.get(step, {}).get(language, step)