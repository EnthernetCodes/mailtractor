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

# ======= File Names for Saving Progress =======
LINKS_FILE = "collected_links.json"
SCRAPED_FILE = "scraped_data.json"
CSV_FILE = "scraped_companies.csv"


# ======= ChromeDriver Setup (Only Once) =======
def update_chromedriver():
    print("[INFO] Updating ChromeDriver...")
    return ChromeDriverManager().install()


CHROME_DRIVER_PATH = update_chromedriver()


# ======= Browser Initialization (Single Instance) =======
def init_browser():
    service = Service(CHROME_DRIVER_PATH)
    chrome_options = Options()

    show_browser = input("Do you want to open the browser and watch it work? (yes/no): ").strip().lower()
    if show_browser == "no":
        chrome_options.add_argument("--headless")  # Run in headless mode

    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)
    print("[INFO] Browser initialized.")
    return browser


# ======= File Handling for Saving Progress =======
def save_json(data, filename):
    with open(filename, "w") as file:
        json.dump(data, file)


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


# ======= Enhanced Scroll to Load Dynamic Content =======
def enhanced_scroll_to_load(browser, max_attempts=10):
    """ Thorough scrolling: Step-by-step with content checks to ensure full load. """
    last_height = browser.execute_script("return document.body.scrollHeight")
    attempts = 0

    while attempts < max_attempts:
        for _ in range(10):
            browser.execute_script("window.scrollBy(0, 200);")
            time.sleep(0.2)

        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1
            time.sleep(0.5)
        else:
            last_height = new_height
            attempts = 0  # Reset attempts if new content loads


# ======= Collect All Page URLs =======
def collect_all_page_urls(niche, max_pages):
    """ Generate all page URLs up to max_pages """
    base_url = "https://www.europages.co.uk/en/search"
    return [f"{base_url}?cserpRedirect=1&q={niche}"] + [
        f"{base_url}/page/{page}?cserpRedirect=1&q={niche}" for page in range(2, max_pages + 1)
    ]


# ======= Collect Company Links (Resumable) =======
def collect_company_links(browser, page_urls):
    """ Collect company profile links across all pages & save progress """
    all_links = load_json(LINKS_FILE)

    for i, url in enumerate(tqdm(page_urls, desc="Collecting Links", unit="page")):
        if url in all_links:
            print(f"[INFO] Skipping already processed page {i + 1}")
            continue

        browser.get(url)
        enhanced_scroll_to_load(browser)

        # Extract company links
        links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
        for link in links:
            href = link.get_attribute("href")
            full_link = href if href.startswith("http") else f"https://www.europages.co.uk{href}"

            if full_link not in all_links:
                all_links.append(full_link)
                save_json(all_links, LINKS_FILE)  # Save progress

    print(f"[✅] Total company links collected: {len(all_links)}")
    return all_links


# ======= Scrape Company Details (Resumable) =======
def scrape_company_details(browser, url, retries=3):
    """ Scrape details from a company page with retries on timeout. """
    attempt = 0

    while attempt < retries:
        try:
            print(f"[INFO] Scraping: {url} (Attempt {attempt + 1}/{retries})")
            browser.get(url)
            time.sleep(3)
            enhanced_scroll_to_load(browser)

            # Extract Company Details
            name = browser.find_element(By.TAG_NAME, "h1").text.strip() if browser.find_elements(By.TAG_NAME, "h1") else "N/A"
            page_text = browser.page_source
            email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_text)
            phone = browser.find_element(By.CLASS_NAME, "tel-number").text.strip() if browser.find_elements(By.CLASS_NAME, "tel-number") else "N/A"
            location = browser.find_element(By.CLASS_NAME, "company-card__info--address").text.strip() if browser.find_elements(By.CLASS_NAME, "company-card__info--address") else "N/A"

            return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone, "Location": location, "Profile URL": url}

        except Exception as e:
            print(f"[ERROR] Failed {url} (Attempt {attempt + 1}/{retries}): {e}")
            attempt += 1
            time.sleep(5)

    return None


# ======= Export to CSV =======
def export_to_csv(data, filename=CSV_FILE):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Data exported to '{filename}'")


# ======= Main Execution =======
if __name__ == "__main__":
    browser = init_browser()
    browser.set_page_load_timeout(300)

    niche = input("Enter the niche to search for: ").strip()
    max_pages = int(input("Enter the number of pages to scrape: ").strip())

    # Collect URLs & company links
    page_urls = collect_all_page_urls(niche, max_pages)
    company_links = collect_company_links(browser, page_urls)

    # Resume from last scraped company
    scraped_data = load_json(SCRAPED_FILE)
    scraped_urls = {entry["Profile URL"] for entry in scraped_data}

    # Scrape company details
    for link in tqdm(company_links, desc="Scraping Details", unit="company"):
        if link in scraped_urls:
            continue  # Skip already scraped links

        result = scrape_company_details(browser, link)
        if result:
            scraped_data.append(result)
            save_json(scraped_data, SCRAPED_FILE)  # Save after each entry

    # Export final data
    export_to_csv(scraped_data)
    browser.quit()
    print("[✅] Scraping Complete!")
