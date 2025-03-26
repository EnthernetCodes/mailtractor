from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from tqdm import tqdm
import time
import csv
import json
import os
import re

# ======= Browser Initialization =======
def init_browser():
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    
    show_browser = input("Do you want to open the browser and watch it work? (yes/no): ").strip().lower()
    if show_browser == "no":
        chrome_options.add_argument("--headless")  # Run in headless mode

    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)
    print("[INFO] Browser initialized.")
    return browser

# ======= File Handling =======
def save_json(data, filename):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return []

# ======= Accept Cookies =======
def accept_cookies(browser):
    try:
        cookie_button = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept')]"))
        )
        cookie_button.click()
        print("[INFO] Cookie popup accepted.")
        time.sleep(2)
    except TimeoutException:
        print("[INFO] No cookie popup found.")

# ======= Extract Company Website from Europages Profile =======
def get_company_website(browser):
    try:
        visit_site_button = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Visit site') or contains(text(), 'visit site')]"))
        )
        website_url = visit_site_button.get_attribute("href")
        if website_url and website_url.startswith("http"):
            return website_url
    except TimeoutException:
        return None
    return None

# ======= Extract Emails from the Official Website =======
def extract_emails_from_website(browser, website_url):
    try:
        browser.get(website_url)
        time.sleep(3)
        
        # Extract emails using regex
        page_text = browser.page_source
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_text)
        
        return list(set(emails))  # Remove duplicates
    except Exception as e:
        print(f"[ERROR] Failed to extract emails from {website_url}: {e}")
        return []

# ======= Scrape Company Details =======
def scrape_company_details(browser, europages_url):
    try:
        browser.get(europages_url)
        time.sleep(3)
        
        name = browser.find_element(By.TAG_NAME, "h1").text.strip() if browser.find_elements(By.TAG_NAME, "h1") else "N/A"
        company_website = get_company_website(browser)
        
        if company_website:
            print(f"[INFO] Visiting official site: {company_website}")
            emails = extract_emails_from_website(browser, company_website)
            if emails:
                return {
                    "Name": name,
                    "Emails": emails,
                    "Website": company_website,
                    "Europages Profile": europages_url
                }
        else:
            print(f"[INFO] No official site found for {name}. Skipping.")
            
    except Exception as e:
        print(f"[ERROR] Failed to scrape {europages_url}: {e}")
    
    return None

# ======= Export to CSV =======
def export_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Emails", "Website", "Europages Profile"])
        writer.writeheader()
        for entry in data:
            writer.writerow({
                "Name": entry["Name"],
                "Emails": ", ".join(entry["Emails"]),
                "Website": entry["Website"],
                "Europages Profile": entry["Europages Profile"]
            })
    print(f"[✅] Data exported to '{filename}'")

# ======= Main Execution =======
if __name__ == "__main__":
    browser = init_browser()
    
    niche = input("Enter the niche to search for: ").strip()
    max_pages = int(input("Enter the number of pages to scrape: ").strip())
    
    base_url = "https://www.europages.co.uk/en/search"
    page_urls = [f"{base_url}?cserpRedirect=1&q={niche}"] + [
        f"{base_url}/page/{page}?cserpRedirect=1&q={niche}" for page in range(2, max_pages + 1)
    ]
    
    collected_links = load_json(f"{niche}_collected_links.json")
    
    # Step 1: Collect Europages Company Profile Links
    for i, url in enumerate(tqdm(page_urls, desc="Collecting Links", unit="page")):
        if url in collected_links:
            print(f"[INFO] Skipping already processed page {i + 1}")
            continue

        browser.get(url)
        time.sleep(3)
        
        # Extract company profile links
        links = [link.get_attribute("href") for link in browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")]
        links = [href for href in links if href and href.startswith("http")]
        
        collected_links.extend(links)
        save_json(collected_links, f"{niche}_collected_links.json")
    
    print(f"[✅] Total company links collected: {len(collected_links)}")
    
    scraped_data = load_json(f"{niche}_scraped_data.json")
    scraped_urls = {entry["Europages Profile"] for entry in scraped_data}

    # Step 2: Scrape Each Company Profile for Official Website & Emails
    for link in tqdm(collected_links, desc="Scraping Company Details", unit="company"):
        if link in scraped_urls:
            continue

        company_data = scrape_company_details(browser, link)
        if company_data:
            scraped_data.append(company_data)
            save_json(scraped_data, f"{niche}_scraped_data.json")
    
    # Step 3: Export Data to CSV
    export_to_csv(scraped_data, f"{niche}_scraped_companies.csv")
    
    browser.quit()
    print("[✅] Scraping Complete!")
