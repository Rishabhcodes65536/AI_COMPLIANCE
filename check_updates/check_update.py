import schedule
import time
import requests
from bs4 import BeautifulSoup
import hashlib

# Function to fetch website content
def fetch_text_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts and styles
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        
        # Get textual content
        text = soup.get_text(separator=" ", strip=True)
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the website: {e}")
        return None

# Function to compute hash
def compute_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Global variable to store the last known hash
last_known_hash = None

# Function to check for updates
def check_website_for_updates():
    global last_known_hash
    url = "https://www.revisor.mn.gov/statutes/cite/245D" 

    print(f"Checking website for updates: {url}")
    text_content = fetch_text_content(url)
    if text_content is None:
        print("Failed to fetch website content.")
        return
    
    current_hash = compute_hash(text_content)
    if last_known_hash is None:
        # Initialize the hash
        last_known_hash = current_hash
        print("Initialized hash for the first time.")
    elif current_hash != last_known_hash:
        print("Website content has been updated.")
        last_known_hash = current_hash
    else:
        print("No changes detected in website content.")


schedule.every(20).seconds.do(check_website_for_updates)

print("Scheduler started. Press Ctrl+C to stop.")


try:
    while True:
        schedule.run_pending()
        time.sleep(1)  
except KeyboardInterrupt:
    print("Scheduler stopped.")
