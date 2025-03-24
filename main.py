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
import re


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

    print("[INFO] Starting enhanced scroll...")

    while attempts < max_attempts:
        for _ in range(10):
            browser.execute_script("window.scrollBy(0, 200);")  # Small steps
            time.sleep(0.2)

        # Wait for new content to load
        new_height = browser.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            attempts += 1
            print(f"[INFO] No new content after scroll attempt {attempts}/{max_attempts}.")
            time.sleep(0.5)
        else:
            last_height = new_height
            attempts = 0  # Reset attempts if new content loads

    # Fast scroll up and down to catch any remaining lazy-loaded content
    print("[INFO] Fast up-down scrolling to catch lazy-loaded content...")
    for _ in range(3):
        browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)

    print("[✅] Enhanced scrolling complete. All content should be loaded.")


# ======= Collect All Page URLs =======
def collect_all_page_urls(browser, niche, max_pages):
    """ Collect all page URLs up to max_pages """
    base_url = "https://www.europages.co.uk/en/search"
    page_urls = [f"{base_url}?cserpRedirect=1&q={niche}"]
    accept_cookies(browser)

    for page in range(2, max_pages + 1):
        page_url = f"{base_url}/page/{page}?cserpRedirect=1&q={niche}"
        page_urls.append(page_url)
        print(f"[INFO] Collected page {page} URL: {page_url}")

    print(f"[✅] Total pages collected: {len(page_urls)}")
    return page_urls


# ======= Collect Company Links =======
def collect_company_links(browser, page_urls):
    """ Collect company profile links across all pages """
    all_links = []

    for i, url in enumerate(tqdm(page_urls, desc="Collecting Links", unit="page")):
        browser.get(url)
        enhanced_scroll_to_load(browser)

        # Extract company links
        links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
        if not links:
            print(f"[INFO] No company links found on page {i + 1}.")
            continue

        for link in links:
            href = link.get_attribute("href")
            full_link = href if href.startswith("http") else f"https://www.europages.co.uk{href}"

            if full_link not in all_links:
                all_links.append(full_link)

        print(f"[INFO] Page {i + 1}: Total links collected so far: {len(all_links)}")

    print(f"[✅] Total company links collected: {len(all_links)}")
    return all_links


# ======= Scrape Company Details =======
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
            try:
                name = browser.find_element(By.TAG_NAME, "h1").text.strip()
            except NoSuchElementException:
                name = "N/A"

            page_text = browser.page_source
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, page_text)
            email = found_emails[0] if found_emails else "N/A"

            try:
                phone = browser.find_element(By.CLASS_NAME, "tel-number").text.strip()
            except NoSuchElementException:
                phone = "N/A"

            try:
                location = browser.find_element(By.CLASS_NAME, "company-card__info--address").text.strip()
            except NoSuchElementException:
                location = "N/A"

            return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

        except Exception as e:
            print(f"[ERROR] Failed to scrape {url} (Attempt {attempt + 1}/{retries}): {e}")
            attempt += 1
            time.sleep(5)

    print(f"[ERROR] Skipped {url} after {retries} failed attempts.")
    return None


# ======= Export to CSV =======
def export_to_csv(data, filename="scraped_companies.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Data exported to '{filename}'")


# ======= Main =======
if __name__ == "__main__":
    browser = init_browser()
    browser.set_page_load_timeout(300)

    niche = input("Enter the niche to search for: ").strip()
    max_pages = int(input("Enter the number of pages to scrape: ").strip())

    page_urls = collect_all_page_urls(browser, niche, max_pages)
    company_links = collect_company_links(browser, page_urls)

    # Scrape details and export
    scraped_data = []
    for link in tqdm(company_links, desc="Scraping Details", unit="company"):
        result = scrape_company_details(browser, link)
        if result:
            scraped_data.append(result)

    export_to_csv(scraped_data)
    browser.quit()
    print("[✅] Scraping Complete!")
