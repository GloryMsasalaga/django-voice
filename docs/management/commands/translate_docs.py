"""
This management command allows scheduling translation of documentation sections
to keep translations updated in the database.
"""

from django.core.management.base import BaseCommand
from docs.models import DocumentationSection, LanguageTranslation
from docs.translation import TranslationService, SUPPORTED_LANGUAGES
import time

class Command(BaseCommand):
    help = 'Translate documentation sections to supported languages'

    def add_arguments(self, parser):
        parser.add_argument('--language', type=str, help='Specific language to translate to (e.g., sw, fr)')
        parser.add_argument('--force', action='store_true', help='Force update of existing translations')

    def handle(self, *args, **options):
        language = options.get('language')
        force_update = options.get('force', False)
        
        # Get translation service
        translation_service = TranslationService()
        
        # Get languages to translate to
        languages_to_translate = []
        if language and language in SUPPORTED_LANGUAGES and language != 'en':
            languages_to_translate = [language]
        else:
            # All languages except English
            languages_to_translate = [lang for lang in SUPPORTED_LANGUAGES.keys() if lang != 'en']
        
        # Get sections to translate
        sections = DocumentationSection.objects.filter(language='en')
        total_sections = sections.count()
        total_languages = len(languages_to_translate)
        
        self.stdout.write(f"Translating {total_sections} sections to {total_languages} languages")
        
        # Count translations to perform
        translated_count = 0
        skipped_count = 0
        
        # Translate each section to each language
        for section in sections:
            for lang in languages_to_translate:
                # Check if translation already exists
                existing = LanguageTranslation.objects.filter(
                    section=section,
                    language=lang
                ).first()
                
                if existing and not force_update:
                    self.stdout.write(f"Skipping existing translation for {section.title} [{lang}]")
                    skipped_count += 1
                    continue
                
                # Translate content
                self.stdout.write(f"Translating section '{section.title}' to {SUPPORTED_LANGUAGES[lang]}")
                
                translated_content = translation_service.translate_text(section.content, lang)
                
                if existing:
                    # Update existing translation
                    existing.translated_content = translated_content
                    existing.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated translation for {section.title} [{lang}]"))
                else:
                    # Create new translation
                    LanguageTranslation.objects.create(
                        section=section,
                        language=lang,
                        translated_content=translated_content
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created translation for {section.title} [{lang}]"))
                
                translated_count += 1
                
                # Be nice to the translation API
                time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS(
            f"Translation completed: {translated_count} translations created/updated, {skipped_count} skipped"
        ))
