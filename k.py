from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import time
import csv
import re
import traceback

# ===== Global ChromeDriver Path =====
chrome_driver_path = None

# ===== Chrome Options =====
show_browser = input("Do you want to open the browser and watch it work? (yes/no): ").strip().lower()
chrome_options = Options()
if show_browser == "no":
    chrome_options.add_argument("--headless")  # Headless mode for background execution
chrome_options.add_argument("--start-maximized")

# ===== ChromeDriver Update (Runs Once) =====
def update_chromedriver():
    global chrome_driver_path
    if not chrome_driver_path:
        print("[INFO] Updating ChromeDriver...")
        chrome_driver_path = ChromeDriverManager().install()
        print(f"[INFO] ChromeDriver updated: {chrome_driver_path}")
    return chrome_driver_path

# ===== Browser Initialization =====
def init_browser():
    service = Service(update_chromedriver())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)
    return browser

# ===== Accept Cookies =====
def accept_cookies(browser):
    try:
        print("[INFO] Checking for cookie popup...")
        cookie_button = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept')]"))
        )
        cookie_button.click()
        print("[INFO] Cookie popup accepted.")
        time.sleep(2)
    except:
        print("[INFO] No cookie popup found.")

# ===== Scroll to Load More =====
def scroll_to_load(browser):
    last_height = browser.execute_script("return document.body.scrollHeight")
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ===== Collect Company Links =====
def collect_company_links(browser, niche, max_pages):
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)

    accept_cookies(browser)

    all_links = []

    for page in range(1, max_pages + 1):
        try:
            print(f"[INFO] Scraping page {page} at {browser.current_url}")

            WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-test='company-name']"))
            )

            scroll_to_load(browser)

            links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
            print(f"[INFO] Found {len(links)} company links on page {page}")

            for link in links:
                href = link.get_attribute("href")
                if href:
                    if href.startswith("http"):
                        full_url = href
                    else:
                        full_url = f"https://www.europages.co.uk{href}"
                    if full_url not in all_links:
                        all_links.append(full_url)

            print(f"[INFO] Scraped page {page} - Total links collected so far: {len(all_links)}")

            try:
                next_button = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-test='pagination-next']"))
                )
                next_button.click()
                print(f"[INFO] Clicked 'Next Page' button on page {page}")
                time.sleep(10)
            except:
                print(f"[INFO] No 'Next Page' button found on page {page}. Ending link collection.")
                break

        except Exception as e:
            print(f"[ERROR] Issue on page {page}: {e}")
            traceback.print_exc()
            break

    print(f"[✅] Total company links collected: {len(all_links)}")
    return all_links

# ===== Scrape Company Details =====
def scrape_company_details(browser, url):
    try:
        browser.get(url)
        time.sleep(5)

        accept_cookies(browser)

        name = "N/A"
        email = "N/A"
        phone = "N/A"
        location = "N/A"

        try:
            name = browser.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            pass

        page_text = browser.page_source
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        found_emails = re.findall(email_pattern, page_text)
        if found_emails:
            email = found_emails[0]

        try:
            phone = browser.find_element(By.CLASS_NAME, "tel-number").text.strip()
        except:
            pass

        try:
            location = browser.find_element(By.CLASS_NAME, "company-card__info--address").text.strip()
        except:
            pass

        print(f"[INFO] Scraped: {name} | {email}")

        return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

    except Exception as e:
        print(f"[ERROR] Failed to scrape {url}: {e}")
        traceback.print_exc()
        return None

# ===== Save to CSV =====
def save_results(niche, data):
    safe_niche = re.sub(r'[^\w\s-]', '', niche).replace(" ", "_").lower()
    filename = f"{safe_niche}_companies.csv"
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Results saved as '{filename}'")

# ===== Main Execution =====
if __name__ == "__main__":
    # === Initialize Main Browser ===
    browser = init_browser()

    # === User Input ===
    niche = input("Enter the niche to search for: ").strip()

    while True:
        try:
            max_pages = int(input("Enter the number of pages to scrape (e.g., 5): ").strip())
            break
        except ValueError:
            print("[ERROR] Please enter a valid number.")

    # === Phase 1: Collect Links ===
    print("[INFO] Collecting company links...")
    company_links = collect_company_links(browser, niche, max_pages)
    browser.quit()

    # === Phase 2: Scrape Company Details ===
    print("[INFO] Scraping company details...")
    browser = init_browser()

    scraped_data = []
    for link in tqdm(company_links, desc="Scraping Progress", unit="company"):
        result = scrape_company_details(browser, link)
        if result:
            scraped_data.append(result)

    browser.quit()

    # === Phase 3: Save Results ===
    print("[INFO] Saving results...")
    save_results(niche, scraped_data)

    print(f"[✅] Scraping complete! Total Companies Scraped: {len(scraped_data)}")
