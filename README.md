# Django Voice Assistant for Documentation

This project scrapes the official Django documentation, stores it in PostgreSQL, translates content, and provides a multilingual voice assistant interface.

## Features
- Scrapes Django docs and stores by section (h1, h2, h3)
- Weekly auto-update via scheduled job
- Caching to avoid repeated requests
- PostgreSQL backend
- Translates docs to English, Swahili, French
- Multilingual text-to-speech (TTS) with gTTS
- Web UI: search, language selector, play audio
- Attribution to Django docs (BSD license)

## Setup
1. Create a Python virtual environment and activate it:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
2. Install dependencies:
   ```powershell
   pip install django requests beautifulsoup4 psycopg2-binary gTTS
   ```
3. Configure PostgreSQL in `djvoice/settings.py`.
4. Run migrations:
   ```powershell
   python manage.py migrate
   ```
5. Start the server:
   ```powershell
   python manage.py runserver
   ```

## Attribution
Content sourced from the official Django documentation. BSD license applies.

---
