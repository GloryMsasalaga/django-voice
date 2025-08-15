"""
This file contains the module to handle text-to-speech functionality
using gTTS (Google Text-to-Speech) to convert text to audio.
"""

import os
import re
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
    
    def _preprocess_text(self, text):
        """
        Preprocess text to improve TTS readability, especially for code blocks
        
        This function:
        1. Identifies code blocks and adds appropriate verbal cues
        2. Converts URLs to more readable formats
        3. Improves pronunciation of technical terms
        """
        if not text:
            return text
            
        # Process code blocks (both indented and fenced)
        # Match code blocks with ```...``` or indented with 4 spaces
        code_block_pattern = r'```.*?```|(?:(?:^|\n)[ ]{4}[^\n]+)+(?:\n|$)'
        
        def process_code_block(match):
            code = match.group(0)
            # Remove backticks or leading spaces
            if code.startswith('```') and code.endswith('```'):
                code = code[3:-3].strip()
            else:
                # Handle indented code by removing the 4 spaces at the beginning of each line
                code = re.sub(r'(?:^|\n)[ ]{4}', '\n', code).strip()
            
            # Add verbal cues for code block
            return f"Code block starts. {code} Code block ends."
        
        # Replace code blocks with verbalized versions
        text = re.sub(code_block_pattern, process_code_block, text, flags=re.DOTALL)
        
        # Process inline code (text between backticks)
        text = re.sub(r'`([^`]+)`', r'code: \1', text)
        
        # Make URLs more readable
        text = re.sub(r'https?://([^\s]+)', r'URL: \1', text)
        
        # Add verbal cues for common Django patterns
        text = re.sub(r'{% ([^%]+) %}', r'template tag: \1', text)
        text = re.sub(r'{{ ([^}]+) }}', r'template variable: \1', text)
        
        # Improve pronunciations of common Django terms
        replacements = {
            'django': 'jango',
            'urls.py': 'URLs dot py',
            'views.py': 'views dot py',
            'models.py': 'models dot py',
            'settings.py': 'settings dot py',
            'def ': 'function ',
            'class ': 'class definition ',
            '==': 'equals',
            '!=': 'not equals',
            '>=': 'greater than or equal to',
            '<=': 'less than or equal to',
            '->': 'returns',
            '=>': 'implies',
        }
        
        for pattern, replacement in replacements.items():
            text = text.replace(pattern, replacement)
            
        return text
    
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
            
        # Preprocess the text for better TTS
        processed_text = self._preprocess_text(text)
            
        file_path = self._get_file_path(text, language)
        
        # Check if file already exists
        if os.path.exists(file_path):
            return file_path
            
        try:
            # Convert text to speech
            tts = gTTS(text=processed_text, lang=language, slow=False)
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
