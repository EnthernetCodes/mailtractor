import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

def get_cookies_from_browser(url, message="Solve the challenge in the browser and press Enter to continue..."):
    """ Opens a browser for manual login or CAPTCHA solving, then retrieves session cookies. """
    service = Service(ChromeDriverManager().install())
    options = Options()
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"[INFO] {message}")
        driver.get(url)
        input("[ACTION] Press Enter after solving the challenge...")  # Wait for user confirmation
        
        cookies = driver.get_cookies()
        driver.quit()
        return cookies
    
    except Exception as e:
        print(f"[ERROR] Failed to retrieve cookies: {e}")
        driver.quit()
        return None

def is_captcha_or_cloudflare(response_text):
    """ Detects Cloudflare or CAPTCHA blocks based on page content. """
    if "Checking your browser" in response_text or "Cloudflare" in response_text:
        return "Cloudflare"
    if "recaptcha" in response_text.lower() or "g-recaptcha" in response_text.lower():
        return "reCAPTCHA"
    return None

def extract_emails(url, cookies=None):
    """ Extracts emails from a webpage, handling authentication and CAPTCHA challenges. """
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
            response = session.get(current_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Detect Cloudflare or CAPTCHA blocks
            block_type = is_captcha_or_cloudflare(response.text)
            if block_type:
                print(f"[WARNING] {block_type} detected at {current_url}. Manual intervention required.")
                cookies = get_cookies_from_browser(current_url, f"{block_type} detected! Solve it in the browser.")
                if cookies:
                    return extract_emails(url, cookies)  # Retry extraction with new cookies
                else:
                    print("[ERROR] Could not bypass the challenge. Exiting.")
                    return []
            
            # Parse page content
            soup = BeautifulSoup(response.text, "html.parser")
            text_content = soup.get_text()
            
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, text_content)
            emails.update(found_emails)
            
            # Extract links for further crawling
            for link in soup.find_all("a", href=True):
                absolute_url = urljoin(current_url, link["href"])
                if absolute_url not in visited_urls:
                    urls_to_visit.append(absolute_url)
            
            visited_urls.add(current_url)
            
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
    print("[INFO] No emails found. Login may be required.")
    
    login_url = input("Enter login page URL: ")
    cookies = get_cookies_from_browser(login_url, "Log in manually to fetch session cookies.")

    if cookies:
        emails = extract_emails(target_url, cookies)
        if emails:
            print("Extracted Emails after login:", emails)
        else:
            print("[WARNING] No emails found even after login.")
    else:
        print("[ERROR] Login failed, cannot fetch emails.")
