"""
This file contains the module to handle translation functionality
using third-party translation APIs.
"""

import re
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
    'fr': 'French',
    'es': 'Spanish',
    'de': 'German',
    'zh': 'Chinese',
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
    
    def _extract_code_blocks(self, text):
        """
        Extract code blocks from text to protect them during translation
        
        Returns:
            tuple: (text with placeholders, dictionary of code blocks)
        """
        code_blocks = {}
        
        # Find code blocks with ```...```
        fenced_pattern = r'```(?:\w+)?\n(.*?)```'
        
        def replace_fenced(match):
            block_id = f"CODE_BLOCK_{len(code_blocks)}"
            code_blocks[block_id] = match.group(0)
            return block_id
            
        text = re.sub(fenced_pattern, replace_fenced, text, flags=re.DOTALL)
        
        # Find indented code blocks (4 spaces at beginning of line)
        indented_pattern = r'(?:(?:^|\n)[ ]{4}[^\n]+)+(?:\n|$)'
        
        def replace_indented(match):
            block_id = f"CODE_BLOCK_{len(code_blocks)}"
            code_blocks[block_id] = match.group(0)
            return block_id
            
        text = re.sub(indented_pattern, replace_indented, text, flags=re.DOTALL)
        
        # Find inline code with backticks
        inline_pattern = r'`([^`]+)`'
        
        def replace_inline(match):
            block_id = f"INLINE_CODE_{len(code_blocks)}"
            code_blocks[block_id] = match.group(0)
            return block_id
            
        text = re.sub(inline_pattern, replace_inline, text)
        
        return text, code_blocks
    
    def _restore_code_blocks(self, text, code_blocks):
        """Restore code blocks in translated text"""
        for block_id, block_content in code_blocks.items():
            text = text.replace(block_id, block_content)
        return text
    
    def translate_text(self, text, target_language):
        """Translate text to target language"""
        if not text or not target_language:
            return text
            
        if target_language == 'en':
            return text  # No need to translate English source
        
        # Extract code blocks to protect them during translation
        text_with_placeholders, code_blocks = self._extract_code_blocks(text)
            
        translated_text = ""
        if self.use_gemini:
            try:
                # Format prompt for Gemini
                prompt = f"""Translate the following text from English to {SUPPORTED_LANGUAGES[target_language]}.
                DO NOT translate the text inside CODE_BLOCK_X or INLINE_CODE_X placeholders - leave those exactly as they are.
                Preserve all formatting, technical terms, and placeholder tokens.
                Here's the text to translate:
                
                {text_with_placeholders}"""
                
                # Generate translation with Gemini
                response = self.model.generate_content(prompt)
                
                if hasattr(response, 'text'):
                    translated_text = response.text
                else:
                    translated_text = text_with_placeholders  # Fallback to original
            except Exception as e:
                print(f"Gemini translation error: {e}")
                # Fallback to googletrans if Gemini fails
                try:
                    translator = Translator()
                    result = translator.translate(text_with_placeholders, dest=target_language)
                    translated_text = result.text
                except Exception as e2:
                    print(f"Fallback translation error: {e2}")
                    translated_text = text_with_placeholders  # Return original with placeholders
        else:
            # Use googletrans
            try:
                result = self.translator.translate(text_with_placeholders, dest=target_language)
                translated_text = result.text
            except Exception as e:
                print(f"Google translation error: {e}")
                translated_text = text_with_placeholders  # Return original with placeholders
        
        # Restore code blocks in the translated text
        return self._restore_code_blocks(translated_text, code_blocks)
    
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
