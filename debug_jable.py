import requests
from bs4 import BeautifulSoup
import re

def debug_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check Title
        print(f"Title: {soup.title.string if soup.title else 'No Title'}")
        
        # Check M3U8 Regex
        result = re.search("https://.+m3u8", html_content)
        if result:
            m3u8url = result.group(0)
            print(f"Found M3U8 URL: {m3u8url}")
        else:
            print("No M3U8 URL found via regex.")
            
        # Check og:image
        image_meta = soup.find('meta', property='og:image')
        if image_meta:
            image_url = image_meta.get('content')
            print(f"Found og:image: {image_url}")
        else:
            print("No og:image found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_url("https://jable.tv/videos/ipzz-747/")
