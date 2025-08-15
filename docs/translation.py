"""
This file contains the module to handle translation functionality
using third-party translation APIs.
"""

import requests
from django.conf import settings
from docs.models import DocumentationSection, LanguageTranslation
import time
import os
import json
import google.generativeai as genai
from googletrans import Translator

# Support these languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'sw': 'Swahili',
    'fr': 'French'
}

class TranslationService:
    """Service to translate documentation content"""
    
    def __init__(self, use_gemini=True):
        """Initialize translation service"""
        self.use_gemini = use_gemini
        
        if use_gemini:
            # Initialize Gemini API
            gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            # Fallback to googletrans
            self.translator = Translator()
    
    def translate_text(self, text, target_language):
        """Translate text to target language"""
        if not text or not target_language:
            return text
            
        if target_language == 'en':
            return text  # No need to translate English source
            
        if self.use_gemini:
            try:
                # Format prompt for Gemini
                prompt = f"Translate the following text from English to {SUPPORTED_LANGUAGES[target_language]}. Preserve all formatting, code blocks, and technical terms. Here's the text:\n\n{text}"
                
                # Generate translation with Gemini
                response = self.model.generate_content(prompt)
                
                if hasattr(response, 'text'):
                    return response.text
                return text
            except Exception as e:
                print(f"Gemini translation error: {e}")
                # Fallback to googletrans if Gemini fails
                try:
                    translator = Translator()
                    result = translator.translate(text, dest=target_language)
                    return result.text
                except Exception as e2:
                    print(f"Fallback translation error: {e2}")
                    return text
        else:
            # Use googletrans
            try:
                result = self.translator.translate(text, dest=target_language)
                return result.text
            except Exception as e:
                print(f"Google translation error: {e}")
                return text
    
    def translate_section(self, section_id, target_language):
        """Translate a specific documentation section"""
        try:
            section = DocumentationSection.objects.get(id=section_id)
            
            # Check if translation already exists
            existing = LanguageTranslation.objects.filter(
                section=section,
                language=target_language
            ).first()
            
            if existing:
                return existing
            
            # Translate content
            translated_content = self.translate_text(section.content, target_language)
            
            # Store in database
            translation = LanguageTranslation.objects.create(
                section=section,
                language=target_language,
                translated_content=translated_content
            )
            
            return translation
            
        except DocumentationSection.DoesNotExist:
            print(f"Section with ID {section_id} not found")
            return None
        except Exception as e:
            print(f"Translation error: {e}")
            return None
    
    def get_or_create_translation(self, section, target_language):
        """Get existing translation or create new one if it doesn't exist"""
        try:
            # Try to get existing translation
            translation = LanguageTranslation.objects.filter(
                section=section,
                language=target_language
            ).first()
            
            if translation:
                return translation.translated_content
            
            # Create new translation
            translated_content = self.translate_text(section.content, target_language)
            
            # Store in database
            LanguageTranslation.objects.create(
                section=section,
                language=target_language,
                translated_content=translated_content
            )
            
            return translated_content
            
        except Exception as e:
            print(f"Translation error: {e}")
            return section.content  # Return original content if translation fails
