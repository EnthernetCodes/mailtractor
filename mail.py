import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

def get_cookies_from_manual_login(url):
    """ Opens a browser for the user to log in manually and captures cookies. """
    service = Service(ChromeDriverManager().install())
    options = Options()
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("[INFO] Please log in manually. The browser will close automatically after login.")
        driver.get(url)
        input("[ACTION] Press Enter after logging in...")  # Wait for user confirmation
        
        cookies = driver.get_cookies()
        driver.quit()
        return cookies
    
    except Exception as e:
        print(f"[ERROR] Failed to capture cookies: {e}")
        driver.quit()
        return None

def extract_emails_with_cookies(url, cookies):
    """ Extracts emails using cookies for authentication and crawls all site pages. """
    session = requests.Session()
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
            
            soup = BeautifulSoup(response.text, "html.parser")
            text_content = soup.get_text()
            
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, text_content)
            emails.update(found_emails)
            
            # Extract all links for further crawling
            for link in soup.find_all("a", href=True):
                absolute_url = urljoin(current_url, link["href"])
                if absolute_url not in visited_urls:
                    urls_to_visit.append(absolute_url)
            
            # Extract JavaScript file links
            for script in soup.find_all("script", src=True):
                js_url = urljoin(current_url, script["src"])
                if js_url not in visited_urls:
                    urls_to_visit.append(js_url)
            
            visited_urls.add(current_url)
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to fetch {current_url}: {e}")
    
    return list(emails)

# Example usage
login_url = input("Enter login page URL: ")
target_url = input("Enter target page URL: ")

cookies = get_cookies_from_manual_login(login_url)
if cookies:
    emails = extract_emails_with_cookies(target_url, cookies)
    print("Extracted Emails:", emails)
else:
    print("Login failed, cannot fetch emails.")
