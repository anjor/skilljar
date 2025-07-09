#!/usr/bin/env python3
"""
Skilljar Lesson Downloader

This script downloads all lessons from specified Skilljar courses using the Skilljar API.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any
import argparse
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import re
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Load environment variables
load_dotenv()

# Disable SSL warnings for corporate environments
urllib3.disable_warnings(InsecureRequestWarning)


class SkilljarDownloader:
    """Downloads lessons from Skilljar courses."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.skilljar.com"):
        """
        Initialize the Skilljar downloader.
        
        Args:
            api_key: Skilljar API key
            base_url: Base URL for the Skilljar API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = (api_key, '')  # Basic auth with API key as username, empty password
        self.session.verify = False  # Disable SSL verification for corporate environments
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the Skilljar API with error handling."""
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            raise
    
    def _get_paginated_results(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """Get all results from a paginated endpoint."""
        all_results = []
        page = 1
        
        while True:
            current_params = params.copy() if params else {}
            current_params['page'] = page
            
            response = self._make_request('GET', endpoint, params=current_params)
            data = response.json()
            
            # Handle different response formats
            if 'results' in data:
                results = data['results']
                has_next = data.get('next') is not None
            elif isinstance(data, list):
                results = data
                has_next = False
            else:
                results = [data]
                has_next = False
            
            all_results.extend(results)
            
            if not has_next or not results:
                break
                
            page += 1
            time.sleep(0.1)  # Rate limiting
            
        return all_results
    
    def get_course_lessons(self, course_id: str) -> List[Dict]:
        """Get all lessons for a specific course."""
        print(f"Fetching lessons for course {course_id}...")
        
        # Use the correct endpoint with course_id parameter
        endpoint = '/v1/lessons'
        params = {'course_id': course_id}
        
        try:
            return self._get_paginated_results(endpoint, params)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Could not fetch lessons for course {course_id}: {e}")
    
    def get_lesson_details(self, lesson_id: str) -> Dict:
        """Get detailed information about a specific lesson."""
        endpoint = f'/v1/lessons/{lesson_id}'
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def get_lesson_content(self, lesson_id: str) -> List[Dict]:
        """Get content items for a specific lesson."""
        endpoint = f'/v1/lessons/{lesson_id}/content-items'
        try:
            return self._get_paginated_results(endpoint)
        except requests.exceptions.RequestException:
            print(f"Warning: Could not fetch content items for lesson {lesson_id}")
            return []
    
    def _extract_urls_from_html(self, html_content: str) -> List[str]:
        """Extract image and asset URLs from HTML content."""
        if not html_content:
            return []
        
        # Pattern to match src attributes in img, video, audio, source, and embed tags
        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<video[^>]+src=["\']([^"\']+)["\']',
            r'<audio[^>]+src=["\']([^"\']+)["\']',
            r'<source[^>]+src=["\']([^"\']+)["\']',
            r'<embed[^>]+src=["\']([^"\']+)["\']',
            r'<iframe[^>]+src=["\']([^"\']+)["\']',
            # Also look for href attributes in links to PDFs, docs, etc.
            r'<a[^>]+href=["\']([^"\']+\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar))["\']',
        ]
        
        urls = []
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            urls.extend(matches)
        
        # Filter out relative URLs and invalid URLs
        valid_urls = []
        for url in urls:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
        
        return valid_urls

    def download_lesson_content(self, lesson: Dict, output_dir: Path) -> None:
        """Download content for a specific lesson."""
        lesson_id = lesson['id']
        lesson_title = lesson.get('title', f'Lesson_{lesson_id}')
        
        # Create safe filename
        safe_title = "".join(c for c in lesson_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        lesson_dir = output_dir / f"{safe_title}_{lesson_id}"
        lesson_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  Downloading lesson: {lesson_title}")
        
        # Save lesson metadata
        lesson_details = self.get_lesson_details(lesson_id)
        metadata_file = lesson_dir / 'lesson_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(lesson_details, f, indent=2, ensure_ascii=False)
        
        # Get and save content items
        content_items = self.get_lesson_content(lesson_id)
        if content_items:
            content_file = lesson_dir / 'content_items.json'
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content_items, f, indent=2, ensure_ascii=False)
        
        # Download direct content files if URLs are provided
        for i, content_item in enumerate(content_items):
            if 'url' in content_item or 'file_url' in content_item:
                file_url = content_item.get('url') or content_item.get('file_url')
                if file_url:
                    self._download_file(file_url, lesson_dir, f"content_{i}")
        
        # Extract and download assets from HTML content
        asset_counter = 0
        for i, content_item in enumerate(content_items):
            html_content = content_item.get('content_html', '')
            if html_content:
                urls = self._extract_urls_from_html(html_content)
                for url in urls:
                    try:
                        # Create a descriptive filename
                        parsed_url = urlparse(url)
                        original_filename = Path(parsed_url.path).name
                        if original_filename:
                            filename_prefix = f"asset_{asset_counter}_{original_filename}"
                        else:
                            filename_prefix = f"asset_{asset_counter}"
                        
                        self._download_file(url, lesson_dir, filename_prefix, use_extension=False)
                        asset_counter += 1
                    except Exception as e:
                        print(f"    Failed to download asset {url}: {e}")
        
        time.sleep(0.2)  # Rate limiting
    
    def _download_file(self, url: str, output_dir: Path, filename_prefix: str, use_extension: bool = True) -> None:
        """Download a file from a URL."""
        try:
            response = requests.get(url, stream=True, verify=False)
            response.raise_for_status()
            
            # Determine filename
            if use_extension:
                # Try to determine file extension from URL or content type
                file_extension = ""
                if '.' in url.split('/')[-1]:
                    file_extension = '.' + url.split('/')[-1].split('.')[-1]
                elif 'content-type' in response.headers:
                    content_type = response.headers['content-type'].lower()
                    if 'video' in content_type:
                        file_extension = '.mp4'
                    elif 'pdf' in content_type:
                        file_extension = '.pdf'
                    elif 'image' in content_type:
                        file_extension = '.jpg'
                
                filename = f"{filename_prefix}{file_extension}"
            else:
                # Use the filename_prefix as-is (it already contains the extension)
                filename = filename_prefix
            
            filepath = output_dir / filename
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"    Downloaded: {filename}")
            
        except Exception as e:
            print(f"    Error downloading {url}: {e}")
    
    def download_courses(self, course_ids: List[str], output_dir: str = "downloads") -> None:
        """Download all lessons from the specified courses."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for course_id in course_ids:
            print(f"\nProcessing course: {course_id}")
            
            try:
                # Create course directory
                course_dir = output_path / f"course_{course_id}"
                course_dir.mkdir(parents=True, exist_ok=True)
                
                # Get lessons for this course
                lessons = self.get_course_lessons(course_id)
                
                if not lessons:
                    print(f"  No lessons found for course {course_id}")
                    continue
                
                print(f"  Found {len(lessons)} lessons")
                
                # Download each lesson
                for lesson in lessons:
                    self.download_lesson_content(lesson, course_dir)
                
                print(f"  Completed course {course_id}")
                
            except Exception as e:
                print(f"  Error processing course {course_id}: {e}")
                continue


def main():
    """Main function to run the downloader."""
    parser = argparse.ArgumentParser(description='Download lessons from Skilljar courses')
    parser.add_argument('--api-key', help='Skilljar API key (can also be set via SKILLJAR_API_KEY env variable)')
    parser.add_argument('--course-ids', required=True, nargs='+', help='List of course IDs to download')
    parser.add_argument('--output-dir', default='downloads', help='Output directory for downloads')
    parser.add_argument('--base-url', default='https://api.skilljar.com', help='Base URL for Skilljar API')
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.getenv('SKILLJAR_API_KEY')
    if not api_key:
        print("Error: API key must be provided via --api-key argument or SKILLJAR_API_KEY environment variable")
        exit(1)
    
    # Initialize downloader
    downloader = SkilljarDownloader(api_key, args.base_url)
    
    # Start downloading
    print(f"Starting download of {len(args.course_ids)} courses...")
    downloader.download_courses(args.course_ids, args.output_dir)
    print("\nDownload completed!")


if __name__ == "__main__":
    main()