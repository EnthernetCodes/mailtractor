import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

def get_cookies_from_browser(url):
    """
    Opens a visible Chrome browser, navigates to the URL, and retrieves session cookies.
    Ensures the browser is visible and waits for user input if login or CAPTCHA is required.
    """
    print(f"[INFO] Opening browser for {url}...")

    # Install ChromeDriver if not already installed
    service = Service(ChromeDriverManager().install())

    # Explicitly disable headless mode to make sure browser is visible
    options = Options()
    options.headless = False  # Forces browser to be visible
    options.add_argument("--start-maximized")  # Opens browser in full-screen mode

    # Launch Chrome
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(5)  # Delay to allow the page to fully load

        print("[INFO] If a CAPTCHA or login page is detected, please solve it.")
        input("[ACTION] Press Enter after solving the challenge...")

        # Retrieve cookies
        cookies = driver.get_cookies()
        print(f"[INFO] Cookies obtained: {cookies}")

        driver.quit()
        return cookies
    
    except Exception as e:
        print(f"[ERROR] Failed to retrieve cookies: {e}")
        driver.quit()
        return None

def extract_emails(url, cookies=None):
    """ Extracts emails from a webpage while handling XML pages, Cloudflare, and login authentication. """
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

            # Detect XML pages
            is_xml = "xml" in response.headers.get("Content-Type", "").lower()

            if is_xml:
                print(f"[INFO] XML detected: {current_url}. Parsing with lxml.")
                soup = BeautifulSoup(response.content, "xml")  # Use XML parser
            else:
                soup = BeautifulSoup(response.text, "html.parser")  # Default HTML parser
            
            # Check for Cloudflare challenge
            if "Checking your browser" in response.text or "cf-browser-verification" in response.text:
                print(f"[WARNING] Cloudflare detected at {current_url}. Opening browser for bypass...")
                cookies = get_cookies_from_browser(current_url)
                
                if cookies:
                    return extract_emails(url, cookies)  # Retry with new cookies
                else:
                    print("[ERROR] Could not bypass Cloudflare. Exiting.")
                    return []
            
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
