"""
Voice command recognition and processing for the Django Voice Assistant
"""

import re
import speech_recognition as sr
from django.db.models import Q
from .models import DocumentationSection
from .tts import TextToSpeech
from .translation import TranslationService, SUPPORTED_LANGUAGES

class VoiceCommandProcessor:
    """Process voice commands for the Django Voice Assistant"""
    
    # Command patterns
    COMMAND_PATTERNS = [
        # Format: (regex pattern, command_handler_method_name)
        (r'(kibena|cybena|key\s*bena)\s+read\s+(.+)', 'handle_read_command'),
        (r'(kibena|cybena|key\s*bena)\s+search\s+(.+)', 'handle_search_command'),
        (r'(kibena|cybena|key\s*bena)\s+translate\s+to\s+(\w+)\s+(.+)', 'handle_translate_command'),
        (r'(kibena|cybena|key\s*bena)\s+help', 'handle_help_command'),
    ]
    
    def __init__(self):
        """Initialize voice command processor"""
        self.recognizer = sr.Recognizer()
        self.tts_service = TextToSpeech()
        self.translation_service = TranslationService()
    
    def listen_for_command(self):
        """Listen for voice command using microphone"""
        with sr.Microphone() as source:
            print("Listening for voice command...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
            
        try:
            # Recognize speech using Google Speech Recognition
            command = self.recognizer.recognize_google(audio)
            print(f"Command recognized: {command}")
            return command.lower()
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None
    
    def process_command(self, command_text):
        """Process recognized command text"""
        if not command_text:
            return {
                'success': False,
                'message': 'No command recognized',
                'response': None
            }
            
        # Check command against patterns
        for pattern, handler_name in self.COMMAND_PATTERNS:
            match = re.match(pattern, command_text, re.IGNORECASE)
            if match:
                # Call the appropriate handler method
                handler = getattr(self, handler_name)
                return handler(*match.groups())
                
        # No matching pattern found
        return {
            'success': False,
            'message': 'Unknown command',
            'response': f"I'm sorry, I didn't understand the command: {command_text}"
        }
    
    def handle_read_command(self, trigger_word, topic):
        """Handle 'read' commands"""
        print(f"Processing read command for topic: {topic}")
        
        # Search for the topic in documentation
        sections = DocumentationSection.objects.filter(
            Q(title__icontains=topic) | Q(content__icontains=topic)
        ).order_by('id')[:1]
        
        if sections.exists():
            section = sections.first()
            # Get audio URL for the content
            audio_url = self.tts_service.get_audio_url(section.content, 'en')
            
            return {
                'success': True,
                'message': f"Reading about {topic}",
                'response': section.content,
                'audio_url': audio_url,
                'section_id': section.id
            }
        else:
            return {
                'success': False,
                'message': f"Could not find documentation about {topic}",
                'response': f"I'm sorry, I couldn't find any information about {topic}."
            }
    
    def handle_search_command(self, trigger_word, query):
        """Handle 'search' commands"""
        print(f"Processing search command for query: {query}")
        
        # Search for the query in documentation
        sections = DocumentationSection.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('id')[:5]
        
        if sections.exists():
            results = []
            for section in sections:
                results.append({
                    'id': section.id,
                    'title': section.title,
                    'url': section.url
                })
                
            return {
                'success': True,
                'message': f"Found {sections.count()} results for {query}",
                'response': results
            }
        else:
            return {
                'success': False,
                'message': f"No results found for {query}",
                'response': f"I'm sorry, I couldn't find any information about {query}."
            }
    
    def handle_translate_command(self, trigger_word, language, topic):
        """Handle 'translate' commands"""
        print(f"Processing translate command for language: {language}, topic: {topic}")
        
        # Map spoken language name to language code
        language_code = None
        for code, name in SUPPORTED_LANGUAGES.items():
            if name.lower() == language.lower():
                language_code = code
                break
        
        if not language_code:
            return {
                'success': False,
                'message': f"Unsupported language: {language}",
                'response': f"I'm sorry, {language} is not supported for translation."
            }
            
        # Search for the topic in documentation
        sections = DocumentationSection.objects.filter(
            Q(title__icontains=topic) | Q(content__icontains=topic)
        ).order_by('id')[:1]
        
        if sections.exists():
            section = sections.first()
            
            # Get translation
            translated_content = self.translation_service.get_or_create_translation(
                section, language_code
            )
            
            # Get audio URL for the translated content
            audio_url = self.tts_service.get_audio_url(translated_content, language_code)
            
            return {
                'success': True,
                'message': f"Translated content about {topic} to {language}",
                'response': translated_content,
                'audio_url': audio_url,
                'section_id': section.id,
                'language': language_code
            }
        else:
            return {
                'success': False,
                'message': f"Could not find documentation about {topic}",
                'response': f"I'm sorry, I couldn't find any information about {topic}."
            }
    
    def handle_help_command(self, trigger_word):
        """Handle 'help' command"""
        help_text = """
        Available commands:
        - "Kibena read [topic]" - Read documentation about a topic
        - "Kibena search [query]" - Search the documentation for a query
        - "Kibena translate to [language] [topic]" - Translate and read documentation in another language
        - "Kibena help" - Show this help message
        """
        
        return {
            'success': True,
            'message': "Help command",
            'response': help_text
        }
