import os
import re
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

# Initialize Chrome browser
def init_browser():
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = False  # Keep browser visible
    options.add_argument("--start-maximized")  # Open in full-screen mode
    return webdriver.Chrome(service=service, options=options)

# Extract company profile links from search results
def get_company_links(browser, search_url):
    browser.get(search_url)
    time.sleep(5)  # Wait for page to load

    company_links = []
    while True:
        soup = BeautifulSoup(browser.page_source, "html.parser")

        # Extract company profile links
        for link in soup.find_all("a", href=True):
            if "companyinfo.html" in link["href"]:  # Targeting company profile pages
                company_links.append(urljoin("https://www.exportbureau.com/", link["href"]))

        # Find and click "Next" button if it exists
        next_button = browser.find_elements(By.LINK_TEXT, "Next")
        if next_button:
            next_button[0].click()
            time.sleep(5)  # Wait for next page to load
        else:
            break  # No more pages

    print(f"[INFO] Found {len(company_links)} suppliers.")
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
    phone_span = soup.find("td", string="Phone:")
    if phone_span and phone_span.find_next_sibling("td"):
        phone = phone_span.find_next_sibling("td").text.strip()

    # Extract location (if available)
    location = "N/A"
    location_span = soup.find("td", string="Country:")
    if location_span and location_span.find_next_sibling("td"):
        location = location_span.find_next_sibling("td").text.strip()

    return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

# Save results to a CSV file
def save_to_csv(niche, data):
    filename = f"{niche}_exportbureau_contacts.csv"
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Location", "Profile URL"]

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
def scrape_exportbureau():
    niche = input("Enter a niche (e.g., Engineering, Chemicals, Electronics): ").strip()
    if not niche:
        print("[ERROR] Niche cannot be empty!")
        return

    search_url = f"https://www.exportbureau.com/search.html?search={niche}&country=all&submit=Search"
    csv_filename = f"{niche}_exportbureau_contacts.csv"

    # Load previous data for auto-resume
    scraped_urls, company_data = load_previous_data(csv_filename)

    print(f"[INFO] Searching for '{niche}' suppliers on ExportBureau...")

    browser = init_browser()

    try:
        company_links = get_company_links(browser, search_url)

        for index, link in enumerate(company_links):
            if link in scraped_urls:
                print(f"[INFO] Skipping already scraped ({index+1}/{len(company_links)}) → {link}")
                continue  # Skip companies already scraped

            print(f"[INFO] Scraping ({index+1}/{len(company_links)}) → {link}")
            details = get_company_details(browser, link)
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

# Run the script
if __name__ == "__main__":
    scrape_exportbureau()
