# Skilljar Lesson Downloader

A Python script to download all lessons from specified Skilljar courses using the Skilljar API.

## Setup

1. Install dependencies:
   ```bash
   # Option 1: Using uv (recommended)
   uv install
   
   # Option 2: Using pip (for corporate environments with SSL issues)
   pip install -r requirements.txt
   ```

2. Set up your API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your Skilljar API key
   ```

## Usage

Download lessons from one or more courses:

```bash
# Using environment variable (recommended)
python skilljar_lesson_downloader.py --course-ids COURSE_ID_1 COURSE_ID_2

# Using command line argument
python skilljar_lesson_downloader.py --api-key YOUR_API_KEY --course-ids COURSE_ID_1 COURSE_ID_2

# Specify custom output directory
python skilljar_lesson_downloader.py --course-ids COURSE_ID_1 --output-dir my_downloads
```

### Corporate Environment / SSL Issues

If you're in a corporate environment with SSL certificate issues:

```bash
# Option 1: Install with pip instead of uv
pip install -r requirements.txt
python skilljar_lesson_downloader.py --course-ids COURSE_ID_1 COURSE_ID_2

# Option 2: Use the SSL-friendly wrapper
python run_with_ssl_fix.py --course-ids COURSE_ID_1 COURSE_ID_2

# Option 3: Configure uv to ignore SSL (if you want to keep using uv)
uv pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org
uv run skilljar_lesson_downloader.py --course-ids COURSE_ID_1 COURSE_ID_2
```

This version disables SSL verification which is sometimes necessary in corporate environments with intercepting proxies.

## Output Structure

The script creates the following directory structure:

```
downloads/
├── course_COURSE_ID_1/
│   ├── Lesson_Title_1_LESSON_ID/
│   │   ├── lesson_metadata.json
│   │   ├── content_items.json
│   │   └── content_0.mp4
│   └── Lesson_Title_2_LESSON_ID/
│       ├── lesson_metadata.json
│       └── content_items.json
└── course_COURSE_ID_2/
    └── ...
```

## Features

- Downloads lesson metadata and content items
- Attempts to download actual content files (videos, PDFs, etc.)
- Rate limiting to be respectful to the API
- Error handling for failed downloads
- Progress tracking
- Configurable output directory