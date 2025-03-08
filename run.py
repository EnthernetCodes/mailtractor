import asyncio
import csv
import re
import time
import os
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Function to initialize Chrome browser
def init_browser():
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = False  # Ensure browser is visible
    options.add_argument("--start-maximized")  # Open in full-screen mode
    return webdriver.Chrome(service=service, options=options)

# Function to extract company profile links from search results
async def get_company_links(browser, niche):
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)
    time.sleep(5)  # Wait for page to load

    soup = BeautifulSoup(browser.page_source, "html.parser")
    company_links = []
    
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/en/company/" in href:  # Only pick company profile links
            company_links.append(urljoin("https://www.europages.co.uk", href))

    print(f"[INFO] Found {len(company_links)} companies for '{niche}'.")
    return list(set(company_links))  # Remove duplicates

# Function to extract email and contact details from a company profile
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
    phone_span = soup.find("span", class_="tel-number")
    if phone_span:
        phone = phone_span.text.strip()

    # Extract location (if available)
    location = "N/A"
    location_div = soup.find("div", class_="company-card__info--address")
    if location_div:
        location = location_div.text.strip()

    return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

# Function to save results to a CSV file
def save_to_csv(niche, data):
    filename = f"{niche}_contacts.csv"
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Location", "Profile URL"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    print(f"[INFO] Data saved to '{filename}'.")

# Main function to run the bot
async def scrape_europages():
    niche = input("Enter a niche (e.g., mining, engineering, healthcare): ").strip()
    if not niche:
        print("[ERROR] Niche cannot be empty!")
        return

    print(f"[INFO] Searching for '{niche}' companies on Europages...")

    browser = init_browser()

    try:
        company_links = await get_company_links(browser, niche)
        company_data = []

        for index, link in enumerate(company_links):
            print(f"[INFO] Scraping ({index+1}/{len(company_links)}) → {link}")
            details = await get_company_details(browser, link)
            company_data.append(details)

        save_to_csv(niche, company_data)
        
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    
    finally:
        input("[ACTION] Press Enter to close the browser...")
        browser.quit()

# Run the script asynchronously
if __name__ == "__main__":
    asyncio.run(scrape_europages())
