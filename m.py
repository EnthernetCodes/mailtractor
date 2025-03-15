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
        chrome_options.add_argument("--headless")  # Headless mode for background execution
    
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)
    print("[INFO] Browser initialized.")
    return browser

# ======= Cookie Handling =======
def accept_cookies(browser):
    try:
        cookie_button = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept')]"))
        )
        cookie_button.click()
        print("[INFO] Cookie popup accepted.")
        time.sleep(2)
    except:
        print("[INFO] No cookie popup found.")

# ======= Scroll to Bottom =======
def scroll_to_load(browser):
    last_height = browser.execute_script("return document.body.scrollHeight")
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ======= Collect Company Links =======
def collect_company_links(browser, niche, max_pages):
    """ Collect all company profile links from search results first """
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)
    accept_cookies(browser)

    all_links = []
    for page in range(1, max_pages + 1):
        try:
            # Scroll and load all content
            scroll_to_load(browser)

            # Extract company links
            links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
            if not links:
                print(f"[INFO] No company links found on page {page}. Ending link collection.")
                break

            for link in links:
                href = link.get_attribute("href")

                # Fix: Avoid double base URL
               if href.startswith("http"):
                  full_link = href
               else:
                  full_link = f"https://www.europages.co.uk{href}"

               # Add the link if it's not already collected
               if full_link not in all_links:
                  all_links.append(full_link)

            print(f"[INFO] Scraped page {page} - Total links collected: {len(all_links)}")

            # Click "Next" button if available
            scroll_to_load(browser)
            try:
                next_button = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-test='pagination-next']"))
                )
                browser.execute_script("arguments[0].scrollIntoView(true);", next_button)
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

# ======= Scrape Company Details =======
def scrape_company_details(browser, url, retries=3):
    """ Scrape details from a company page using a single browser instance """
    attempt = 0
    while attempt < retries:
        try:
            browser.get(url)
            time.sleep(3)
            accept_cookies(browser)

            # Extract Company Details
            try:
                name = browser.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                name = "N/A"

            # Extract email using regex from page source
            page_text = browser.page_source
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, page_text)
            email = found_emails[0] if found_emails else "N/A"

            try:
                phone = browser.find_element(By.CLASS_NAME, "tel-number").text.strip()
            except:
                phone = "N/A"

            try:
                location = browser.find_element(By.CLASS_NAME, "company-card__info--address").text.strip()
            except:
                location = "N/A"

            return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

        except Exception as e:
            print(f"[ERROR] Failed to scrape {url} (Attempt {attempt + 1}/{retries}): {e}")
            traceback.print_exc()
            attempt += 1

    print(f"[ERROR] Skipped {url} after {retries} failed attempts.")
    return None

# ======= Save Results =======
def save_results(niche, data):
    safe_niche = re.sub(r'[^\w\s-]', '', niche).replace(" ", "_").lower()
    with open(f"{safe_niche}_companies.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Results saved as '{safe_niche}_companies.csv'")

# ======= Main =======
if __name__ == "__main__":
    browser = init_browser()

    niche = input("Enter the niche to search for: ").strip()

    while True:
        try:
            max_pages = int(input("Enter the number of pages to scrape (e.g., 5): ").strip())
            break
        except ValueError:
            print("[ERROR] Please enter a valid number.")

    # Phase 1: Collect Links
    print("[INFO] Collecting company links...")
    company_links = collect_company_links(browser, niche, max_pages)

    # Phase 2: Scrape Details with Single Browser Instance
    print("[INFO] Scraping company details...")
    scraped_data = []

    for link in tqdm(company_links, desc="Scraping Progress", unit="company"):
        result = scrape_company_details(browser, link)
        if result:
            scraped_data.append(result)

    # Phase 3: Save Results
    print("[INFO] Saving results...")
    save_results(niche, scraped_data)

    browser.quit()
    print(f"[✅] Scraping complete! Total Companies Scraped: {len(scraped_data)}")
