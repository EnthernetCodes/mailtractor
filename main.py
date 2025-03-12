import time
import traceback
import csv
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ===== Auto-Update ChromeDriver =====
def update_chromedriver():
    print("[INFO] Updating ChromeDriver to match the latest browser version...")
    driver_path = ChromeDriverManager().install()
    print(f"[INFO] ChromeDriver updated: {driver_path}")
    return driver_path

# ===== Ask User if They Want to See the Browser =====
show_browser = input("Do you want to open the browser and watch it work? (yes/no): ").strip().lower()

# ===== Configure Browser Options =====
chrome_options = Options()
if show_browser == "no":
    chrome_options.add_argument("--headless")  # Run in background mode

def init_browser():
    service = Service(update_chromedriver())  # Auto-updated ChromeDriver
    chrome_options.add_argument("--start-maximized")  # Full-screen mode
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)  # Wait up to 10 seconds for elements
    return browser

# ===== Accept Cookies if Popup Appears =====
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

# ===== Scroll to Load Dynamic Content =====
def scroll_to_load(browser):
    last_height = browser.execute_script("return document.body.scrollHeight")
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ===== Extract Company Links =====
def get_company_links(browser, niche, max_pages):
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)

    # Accept cookies at the start of scraping
    accept_cookies(browser)
    
    all_links = []

    for page in range(1, max_pages + 1):
        try:
            # Wait for elements to load
            WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-test='company-name']"))
            )

            # Scroll to load all results
            scroll_to_load(browser)

            # Extract links from the page
            links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
            for link in links:
                href = link.get_attribute("href")
                if href and href not in all_links:
                    all_links.append(href)

            print(f"[INFO] Scraped page {page} - Total links collected: {len(all_links)}")

            # Click "Next Page" button if available
            # Click "Next Page" button if available
            try:
               next_button = WebDriverWait(browser, 10).until(
              EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label='Next page']"))
               )
               browser.execute_script("arguments[0].scrollIntoView(true);", next_button)  # Scroll into view
               next_button.click()
               print(f"[INFO] Clicked 'Next Page' button on page {page}")
               time.sleep(10)  # Wait for next page to load
            except:
               print(f"[INFO] No 'Next Page' button found on page {page}. Ending scraping.")
               break

        except Exception as e:
            print(f"[ERROR] Issue on page {page}: {e}")
            traceback.print_exc()
            break
    
    return all_links

# ===== Extract Company Details =====
def get_company_details(browser, url):
    browser.get(url)
    time.sleep(5)  # Allow JavaScript to load

    # Accept cookies if they appear on company page
    accept_cookies(browser)

    # Extract Name
    try:
        name = browser.find_element(By.TAG_NAME, "h1").text.strip()
    except:
        name = "N/A"

    # Extract Email
    page_text = browser.page_source
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    found_emails = re.findall(email_pattern, page_text)
    email = found_emails[0] if found_emails else "N/A"

    # Extract Phone Number
    try:
        phone = browser.find_element(By.CLASS_NAME, "tel-number").text.strip()
    except:
        phone = "N/A"

    # Extract Location
    try:
        location = browser.find_element(By.CLASS_NAME, "company-card__info--address").text.strip()
    except:
        location = "N/A"

    return {"Name": name, "Email": email, "Phone": phone, "Location": location, "Profile URL": url}

# ===== Save Results to CSV Files =====
def save_results(niche, companies_with_email, companies_without_email):
    safe_niche = re.sub(r'[^\w\s-]', '', niche).replace(" ", "_").lower()

    # Save companies WITH email
    with open(f"{safe_niche}_companies_with_emails.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(companies_with_email)

    # Save companies WITHOUT email
    with open(f"{safe_niche}_companies_without_emails.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(companies_without_email)

    print(f"[✅] Files saved as '{safe_niche}_companies_with_emails.csv' and '{safe_niche}_companies_without_emails.csv'")

# ===== Main Execution =====
if __name__ == "__main__":
    browser = init_browser()
    
    # Ask user for search query
    niche = input("Enter the niche to search for: ").strip()
    
    # Ask user for number of pages to scrape
    while True:
        try:
            max_pages = int(input("Enter the number of pages to scrape (e.g., 5): ").strip())
            break
        except ValueError:
            print("[ERROR] Please enter a valid number.")

    # Scrape company links
    company_links = get_company_links(browser, niche, max_pages)

    # Lists to store categorized data
    companies_with_email = []
    companies_without_email = []

    # Extract details for each company
    for index, link in enumerate(company_links):
        print(f"[INFO] Scraping company {index + 1}/{len(company_links)}: {link}")
        details = get_company_details(browser, link)

        if details["Email"] != "N/A":
            companies_with_email.append(details)
        else:
            companies_without_email.append(details)

    # Save categorized results
    save_results(niche, companies_with_email, companies_without_email)

    print(f"[✅] Scraping complete! Extracted {len(companies_with_email)} companies with emails and {len(companies_without_email)} without emails.")
    browser.quit()
