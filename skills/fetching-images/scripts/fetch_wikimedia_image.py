#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Fetch images from multiple providers with a unified CLI.

Usage:
    uv run ./fetch_wikimedia_image.py [args]
    uv run ./fetch_wikimedia_image.py "topic" [--count 5] [--source wikimedia] [--type photo] [--json]
    uv run ./fetch_wikimedia_image.py --file-page URL [--verify] [--html]

Examples:
    # Search Wikimedia and get URLs directly
    uv run ./fetch_wikimedia_image.py "mofongo puerto rico" --count 3

    # Search Unsplash vectors/icons/photos (requires UNSPLASH_ACCESS_KEY)
    uv run ./fetch_wikimedia_image.py "rocket" --source unsplash --type vector --count 10

    # Search with JSON output
    uv run ./fetch_wikimedia_image.py "Old San Juan street" --json

    # Get URL from specific File: page
    uv run ./fetch_wikimedia_image.py --file-page "https://commons.wikimedia.org/wiki/File:Mofongo.jpg" --verify --html
"""

import sys
import json
import re
import urllib.request
import urllib.parse
import os
from typing import List, Dict, Optional

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
UNSPLASH_API = "https://api.unsplash.com/search/photos"
PEXELS_API = "https://api.pexels.com/v1/search"
PIXABAY_API = "https://pixabay.com/api/"
# Wikimedia API requires a descriptive User-Agent per their policy
# See: https://www.mediawiki.org/wiki/API:Etiquette
USER_AGENT = "WikimediaImageFetcher/1.0 (ClaudeCode-Plugin; fuchengwarrenzhu@gmail.com)"


def make_json_request(url: str, headers: Optional[Dict[str, str]] = None) -> dict:
    """Make a JSON request with optional headers."""
    req = urllib.request.Request(url)
    req.add_header('User-Agent', USER_AGENT)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())

def make_api_request(url: str) -> dict:
    """Make a request to the Wikimedia API with proper headers."""
    return make_json_request(url)


def normalize_image_type(image_type: str) -> str:
    normalized = image_type.lower().strip()
    if normalized not in {"photo", "icon", "vector", "any"}:
        raise ValueError(f"Invalid --type value: {image_type}. Use photo|icon|vector|any")
    return normalized


def filter_by_type(images: List[Dict[str, str]], image_type: str) -> List[Dict[str, str]]:
    """Filter normalized image rows by requested type."""
    if image_type == "any":
        return images

    filtered = []
    for img in images:
        mime = (img.get("mime") or "").lower()
        filename = (img.get("filename") or "").lower()
        title = (img.get("title") or "").lower()
        marker = f"{filename} {title}"

        if image_type == "photo":
            if mime in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
                filtered.append(img)
        elif image_type == "vector":
            if mime in {"image/svg+xml", "application/svg+xml"} or filename.endswith('.svg'):
                filtered.append(img)
        elif image_type == "icon":
            if (
                "icon" in marker
                or mime in {"image/svg+xml", "application/svg+xml"}
                or filename.endswith('.svg')
            ):
                filtered.append(img)

    return filtered


def search_wikimedia(topic: str, count: int = 5) -> List[Dict[str, str]]:
    """
    Search Wikimedia Commons for images using the API.
    Returns list of dicts with title, file_page, and direct_url.
    """
    print(f"🔍 Searching Wikimedia Commons for: {topic}")
    print(f"   Looking for top {count} results...\n")

    # Step 1: Search for files
    search_params = {
        'action': 'query',
        'list': 'search',
        'srsearch': topic,
        'srnamespace': '6',  # File namespace
        'srlimit': str(count),
        'format': 'json'
    }

    search_url = f"{WIKIMEDIA_API}?{urllib.parse.urlencode(search_params)}"

    try:
        search_data = make_api_request(search_url)
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []

    if 'query' not in search_data or 'search' not in search_data['query']:
        print("❌ No results found")
        return []

    results = search_data['query']['search']

    if not results:
        print("❌ No results found")
        return []

    print(f"📋 Found {len(results)} results\n")

    # Step 2: Get image URLs for each result
    titles = '|'.join([r['title'] for r in results])

    info_params = {
        'action': 'query',
        'titles': titles,
        'prop': 'imageinfo',
        'iiprop': 'url|size|mime',
        'format': 'json'
    }

    info_url = f"{WIKIMEDIA_API}?{urllib.parse.urlencode(info_params)}"

    try:
        info_data = make_api_request(info_url)
    except Exception as e:
        print(f"❌ Failed to get image info: {e}")
        return []

    images = []
    pages = info_data.get('query', {}).get('pages', {})

    for page_id, page_data in pages.items():
        if 'imageinfo' in page_data:
            info = page_data['imageinfo'][0]
            title = page_data.get('title', 'Unknown')
            filename = title.replace('File:', '')

            image = {
                'provider': 'wikimedia',
                'title': title,
                'filename': filename,
                'direct_url': info.get('url', ''),
                'file_page': f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                'width': info.get('width', 0),
                'height': info.get('height', 0),
                'mime': info.get('mime', ''),
                'license': 'CC BY-SA (check file page for exact version)',
                'attribution': f'Photo: Wikimedia Commons'
            }
            images.append(image)

    return images


def search_unsplash(topic: str, count: int = 5) -> List[Dict[str, str]]:
    """Search Unsplash (requires UNSPLASH_ACCESS_KEY)."""
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        print("❌ Missing UNSPLASH_ACCESS_KEY environment variable")
        return []

    params = {
        "query": topic,
        "per_page": str(count),
        "page": "1",
    }
    url = f"{UNSPLASH_API}?{urllib.parse.urlencode(params)}"
    data = make_json_request(url, headers={"Authorization": f"Client-ID {access_key}"})

    images = []
    for item in data.get("results", []):
        direct_url = item.get("urls", {}).get("full") or item.get("urls", {}).get("regular", "")
        width = item.get("width", 0)
        height = item.get("height", 0)
        image = {
            "provider": "unsplash",
            "title": item.get("description") or item.get("alt_description") or "Unsplash image",
            "filename": f"unsplash-{item.get('id', 'unknown')}.jpg",
            "direct_url": direct_url,
            "file_page": item.get("links", {}).get("html", ""),
            "width": width,
            "height": height,
            "mime": "image/jpeg",
            "license": "Unsplash License",
            "artist": item.get("user", {}).get("name", "Unknown"),
            "attribution": f"Photo: {item.get('user', {}).get('name', 'Unknown')} via Unsplash",
        }
        images.append(image)
    return images


def search_pexels(topic: str, count: int = 5) -> List[Dict[str, str]]:
    """Search Pexels (requires PEXELS_API_KEY)."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("❌ Missing PEXELS_API_KEY environment variable")
        return []

    params = {
        "query": topic,
        "per_page": str(count),
        "page": "1",
    }
    url = f"{PEXELS_API}?{urllib.parse.urlencode(params)}"
    data = make_json_request(url, headers={"Authorization": api_key})

    images = []
    for item in data.get("photos", []):
        src = item.get("src", {})
        direct_url = src.get("original") or src.get("large2x") or src.get("large", "")
        image = {
            "provider": "pexels",
            "title": item.get("alt", "Pexels image"),
            "filename": f"pexels-{item.get('id', 'unknown')}.jpg",
            "direct_url": direct_url,
            "file_page": item.get("url", ""),
            "width": item.get("width", 0),
            "height": item.get("height", 0),
            "mime": "image/jpeg",
            "license": "Pexels License",
            "artist": item.get("photographer", "Unknown"),
            "attribution": f"Photo: {item.get('photographer', 'Unknown')} via Pexels",
        }
        images.append(image)
    return images


def search_pixabay(topic: str, count: int = 5) -> List[Dict[str, str]]:
    """Search Pixabay (requires PIXABAY_API_KEY)."""
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        print("❌ Missing PIXABAY_API_KEY environment variable")
        return []

    params = {
        "key": api_key,
        "q": topic,
        "per_page": str(min(count, 200)),
        "page": "1",
        "image_type": "all",
    }
    url = f"{PIXABAY_API}?{urllib.parse.urlencode(params)}"
    data = make_json_request(url)

    images = []
    for item in data.get("hits", []):
        direct_url = item.get("largeImageURL") or item.get("webformatURL", "")
        image = {
            "provider": "pixabay",
            "title": item.get("tags", "Pixabay image"),
            "filename": f"pixabay-{item.get('id', 'unknown')}.jpg",
            "direct_url": direct_url,
            "file_page": item.get("pageURL", ""),
            "width": item.get("imageWidth", 0),
            "height": item.get("imageHeight", 0),
            "mime": "image/jpeg",
            "license": "Pixabay License",
            "artist": item.get("user", "Unknown"),
            "attribution": f"Photo: {item.get('user', 'Unknown')} via Pixabay",
        }
        images.append(image)
    return images


def search_images(topic: str, source: str, count: int) -> List[Dict[str, str]]:
    source = source.lower().strip()
    if source == "wikimedia":
        return search_wikimedia(topic, count)
    if source == "unsplash":
        return search_unsplash(topic, count)
    if source == "pexels":
        return search_pexels(topic, count)
    if source == "pixabay":
        return search_pixabay(topic, count)
    print(f"❌ Unsupported --source: {source}. Use wikimedia|unsplash|pexels|pixabay")
    return []


def extract_image_url_from_file_page(file_page_url: str) -> Optional[Dict[str, str]]:
    """
    Extract direct image URL from a Wikimedia Commons File: page.
    Uses the Wikimedia API for reliable extraction.

    Args:
        file_page_url: URL like https://commons.wikimedia.org/wiki/File:Image.jpg

    Returns:
        Dict with: direct_url, filename, license, attribution
    """
    print(f"📥 Extracting image URL from: {file_page_url}")

    # Extract the File: title from URL
    # URL format: https://commons.wikimedia.org/wiki/File:Name.jpg
    try:
        if '/wiki/' in file_page_url:
            title = urllib.parse.unquote(file_page_url.split('/wiki/')[-1])
        else:
            print("   ❌ Invalid Wikimedia Commons URL")
            return None

        # Use API to get direct URL
        params = {
            'action': 'query',
            'titles': title,
            'prop': 'imageinfo',
            'iiprop': 'url|size|mime|extmetadata',
            'format': 'json'
        }

        api_url = f"{WIKIMEDIA_API}?{urllib.parse.urlencode(params)}"

        data = make_api_request(api_url)

        pages = data.get('query', {}).get('pages', {})

        for page_id, page_data in pages.items():
            if 'imageinfo' in page_data:
                info = page_data['imageinfo'][0]
                metadata = info.get('extmetadata', {})

                # Try to get license from metadata
                license_info = metadata.get('LicenseShortName', {}).get('value', 'Check file page')
                artist = metadata.get('Artist', {}).get('value', 'Unknown')
                # Strip HTML tags from artist
                artist_clean = re.sub(r'<[^>]+>', '', artist).strip()

                filename = title.replace('File:', '')

                return {
                    'provider': 'wikimedia',
                    'title': title,
                    'filename': filename,
                    'direct_url': info.get('url', ''),
                    'file_page': file_page_url,
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'mime': info.get('mime', ''),
                    'license': license_info,
                    'artist': artist_clean,
                    'attribution': f'Photo: {artist_clean} via Wikimedia Commons, {license_info}'
                }

        print("   ❌ Could not find image info")
        return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def verify_image_url(url: str) -> bool:
    """Verify that an image URL is accessible."""
    print(f"🔍 Verifying URL...")

    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; ImageFetcher/1.0)')

        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            status = response.status

            if status == 200 and content_type.startswith('image/'):
                print(f"   ✅ URL verified (HTTP {status}, {content_type})")
                return True
            else:
                print(f"   ⚠️  HTTP {status}, Content-Type: {content_type}")
                return False

    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False


def generate_html_snippet(image_info: Dict[str, str], alt_text: str = "") -> str:
    """Generate HTML code snippet for embedding the image."""
    alt = alt_text or image_info.get('filename', 'Image')
    return f'''<figure>
  <img src="{image_info['direct_url']}"
       alt="{alt}"
       loading="lazy">
  <figcaption>
    {alt}
    <br><small>{image_info.get('attribution', 'Photo: Wikimedia Commons')}</small>
  </figcaption>
</figure>'''


def generate_react_snippet(image_info: Dict[str, str], alt_text: str = "") -> str:
    """Generate React/JSX code snippet for embedding the image."""
    alt = alt_text or image_info.get('filename', 'Image')
    return f'''<figure>
  <img
    src="{image_info['direct_url']}"
    alt="{alt}"
    loading="lazy"
    style={{{{ maxWidth: '100%', height: 'auto' }}}}
  />
  <figcaption style={{{{ fontSize: '0.85rem', color: '#666', fontStyle: 'italic' }}}}>
    {alt}
    <br />
    <small>{image_info.get('attribution', 'Photo: Wikimedia Commons')}</small>
  </figcaption>
</figure>'''


def print_image_info(info: Dict[str, str]) -> None:
    """Pretty print image information."""
    print()
    print("=" * 60)
    print("📸 Image Information")
    print("=" * 60)
    print(f"Filename:     {info.get('filename', 'N/A')}")
    print(f"Provider:     {info.get('provider', 'N/A')}")
    print(f"Direct URL:   {info.get('direct_url', 'N/A')}")
    print(f"File Page:    {info.get('file_page', 'N/A')}")
    print(f"Dimensions:   {info.get('width', '?')}x{info.get('height', '?')}")
    print(f"MIME Type:    {info.get('mime', 'N/A')}")
    print(f"License:      {info.get('license', 'N/A')}")
    print(f"Attribution:  {info.get('attribution', 'N/A')}")
    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch images from Wikimedia, Unsplash, Pexels, or Pixabay',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for images from Wikimedia
  %(prog)s "mofongo puerto rico" --count 5

  # Search on Unsplash (requires UNSPLASH_ACCESS_KEY)
  %(prog)s "coffee icon" --source unsplash --type icon --count 10

  # Search and output as JSON
  %(prog)s "Old San Juan colorful" --json

  # Get info from specific file page
  %(prog)s --file-page "https://commons.wikimedia.org/wiki/File:Mofongo.jpg"

  # Get file page info with verification and HTML snippet
  %(prog)s --file-page URL --verify --html --alt "Delicious mofongo"
        """
    )
    parser.add_argument('topic', nargs='?', help='Topic to search for (e.g., "paella valenciana")')
    parser.add_argument('--count', '-n', type=int, default=5, help='Number of results (default: 5)')
    parser.add_argument('--source', choices=['wikimedia', 'unsplash', 'pexels', 'pixabay'], default='wikimedia', help='Image provider (default: wikimedia)')
    parser.add_argument('--type', dest='image_type', choices=['photo', 'icon', 'vector', 'any'], default='photo', help='Filter by image type (default: photo)')
    parser.add_argument('--file-page', '-f', help='Direct File: page URL to extract from')
    parser.add_argument('--verify', '-v', action='store_true', help='Verify URL accessibility')
    parser.add_argument('--html', action='store_true', help='Generate HTML snippet')
    parser.add_argument('--react', action='store_true', help='Generate React/JSX snippet')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--alt', default='', help='Alt text for HTML/React snippet')
    parser.add_argument('--urls-only', '-u', action='store_true', help='Only output direct URLs (one per line)')

    args = parser.parse_args()
    image_type = normalize_image_type(args.image_type)

    # Validate that either topic or --file-page is provided
    if not args.topic and not args.file_page:
        parser.error("Either provide a topic or use --file-page with a File: page URL")

    if args.file_page:
        if args.source != 'wikimedia':
            parser.error('--file-page is only supported with --source wikimedia')
        # Extract from a specific File: page
        info = extract_image_url_from_file_page(args.file_page)

        if info:
            if args.json:
                print(json.dumps(info, indent=2))
            elif args.urls_only:
                print(info['direct_url'])
            else:
                print_image_info(info)

                if args.verify:
                    verify_image_url(info['direct_url'])
                    print()

                if args.html:
                    print("=" * 60)
                    print("📝 HTML Snippet")
                    print("=" * 60)
                    print(generate_html_snippet(info, args.alt))
                    print()

                if args.react:
                    print("=" * 60)
                    print("⚛️  React/JSX Snippet")
                    print("=" * 60)
                    print(generate_react_snippet(info, args.alt))
                    print()
        else:
            print("❌ Could not extract image URL")
            sys.exit(1)
    else:
        # Search mode - now actually searches!
        query = args.topic
        if image_type == 'icon':
            query = f"{args.topic} icon"
        elif image_type == 'vector':
            query = f"{args.topic} vector svg"

        print(f"🌐 Source: {args.source}")
        print(f"🧩 Type:   {image_type}")
        images = search_images(query, args.source, args.count)
        images = filter_by_type(images, image_type)

        if not images:
            print("❌ No images found")
            sys.exit(1)

        if args.json:
            print(json.dumps(images, indent=2))
        elif args.urls_only:
            for img in images:
                print(img['direct_url'])
        else:
            for i, img in enumerate(images, 1):
                print(f"[{i}] {img['filename']}")
                print(f"    Provider: {img.get('provider', 'N/A')}")
                print(f"    URL: {img['direct_url']}")
                print(f"    Size: {img.get('width', '?')}x{img.get('height', '?')}")
                print(f"    Page: {img['file_page']}")

                if args.verify:
                    verify_image_url(img['direct_url'])

                print()

            if args.html:
                print("=" * 60)
                print("📝 HTML Snippets")
                print("=" * 60)
                for img in images:
                    print(generate_html_snippet(img, args.alt))
                    print()

            if args.react:
                print("=" * 60)
                print("⚛️  React/JSX Snippets")
                print("=" * 60)
                for img in images:
                    print(generate_react_snippet(img, args.alt))
                    print()


if __name__ == '__main__':
    main()
