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
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# ====== Auto-Update ChromeDriver =======
def update_chromedriver():
    print("[INFO] Updating ChromeDriver to match the latest browser version...")
    driver_path = ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
    print(f"[INFO] ChromeDriver updated: {driver_path}")
    return driver_path

# ====== Initialize Chrome Browser =======
def init_browser():
    service = Service(update_chromedriver())  # Updated ChromeDriver
    options = Options()
    options.headless = False  # Change to True for background execution
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = webdriver.Chrome(service=service, options=options)
    browser.implicitly_wait(15)  # Increase wait time to 15 seconds
    return browser

# ===== Scroll to Load Dynamic Content =====
def scroll_to_bottom(browser):
    last_height = 0
    for _ in range(30):  # Scroll multiple times
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(3, 7))
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ===== Load Page with Retries =====
def load_page_with_retries(browser, url, retries=3):
    """Try to load a page multiple times in case of failure."""
    for i in range(retries):
        try:
            browser.get(url)
            time.sleep(random.uniform(7, 15))
            scroll_to_bottom(browser)
            return
        except Exception as e:
            print(f"[ERROR] Failed to load page (Attempt {i+1}/{retries}): {e}")
            time.sleep(5)
    print("[ERROR] Failed to load page after retries.")

# ===== Extract Company Links =====
async def get_company_links(browser, niche):
    base_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    load_page_with_retries(browser, base_url)
    
    company_links = set()

    while True:
        scroll_to_bottom(browser)  # Ensure full page loads
        soup = BeautifulSoup(browser.page_source, "html.parser")

        for link in soup.find_all("a", href=True):
            if "/en/company/" in link["href"]:
                company_links.add(urljoin("https://www.europages.co.uk", link["href"]))

        print(f"[INFO] Collected {len(company_links)} companies so far...")

        # Click "Next" button
        try:
            next_button = browser.find_element(By.CSS_SELECTOR, "a.pagination__next")
            if next_button.is_enabled():
                next_button.click()
                time.sleep(random.uniform(7, 15))
            else:
                break
        except (NoSuchElementException, TimeoutException):
            print("[INFO] No more pages found.")
            break

    return list(company_links)

# ===== Extract Company Details =====
async def get_company_details(browser, url):
    load_page_with_retries(browser, url)
    soup = BeautifulSoup(browser.page_source, "html.parser")

    name = soup.find("h1")
    name = name.text.strip() if name else "N/A"

    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found_emails = re.findall(email_pattern, soup.text)
    email = found_emails[0] if found_emails else "N/A"

    phone = "N/A"
    phone_span = soup.find("span", class_="tel-number")
    if phone_span:
        phone = phone_span.text.strip()

    location = "N/A"
    location_div = soup.find("div", class_="company-card__info--address")
    if location_div:
        location = location_div.text.strip()

    return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

# ===== Save Results to CSV =====
def save_to_csv(filename, data):
    keys = data[0].keys() if data else ["Name", "Email", "Phone", "Location", "Profile URL"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"[INFO] Data saved to '{filename}'.")

# ===== Load Previous Data for Resumption =====
def load_previous_data(filename):
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        scraped_urls = set(df["Profile URL"])
        print(f"[INFO] Resuming from last saved progress ({len(scraped_urls)} companies already scraped).")
        return scraped_urls, df.to_dict(orient="records")
    return set(), []

# ===== Main Scraper =====
async def scrape_europages():
    niche = input("Enter a niche (e.g., machine, mining, engineering): ").strip()
    if not niche:
        print("[ERROR] Niche cannot be empty!")
        return

    csv_filename = f"{niche}_contacts.csv"
    scraped_urls, company_data = load_previous_data(csv_filename)

    print(f"[INFO] Searching for '{niche}' companies on Europages...")
    browser = init_browser()

    try:
        company_links = await get_company_links(browser, niche)

        for index, link in enumerate(company_links):
            if link in scraped_urls:
                print(f"[INFO] Skipping already scraped ({index+1}/{len(company_links)}) → {link}")
                continue

            print(f"[INFO] Scraping ({index+1}/{len(company_links)}) → {link}")
            details = await get_company_details(browser, link)
            company_data.append(details)

            # Auto-save every 5 companies
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

# ===== Run the Script =====
if __name__ == "__main__":
    asyncio.run(scrape_europages())
