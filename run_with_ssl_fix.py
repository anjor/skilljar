#!/usr/bin/env python3
"""
SSL-friendly version of the Skilljar downloader for corporate environments
"""

import ssl
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings and verification for corporate environments
urllib3.disable_warnings(InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Now import and run the main script
from skilljar_lesson_downloader import main

if __name__ == "__main__":
    main()