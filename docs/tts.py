"""
This file contains the module to handle text-to-speech functionality
using gTTS (Google Text-to-Speech) to convert text to audio.
"""

import os
import hashlib
from gtts import gTTS
from django.conf import settings
import tempfile

class TextToSpeech:
    """Service to convert text to speech audio files"""
    
    def __init__(self):
        """Initialize TTS service"""
        # Create media directory for audio files if it doesn't exist
        self.audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def _get_file_path(self, text, language):
        """Generate a unique filename based on text content and language"""
        # Create hash from text and language to use as filename
        text_hash = hashlib.md5(f"{text}_{language}".encode()).hexdigest()
        return os.path.join(self.audio_dir, f"{text_hash}_{language}.mp3")
    
    def text_to_speech(self, text, language='en'):
        """
        Convert text to speech and return the file path
        
        Args:
            text (str): Text to convert to speech
            language (str): Language code (e.g., 'en', 'fr', 'sw')
            
        Returns:
            str: Path to the generated audio file
        """
        if not text:
            return None
            
        file_path = self._get_file_path(text, language)
        
        # Check if file already exists
        if os.path.exists(file_path):
            return file_path
            
        try:
            # Convert text to speech
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(file_path)
            return file_path
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    def get_audio_url(self, text, language='en'):
        """
        Get the URL for the audio file
        
        Args:
            text (str): Text to convert to speech
            language (str): Language code
            
        Returns:
            str: URL to the audio file
        """
        file_path = self.text_to_speech(text, language)
        if not file_path:
            return None
            
        # Convert file path to URL
        media_url = settings.MEDIA_URL
        relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
        return f"{media_url}{relative_path}"
