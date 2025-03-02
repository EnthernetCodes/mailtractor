import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def extract_emails_bs4(url):
    """ Try extracting emails using requests + BeautifulSoup. """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP issues

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        text_content = soup.get_text()

        # Extract emails
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, text_content)

        if emails:
            return list(set(emails))  # Remove duplicates
        else:
            print("[INFO] No emails found using BeautifulSoup. Switching to Selenium...")
            return None  # Trigger Selenium fallback

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Requests failed: {e}. Switching to Selenium...")
        return None  # Trigger Selenium fallback


def extract_emails_selenium(url):
    """ Fallback: Extract emails using Selenium for dynamic content. """
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (no GUI)
    options.add_argument("--disable-blink-features=AutomationControlled")  # Reduce detection
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for JavaScript-rendered content to load

        # Extract page source
        page_source = driver.page_source

        # Extract emails
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, page_source)

        driver.quit()
        return list(set(emails))  # Remove duplicates

    except Exception as e:
        print(f"[ERROR] Selenium extraction failed: {e}")
        driver.quit()
        return []


def extract_emails(url):
    """ Hybrid approach: Try BeautifulSoup first, then Selenium if needed. """
    emails = extract_emails_bs4(url)
    if emails is None:
        emails = extract_emails_selenium(url)

    return emails


# Example usage (Replace with actual AliExpress store URL)
url = input("Enter weblink ie https://example.com") #"https://www.aliexpress.com"  # Replace with actual store URL
emails = extract_emails(url)

if emails:
    print("Extracted Emails:", emails)
else:
    print("No emails found.")
