import os
import time
import json
import csv
import asyncio
import re
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

COOKIES_FILE = "alibaba_cookies.json"

# Initialize Chrome browser
def init_browser():
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = False  # Make sure the browser is visible
    options.add_argument("--start-maximized")  # Open in full-screen mode
    return webdriver.Chrome(service=service, options=options)

# Save cookies to a file
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

# Check if login is needed
def check_login(browser):
    browser.get("https://www.alibaba.com/")
    time.sleep(5)
    
    if "Login" in browser.page_source or "Sign In" in browser.page_source:
        print("[WARNING] Not logged in! Please log in manually.")
        input("[ACTION] After logging in, press Enter to continue...")
        save_cookies(browser)
    else:
        print("[INFO] Logged in successfully!")

# Extract company profile links from search results
async def get_company_links(browser, niche):
    search_url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=company_en&CatId=&SearchText={niche}"
    browser.get(search_url)
    time.sleep(5)  # Allow page to load

    soup = BeautifulSoup(browser.page_source, "html.parser")
    company_links = []

    for link in soup.find_all("a", href=True):
        if "/company/" in link["href"]:
            company_links.append(urljoin("https://www.alibaba.com", link["href"]))

    print(f"[INFO] Found {len(company_links)} suppliers for '{niche}'.")
    return list(set(company_links))  # Remove duplicates

# Extract email and contact details from supplier profile
async def get_company_details(browser, url):
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

    return {"Name": name, "Email": email, "Phone": phone, "Profile URL": url}

# Save results to a CSV file
def save_to_csv(niche, data):
    filename = f"{niche}_alibaba_contacts.csv"
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Profile URL"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    print(f"[INFO] Data saved to '{filename}'.")

# Load previously scraped data for auto-resume
def load_previous_data(filename):
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        scraped_urls = set(df["Profile URL"])
        print(f"[INFO] Resuming from last saved progress ({len(scraped_urls)} suppliers already scraped).")
        return scraped_urls, df.to_dict(orient="records")
    return set(), []

# Main function to run the bot
async def scrape_alibaba():
    niche = input("Enter a niche (e.g., mining, electronics, textiles): ").strip()
    if not niche:
        print("[ERROR] Niche cannot be empty!")
        return

    csv_filename = f"{niche}_alibaba_contacts.csv"

    # Load previous data for auto-resume
    scraped_urls, company_data = load_previous_data(csv_filename)

    print(f"[INFO] Searching for '{niche}' suppliers on Alibaba...")

    browser = init_browser()

    try:
        # Load cookies and check login status
        load_cookies(browser)
        check_login(browser)

        company_links = await get_company_links(browser, niche)

        for index, link in enumerate(company_links):
            if link in scraped_urls:
                print(f"[INFO] Skipping already scraped ({index+1}/{len(company_links)}) → {link}")
                continue  # Skip companies already scraped

            print(f"[INFO] Scraping ({index+1}/{len(company_links)}) → {link}")
            details = await get_company_details(browser, link)
            company_data.append(details)

            # **Auto-save every 5 suppliers**
            if len(company_data) % 5 == 0:
                save_to_csv(niche, company_data)

    except KeyboardInterrupt:
        print("\n[WARNING] Script interrupted! Saving progress before exiting...")
        save_to_csv(csv_filename, company_data)

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

    finally:
        save_to_csv(csv_filename, company_data)  # Final save
        input("[ACTION] Press Enter to close the browser...")
        browser.quit()

# Run the script asynchronously
if __name__ == "__main__":
    asyncio.run(scrape_alibaba())
