"""
Views for the docs app.
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from .models import DocumentationSection, LanguageTranslation
from .translation import TranslationService, SUPPORTED_LANGUAGES
from .tts import TextToSpeech
from .voice_commands import VoiceCommandProcessor
import os
import json
import re

def index(request):
    """Home page view"""
    # Get all unique URLs for documentation sections
    doc_urls = DocumentationSection.objects.values_list('url', flat=True).distinct()
    doc_pages = []
    
    for url in doc_urls:
        # Get the first section for each URL to use as page title
        first_section = DocumentationSection.objects.filter(url=url).order_by('id').first()
        if first_section:
            doc_pages.append({
                'url': url,
                'id': first_section.id,  # Use the ID of the first section for the page link
                'title': first_section.title,
                'section_count': DocumentationSection.objects.filter(url=url).count()
            })
    
    context = {
        'doc_pages': doc_pages,
        'languages': SUPPORTED_LANGUAGES
    }
    return render(request, 'docs/index.html', context)

def page_detail(request, page_id):
    """View for a specific documentation page"""
    # Get the page by ID
    page = get_object_or_404(DocumentationSection, id=page_id)
    
    # Get all sections from the same URL
    sections = DocumentationSection.objects.filter(url=page.url).order_by('id')
    
    # Get selected language (default to English)
    language = request.GET.get('lang', 'en')
    
    # Get translation service
    translation_service = TranslationService()
    
    # Prepare sections with translations
    translated_sections = []
    for section in sections:
        # Get translation if language is not English
        if language != 'en':
            translated_content = translation_service.get_or_create_translation(section, language)
        else:
            translated_content = section.content
            
        translated_sections.append({
            'id': section.id,
            'title': section.title,
            'content': translated_content,
            'level': section.section_level,
        })
    
    context = {
        'page': page,
        'sections': translated_sections,
        'languages': SUPPORTED_LANGUAGES,
        'selected_language': language
    }
    return render(request, 'docs/page_detail.html', context)

def section_detail(request, section_id):
    """View for a specific documentation section"""
    # Get the section
    section = get_object_or_404(DocumentationSection, id=section_id)
    
    # Get selected language (default to English)
    language = request.GET.get('lang', 'en')
    
    # Get translation service
    translation_service = TranslationService()
    
    # Get translation if language is not English
    if language != 'en':
        content = translation_service.get_or_create_translation(section, language)
    else:
        content = section.content
    
    # Process code blocks for better display
    content = process_code_blocks_for_display(content)
    
    # Get TTS service
    tts_service = TextToSpeech()
    
    # Get audio URL for the content
    audio_url = tts_service.get_audio_url(content, language)
    
    context = {
        'section': section,
        'content': content,
        'languages': SUPPORTED_LANGUAGES,
        'selected_language': language,
        'audio_url': audio_url
    }
    return render(request, 'docs/section_detail.html', context)

def process_code_blocks_for_display(content):
    """Process code blocks to ensure they display and read correctly"""
    # Process fenced code blocks
    content = re.sub(
        r'```(\w+)?\n(.*?)```',
        r'<div class="code-block"><div class="code-language">\1</div><pre><code>\2</code></pre></div>',
        content,
        flags=re.DOTALL
    )
    
    # Process indented code blocks (4 spaces at beginning of line)
    indented_pattern = r'(?:(?:^|\n)[ ]{4}[^\n]+)+(?:\n|$)'
    
    def replace_indented(match):
        code = match.group(0)
        # Remove the 4 spaces at the beginning of each line
        code = re.sub(r'(?:^|\n)[ ]{4}', '\n', code).strip()
        return f'<div class="code-block"><pre><code>{code}</code></pre></div>'
    
    content = re.sub(indented_pattern, replace_indented, content, flags=re.DOTALL)
    
    # Process inline code
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
    
    return content

@csrf_exempt
def get_audio(request):
    """API endpoint to get audio for text"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            language = data.get('language', 'en')
            
            # Validate language
            if language not in SUPPORTED_LANGUAGES:
                return JsonResponse({'error': 'Unsupported language'}, status=400)
            
            # Get TTS service
            tts_service = TextToSpeech()
            
            # Get audio URL
            audio_url = tts_service.get_audio_url(text, language)
            
            if audio_url:
                return JsonResponse({'audio_url': audio_url})
            else:
                return JsonResponse({'error': 'Failed to generate audio'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def process_voice_command(request):
    """API endpoint to process voice commands"""
    if request.method == 'POST':
        try:
            # Get command from request
            data = json.loads(request.body)
            command_text = data.get('command', '')
            
            if not command_text:
                return JsonResponse({'error': 'No command provided'}, status=400)
            
            # Process the command
            command_processor = VoiceCommandProcessor()
            result = command_processor.process_command(command_text)
            
            return JsonResponse(result)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def voice_interface(request):
    """View for voice command interface"""
    context = {
        'languages': SUPPORTED_LANGUAGES,
        'selected_language': 'en'
    }
    return render(request, 'docs/voice_interface.html', context)

def search(request):
    """Search documentation sections"""
    query = request.GET.get('q', '')
    language = request.GET.get('lang', 'en')
    
    if not query:
        return render(request, 'docs/search.html', {
            'query': query,
            'results': [],
            'languages': SUPPORTED_LANGUAGES,
            'selected_language': language
        })
    
    # Search in section titles and content
    results = DocumentationSection.objects.filter(
        language='en'  # Always search in English content
    ).filter(
        title__icontains=query
    ) | DocumentationSection.objects.filter(
        content__icontains=query
    )
    
    # Debug: Check if any results were found
    print(f"Search query: '{query}', Found {results.count()} results")
    
    # Get translation service if needed
    translation_service = None
    if language != 'en':
        translation_service = TranslationService()
    
    # Prepare results with translations if needed
    search_results = []
    for result in results:
        # Get translation if language is not English
        if language != 'en' and translation_service:
            content = translation_service.get_or_create_translation(result, language)
        else:
            content = result.content
            
        # Truncate content for preview
        if len(content) > 300:
            content = content[:300] + '...'
            
        search_results.append({
            'id': result.id,
            'title': result.title,
            'content': content,
            'url': result.url
        })
    
    context = {
        'query': query,
        'results': search_results,
        'result_count': len(search_results),
        'languages': SUPPORTED_LANGUAGES,
        'selected_language': language
    }
    return render(request, 'docs/search.html', context)
