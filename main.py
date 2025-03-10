import asyncio
import csv
import re
import time
import os
import random
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# Function to initialize Chrome browser
def init_browser():
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = False  # Change to True if running in the background
    options.add_argument("--start-maximized")  # Full-screen mode
    return webdriver.Chrome(service=service, options=options)

# Function to extract company profile links from search results (with pagination)
async def get_company_links(browser, niche):
    base_url = "https://www.europages.co.uk/en/search?cserpRedirect=1&q="
    search_url = f"{base_url}{niche}"
    browser.get(search_url)
    time.sleep(random.randint(5, 10))  # Randomized delay for anti-blocking

    company_links = set()

    while True:
        soup = BeautifulSoup(browser.page_source, "html.parser")
        
        # Extract company profile links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/en/company/" in href:
                company_links.add(urljoin("https://www.europages.co.uk", href))

        print(f"[INFO] Found {len(company_links)} companies so far...")

        # Check for "Next" button and navigate
        try:
            next_button = browser.find_element(By.CSS_SELECTOR, "a.pagination__next")
            if next_button.is_enabled():
                next_button.click()
                time.sleep(random.randint(5, 10))  # Allow new page to load
            else:
                break  # No more pages, exit loop
        except NoSuchElementException:
            break  # No "Next" button found, exit

    return list(company_links)

# Function to extract company details
async def get_company_details(browser, url):
    browser.get(url)
    time.sleep(random.randint(5, 10))  # Randomized delay for JS loading

    # Scroll down to load full page content
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)

    soup = BeautifulSoup(browser.page_source, "html.parser")

    # Extract company name
    name = soup.find("h1")
    name = name.text.strip() if name else "N/A"

    # Extract email using regex
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found_emails = re.findall(email_pattern, soup.text)
    email = found_emails[0] if found_emails else "N/A"

    # Extract phone number
    phone = "N/A"
    phone_span = soup.find("span", class_="tel-number")
    if phone_span:
        phone = phone_span.text.strip()

    # Extract location
    location = "N/A"
    location_div = soup.find("div", class_="company-card__info--address")
    if location_div:
        location = location_div.text.strip()

    return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

# Function to save results to a CSV file
def save_to_csv(filename, data):
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Location", "Profile URL"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"[INFO] Data saved to '{filename}'.")

# Function to load previously scraped data for auto-resume
def load_previous_data(filename):
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        scraped_urls = set(df["Profile URL"])
        print(f"[INFO] Resuming from last saved progress ({len(scraped_urls)} companies already scraped).")
        return scraped_urls, df.to_dict(orient="records")
    return set(), []

# Main function to run the bot
async def scrape_europages():
    niche = input("Enter a niche (e.g., mining, engineering, healthcare): ").strip()
    if not niche:
        print("[ERROR] Niche cannot be empty!")
        return

    csv_filename = f"{niche}_contacts.csv"
    
    # Load previously scraped data for resumption
    scraped_urls, company_data = load_previous_data(csv_filename)

    print(f"[INFO] Searching for '{niche}' companies on Europages...")

    browser = init_browser()
    
    try:
        company_links = await get_company_links(browser, niche)

        for index, link in enumerate(company_links):
            if link in scraped_urls:
                print(f"[INFO] Skipping already scraped ({index+1}/{len(company_links)}) → {link}")
                continue  # Skip already scraped companies

            print(f"[INFO] Scraping ({index+1}/{len(company_links)}) → {link}")
            details = await get_company_details(browser, link)
            company_data.append(details)

            # **Auto-save every 5 companies**
            if len(company_data) % 5 == 0:
                save_to_csv(csv_filename, company_data)

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
    asyncio.run(scrape_europages())
