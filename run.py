import re
import requests
import undetected_chromedriver as uc  # Import for Cloudflare bypass
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

def get_cookies_from_browser(url):
    """
    Uses undetected ChromeDriver to bypass Cloudflare and retrieve session cookies.
    The browser is always visible so you can watch the bot work.
    """
    service = Service(ChromeDriverManager().install())
    
    # Start Chrome in normal mode (Visible, not headless)
    driver = uc.Chrome(service=service, use_subprocess=True)
    
    try:
        print(f"[INFO] Accessing {url}...")
        driver.get(url)
        
        # Wait for Cloudflare verification or login page
        driver.implicitly_wait(10)
        
        # Get cookies after verification
        cookies = driver.get_cookies()
        driver.quit()
        return cookies
    
    except Exception as e:
        print(f"[ERROR] Failed to retrieve cookies: {e}")
        driver.quit()
        return None

def extract_emails(url, cookies=None):
    """ Extracts emails from a webpage while handling Cloudflare and login authentication. """
    session = requests.Session()
    
    if cookies:
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    visited_urls = set()
    emails = set()
    urls_to_visit = [url]
    
    while urls_to_visit:
        current_url = urls_to_visit.pop()
        if current_url in visited_urls:
            continue
        
        try:
            # Skip non-http(s) links (e.g., "tel:", "ms-windows-store:")
            if not current_url.startswith(("http://", "https://")):
                print(f"[INFO] Skipping non-HTTP URL: {current_url}")
                continue
            
            response = session.get(current_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check for Cloudflare challenge
            if "Checking your browser" in response.text or "cf-browser-verification" in response.text:
                print(f"[WARNING] Cloudflare detected at {current_url}. Opening browser for bypass...")
                cookies = get_cookies_from_browser(current_url)
                
                if cookies:
                    return extract_emails(url, cookies)  # Retry with new cookies
                else:
                    print("[ERROR] Could not bypass Cloudflare. Exiting.")
                    return []
            
            # Parse page content
            soup = BeautifulSoup(response.text, "html.parser")
            text_content = soup.get_text()
            
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, text_content)
            emails.update(found_emails)
            
            # Extract valid links for further crawling
            for link in soup.find_all("a", href=True):
                absolute_url = urljoin(current_url, link["href"])
                if absolute_url not in visited_urls and absolute_url.startswith(("http://", "https://")):
                    urls_to_visit.append(absolute_url)
            
            visited_urls.add(current_url)
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"[INFO] Skipping broken link (404 Not Found): {current_url}")
            else:
                print(f"[ERROR] HTTP error at {current_url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to fetch {current_url}: {e}")
    
    return list(emails)

# Example usage
target_url = input("Enter target page URL: ")

# Step 1: Try extracting emails without authentication
emails = extract_emails(target_url)

if emails:
    print("Extracted Emails:", emails)
else:
    print("[INFO] No emails found. Checking if login is required.")
    
    login_url = input("Enter login page URL: ")
    cookies = get_cookies_from_browser(login_url)

    if cookies:
        emails = extract_emails(target_url, cookies)
        if emails:
            print("Extracted Emails after login:", emails)
        else:
            print("[WARNING] No emails found even after login.")
    else:
        print("[ERROR] Login failed, cannot fetch emails.")
