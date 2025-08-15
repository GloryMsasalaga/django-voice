
from django.db import models

class DocumentationSection(models.Model):
	title = models.CharField(max_length=255)
	content = models.TextField()
	language = models.CharField(max_length=10, default='en')
	url = models.URLField()
	section_level = models.CharField(max_length=2)  # h1, h2, h3
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.title} ({self.language})"

class LanguageTranslation(models.Model):
	section = models.ForeignKey(DocumentationSection, on_delete=models.CASCADE, related_name='translations')
	language = models.CharField(max_length=10)
	translated_content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.section.title} [{self.language}]"

# Create your models here.
