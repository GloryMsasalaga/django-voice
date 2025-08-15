from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
import time
import os
import json
from django.conf import settings
from docs.models import DocumentationSection
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Scrape specific Django documentation pages and store sections in the database'

    def add_arguments(self, parser):
        parser.add_argument('--urls', nargs='+', type=str, help='Specific URLs to scrape')
        parser.add_argument('--cache', action='store_true', help='Use cached results if available')
        parser.add_argument('--flush-cache', action='store_true', help='Force refresh cache')

    def handle(self, *args, **options):
        urls = options.get('urls', [])
        use_cache = options.get('cache', True)
        flush_cache = options.get('flush_cache', False)
        
        if not urls:
            # Default URLs if none provided
            urls = [
                'https://docs.djangoproject.com/en/5.2/',  # Main documentation page
                'https://docs.djangoproject.com/en/5.2/intro/overview/',
                'https://docs.djangoproject.com/en/5.2/topics/db/models/',
                'https://docs.djangoproject.com/en/5.2/topics/http/views/',
                'https://docs.djangoproject.com/en/5.2/topics/templates/',
                'https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/',
                'https://docs.djangoproject.com/en/5.2/topics/i18n/translation/',
                'https://docs.djangoproject.com/en/5.2/ref/settings/',
            ]
        
        for url in urls:
            self.stdout.write(f"Scraping: {url}")
            
            # Check cache first if enabled
            cache_key = f"django_docs_{url.replace('/', '_')}"
            
            if flush_cache:
                cache.delete(cache_key)
                
            cached_data = None
            if use_cache:
                cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                self.stdout.write(f"Using cached data for {url}")
                sections = cached_data
            else:
                # Scrape the page
                sections = self.scrape_page(url)
                
                # Store in cache for 7 days
                cache.set(cache_key, sections, 60 * 60 * 24 * 7)
            
            # Store in database
            self.store_sections(url, sections)
            
            # Be nice to Django's servers
            time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS('Successfully scraped documentation'))

    def scrape_page(self, url):
        headers = {
            'User-Agent': 'DjangoVoiceAssistant/1.0 (Educational Project)',
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch {url}: {response.status_code}"))
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get the page title from the title tag
        title_tag = soup.find('title')
        page_title = title_tag.get_text().strip() if title_tag else "Django Documentation"
        
        # Debug HTML structure
        self.stdout.write(f"HTML title: {page_title}")
        
        # Find the main content div - try different selectors used in Django docs
        content_div = None
        possible_selectors = [
            ('div', {'id': 'content'}),
            ('div', {'class_': 'document'}),
            ('main', {}),  # Try the main tag
            ('article', {}),  # Try article tag
            ('div', {'class_': 'container'}),
            ('div', {'role': 'main'})
        ]
        
        for tag, attrs in possible_selectors:
            content_div = soup.find(tag, **attrs)
            if content_div:
                self.stdout.write(f"Found content using selector: {tag}, {attrs}")
                break
        
        if not content_div:
            self.stdout.write(self.style.WARNING(f"Could not find content div in {url}"))
            # Fallback to body
            content_div = soup.find('body')
            if content_div:
                self.stdout.write("Using body as fallback")
            else:
                return []
        
        sections = []
        
        # Add the page title as the first section
        current_section = {'title': page_title, 'content': '', 'level': 'h1'}
        
        # Find all headings in the content
        headings = content_div.find_all(['h1', 'h2', 'h3', 'h4'])
        self.stdout.write(f"Found {len(headings)} headings")
        
        # If no headings found, just use the page title and get some content
        if not headings:
            # Extract some content for the main page
            paragraphs = content_div.find_all(['p', 'pre', 'ul', 'ol'])
            self.stdout.write(f"No headings found, using {len(paragraphs)} paragraphs for content")
            
            for p in paragraphs[:10]:  # Get first few paragraphs as content
                if 'class' in p.attrs and any(c in ['breadcrumbs', 'contents', 'footer', 'navigation'] 
                                             for c in p.get('class', [])):
                    continue
                
                if p.name == 'pre':
                    current_section['content'] += f"\n```\n{p.get_text()}\n```\n"
                elif p.name in ['ul', 'ol']:
                    items = [f"- {li.get_text().strip()}" for li in p.find_all('li')]
                    current_section['content'] += "\n" + "\n".join(items) + "\n"
                else:
                    current_section['content'] += "\n" + p.get_text().strip() + "\n"
            
            sections.append(current_section)
            return sections
        
        # Process each heading and its content
        for i, heading in enumerate(headings):
            # Save previous section if it exists
            if current_section['title'] and current_section != {'title': page_title, 'content': '', 'level': 'h1'}:
                sections.append(current_section)
            
            # Start new section
            current_section = {
                'title': heading.get_text().strip(),
                'content': '',
                'level': heading.name  # h1, h2, h3, etc.
            }
            
            self.stdout.write(f"Processing heading: {current_section['title']}")
            
            # Get content until next heading
            next_elements = []
            next_element = heading.next_sibling
            
            # Collect elements until next heading or end of content
            while next_element and (not hasattr(next_element, 'name') or next_element.name not in ['h1', 'h2', 'h3', 'h4']):
                if hasattr(next_element, 'name') and next_element.name:
                    next_elements.append(next_element)
                next_element = next_element.next_sibling
            
            # Process collected elements
            for element in next_elements:
                # Skip navigation and irrelevant elements
                if 'class' in element.attrs and any(c in ['breadcrumbs', 'contents', 'footer', 'navigation'] 
                                                 for c in element.get('class', [])):
                    continue
                
                # For code blocks
                if element.name == 'pre':
                    current_section['content'] += f"\n```\n{element.get_text()}\n```\n"
                # For lists
                elif element.name in ['ul', 'ol']:
                    items = [f"- {li.get_text().strip()}" for li in element.find_all('li')]
                    current_section['content'] += "\n" + "\n".join(items) + "\n"
                # Regular paragraphs and other content elements
                elif element.name in ['p', 'div', 'section', 'article']:
                    current_section['content'] += "\n" + element.get_text().strip() + "\n"
        
        # Add the last section
        if current_section['title']:
            sections.append(current_section)
        
        return sections

    def store_sections(self, url, sections):
        for section in sections:
            doc_section, created = DocumentationSection.objects.update_or_create(
                title=section['title'],
                url=url,
                section_level=section['level'],
                defaults={
                    'content': section['content'].strip(),
                    'language': 'en'  # Default language is English
                }
            )
            
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} section: {section['title']}")
