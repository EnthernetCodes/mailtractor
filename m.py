from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import csv
import re
import traceback


def update_chromedriver():
    """ Ensures the latest ChromeDriver is used """
    print("[INFO] Updating ChromeDriver...")
    driver_path = ChromeDriverManager().install()
    print(f"[INFO] ChromeDriver updated: {driver_path}")
    return driver_path


# Configure browser options
show_browser = input("Do you want to open the browser and watch it work? (yes/no): ").strip().lower()
chrome_options = Options()
if show_browser == "no":
    chrome_options.add_argument("--headless")  # Headless mode for background execution


def init_browser():
    """ Initialize the Selenium browser """
    service = Service(update_chromedriver())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)  # Implicit wait for element loading
    return browser


def accept_cookies(browser):
    """ Accept cookies if the popup appears """
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


def scroll_to_load(browser):
    """ Scroll to the bottom to load all dynamic content """
    last_height = browser.execute_script("return document.body.scrollHeight")
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Allow time for dynamic content to load
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def collect_company_links(browser, niche, max_pages):
    """ Collect all company profile links from search results first """
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)

    accept_cookies(browser)

    all_links = []

    for page in range(1, max_pages + 1):
        try:
            # Wait for company links to load
            WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.flex.flex-col.gap-1.flex-1 a.name"))
            )
            scroll_to_load(browser)

            # Extract company links
            links = browser.find_elements(By.CSS_SELECTOR, "div.flex.flex-col.gap-1.flex-1 a.name")
            for link in links:
                href = link.get_attribute("href")
                if href:
                    full_link = f"https://www.europages.co.uk{href}"
                    if full_link not in all_links:
                        all_links.append(full_link)

            print(f"[INFO] Scraped page {page} - Total links collected so far: {len(all_links)}")

            # Click "Next" button to navigate to the next page
            try:
                next_button = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-test='pagination-next']"))
                )
                next_button.click()
                print(f"[INFO] Clicked 'Next Page' button on page {page}")
                time.sleep(10)  # Wait for next page to load
            except:
                print(f"[INFO] No 'Next Page' button found on page {page}. Ending link collection.")
                break

        except Exception as e:
            print(f"[ERROR] Issue on page {page}: {e}")
            traceback.print_exc()
            break

    print(f"[✅] Total company links collected: {len(all_links)}")
    return all_links


def scrape_company_details(url, retries=3):
    """ Visit each company page and extract details: Name, Email, Phone, Location with retries """
    attempt = 0
    while attempt < retries:
        try:
            browser = init_browser()
            browser.get(url)
            time.sleep(5)

            accept_cookies(browser)

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

            browser.quit()
            return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

        except Exception as e:
            print(f"[ERROR] Failed to scrape {url} (Attempt {attempt + 1}/{retries}): {e}")
            traceback.print_exc()
            attempt += 1
            browser.quit()

    print(f"[ERROR] Skipped {url} after {retries} failed attempts.")
    return None


def save_results(niche, data):
    """ Save scraped results into a CSV file """
    safe_niche = re.sub(r'[^\w\s-]', '', niche).replace(" ", "_").lower()
    with open(f"{safe_niche}_companies.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Results saved as '{safe_niche}_companies.csv'")


if __name__ == "__main__":
    main_browser = init_browser()

    niche = input("Enter the niche to search for: ").strip()

    while True:
        try:
            max_pages = int(input("Enter the number of pages to scrape (e.g., 5): ").strip())
            break
        except ValueError:
            print("[ERROR] Please enter a valid number.")

    # Phase 1: Collect all company links first
    print("[INFO] Collecting company links...")
    company_links = collect_company_links(main_browser, niche, max_pages)
    main_browser.quit()

    # Phase 2: Scrape company details from collected links in parallel with a progress bar
    print("[INFO] Scraping company details...")
    scraped_data = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_company_details, link) for link in company_links]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Scraping Progress", unit="company"):
            result = future.result()
            if result:
                scraped_data.append(result)

    # Phase 3: Save results
    print("[INFO] Saving results...")
    save_results(niche, scraped_data)

    print(f"[✅] Scraping complete! Total Companies Scraped: {len(scraped_data)}")
