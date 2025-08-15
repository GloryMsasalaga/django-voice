
from django.contrib import admin
from .models import DocumentationSection, LanguageTranslation

@admin.register(DocumentationSection)
class DocumentationSectionAdmin(admin.ModelAdmin):
	list_display = ('title', 'language', 'section_level', 'url', 'updated_at')
	search_fields = ('title', 'content')

@admin.register(LanguageTranslation)
class LanguageTranslationAdmin(admin.ModelAdmin):
	list_display = ('section', 'language', 'updated_at')
	search_fields = ('translated_content',)

# Register your models here.
