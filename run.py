import os
import re
import json
import time
import csv
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

COOKIES_FILE = "alibaba_cookies.json"
TEMPLATE_FILE = "message_template.json"

# Load or initialize message template
def load_template():
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r") as f:
            return json.load(f)
    return {
        "name": "Your Name",
        "company": "Your Company",
        "message": "Hello, I am interested in your product. Please provide more details."
    }

# Save user message template
def save_template(template):
    with open(TEMPLATE_FILE, "w") as f:
        json.dump(template, f, indent=4)
    print("[INFO] Message template updated successfully!")

# Ask user if they want to edit the template
def edit_template():
    template = load_template()
    print("\n[📌 Current Contact Supplier Message Template]")
    print(f"Name: {template['name']}")
    print(f"Company: {template['company']}")
    print(f"Message: {template['message']}")
    
    choice = input("\nDo you want to edit the template? (yes/no): ").strip().lower()
    if choice == "yes":
        template["name"] = input("Enter your name: ").strip()
        template["company"] = input("Enter your company name: ").strip()
        template["message"] = input("Enter your message: ").strip()
        save_template(template)
        print("[✅ Template updated!]\n")
    else:
        print("[✅ Using existing template]\n")

# Initialize Chrome browser
def init_browser():
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = False  # Keep browser visible
    options.add_argument("--start-maximized")  # Open in full-screen mode
    return webdriver.Chrome(service=service, options=options)

# Save cookies for login persistence
def save_cookies(browser):
    with open(COOKIES_FILE, "w") as f:
        json.dump(browser.get_cookies(), f)
    print("[INFO] Cookies saved successfully!")

# Load cookies if they exist
def load_cookies(browser):
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
            for cookie in cookies:
                browser.add_cookie(cookie)
        print("[INFO] Cookies loaded successfully!")

# Extract company profile links from search results
def get_company_links(browser, niche):
    search_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=company_en&CatId=&SearchText={niche}"
    browser.get(search_url)
    time.sleep(5)  # Wait for page to load

    company_links = []
    while True:
        soup = BeautifulSoup(browser.page_source, "html.parser")

        # Extract company profile links
        for link in soup.find_all("a", href=True):
            if "/company/" in link["href"]:
                company_links.append(urljoin("https://www.alibaba.com", link["href"]))

        # Find and click "Next" button if it exists
        next_button = browser.find_elements(By.XPATH, "//a[contains(text(),'Next')]")
        if next_button:
            next_button[0].click()
            time.sleep(5)  # Wait for next page to load
        else:
            break  # No more pages

    print(f"[INFO] Found {len(company_links)} suppliers for '{niche}'.")
    return list(set(company_links))  # Remove duplicates

# Extract email and contact details from supplier profile
def get_company_details(browser, url):
    browser.get(url)
    time.sleep(5)  # Allow JavaScript to load

    soup = BeautifulSoup(browser.page_source, "html.parser")

    # Extract company name
    name = soup.find("h1")
    name = name.text.strip() if name else "N/A"

    # Extract email using regex (if present in the page)
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found_emails = re.findall(email_pattern, soup.text)
    email = found_emails[0] if found_emails else "N/A"

    # Extract phone number (if available)
    phone = "N/A"
    phone_span = soup.find("span", class_="contact-phone")
    if phone_span:
        phone = phone_span.text.strip()

    # If email is hidden, try filling out the form
    if email == "N/A":
        email = fill_contact_form(browser)

    return {"Name": name, "Email": email, "Phone": phone, "Profile URL": url}

# Fill "Contact Supplier" form if email is hidden
def fill_contact_form(browser):
    template = load_template()
    
    try:
        # Click "Contact Supplier" button
        contact_button = browser.find_element(By.XPATH, "//button[contains(text(),'Contact Supplier')]")
        contact_button.click()
        time.sleep(3)

        # Fill the form fields
        name_field = browser.find_element(By.NAME, "name")
        company_field = browser.find_element(By.NAME, "companyName")
        message_field = browser.find_element(By.NAME, "content")

        name_field.send_keys(template["name"])
        company_field.send_keys(template["company"])
        message_field.send_keys(template["message"])

        # Submit the form
        submit_button = browser.find_element(By.XPATH, "//button[contains(text(),'Send')]")
        submit_button.click()
        time.sleep(5)  # Wait for possible response

        # Check for a response
        response_text = "N/A"
        try:
            response_element = browser.find_element(By.CLASS_NAME, "message-content")
            response_text = response_element.text.strip()
        except:
            pass  # No response received

        return response_text

    except Exception as e:
        print(f"[WARNING] Could not submit contact form: {e}")
        return "N/A"

# Save results to a CSV file
def save_to_csv(niche, data):
    filename = f"{niche}_alibaba_contacts.csv"
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Profile URL"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    print(f"[INFO] Data saved to '{filename}'.")

# Run the scraper
def scrape_alibaba():
    edit_template()
    niche = input("Enter a niche (e.g., mining, electronics, textiles): ").strip()
    browser = init_browser()
    load_cookies(browser)
    company_links = get_company_links(browser, niche)

    for link in company_links:
        details = get_company_details(browser, link)
        save_to_csv(niche, [details])

if __name__ == "__main__":
    scrape_alibaba()
