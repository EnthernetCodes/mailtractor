import re
import time
import requests
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

visited_urls = set()
email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
proxy_list = ["http://proxy1:port", "http://proxy2:port"]  # Replace with working proxies

def get_random_proxy():
    """ Returns a random proxy from the list. """
    return random.choice(proxy_list)

def extract_emails_bs4(url, use_proxy):
    """ Try extracting emails using requests + BeautifulSoup. """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }
    proxies = {"http": get_random_proxy(), "https": get_random_proxy()} if use_proxy else None
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
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

def extract_emails_selenium(url, use_proxy):
    """ Extract emails from dynamic content using Selenium, including AJAX requests. """
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    if use_proxy:
        proxy = get_random_proxy()
        options.add_argument(f"--proxy-server={proxy}")
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
        time.sleep(10)
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

def crawl_site(url, depth, use_proxy):
    """ Recursively crawl and extract emails. """
    if url in visited_urls or depth == 0:
        return []
    visited_urls.add(url)
    emails = extract_emails_bs4(url, use_proxy)
    if not emails:
        emails = extract_emails_selenium(url, use_proxy)
    for link in get_internal_links(url, url):
        emails.extend(crawl_site(link, depth-1, use_proxy))
    return list(set(emails))

if __name__ == "__main__":
    url = input("Enter website URL: ")
    depth = int(input("Enter crawl depth (e.g., 2, 5, 10): "))
    use_proxy = input("Use proxy? (yes/no): ").strip().lower() == "yes"
    emails = crawl_site(url, depth, use_proxy)
    print("Extracted Emails:", emails if emails else "No emails found.")
