import re
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

visited_urls = set()
email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

def extract_emails_bs4(url):
    """ Try extracting emails using requests + BeautifulSoup. """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        emails = re.findall(email_pattern, response.text)
        if emails:
            print(f"[INFO] Emails found using BeautifulSoup: {emails}")
        else:
            print("[INFO] No emails found using BeautifulSoup. Switching to Selenium...")
        return list(set(emails))
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Requests failed: {e}. Switching to Selenium...")
        return []

def extract_emails_selenium(url):
    """ Extract emails from dynamic content using Selenium. """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True
    )
    try:
        driver.get(url)
        time.sleep(5)
        emails = re.findall(email_pattern, driver.page_source)
        driver.quit()
        if emails:
            print(f"[INFO] Emails found using Selenium: {emails}")
        else:
            print("[INFO] No emails found using Selenium.")
        return list(set(emails))
    except Exception as e:
        print(f"[ERROR] Selenium extraction failed: {e}")
        driver.quit()
        return []

def extract_js_emails(url):
    """ Extract emails from JavaScript files linked to the page. """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        js_links = re.findall(r'src=["\'](.*?\.js)["\']', response.text)
        emails = []
        for js_link in js_links:
            full_url = urljoin(url, js_link)
            js_content = requests.get(full_url, headers=headers).text
            emails.extend(re.findall(email_pattern, js_content))
        if emails:
            print(f"[INFO] Emails found in JavaScript files: {emails}")
        else:
            print("[INFO] No emails found in JavaScript files.")
        return list(set(emails))
    except requests.exceptions.RequestException:
        return []

def get_internal_links(url, base_url):
    """ Get all internal links on a page. """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = urljoin(base_url, a_tag["href"])
            if urlparse(href).netloc == urlparse(base_url).netloc:
                links.add(href)
        return links
    except requests.exceptions.RequestException:
        return set()

def crawl_site(url, depth):
    """ Recursively crawl and extract emails. """
    if url in visited_urls or depth == 0:
        return []
    visited_urls.add(url)
    emails = extract_emails_bs4(url)
    if not emails:
        emails = extract_emails_selenium(url)
    emails.extend(extract_js_emails(url))
    for link in get_internal_links(url, url):
        emails.extend(crawl_site(link, depth-1))
    return list(set(emails))

if __name__ == "__main__":
    url = input("Enter website URL: ")
    depth = int(input("Enter crawl depth (e.g., 2, 5, 10): "))  # Get depth from user
    emails = crawl_site(url, depth)
    print("Extracted Emails:", emails if emails else "No emails found.")
