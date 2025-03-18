import time
import traceback
import csv
import re
import os
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm


# ====== Auto-Update ChromeDriver ======
def update_chromedriver():
    print("[INFO] Updating ChromeDriver to match the latest browser version...")
    driver_path = ChromeDriverManager().install()
    print(f"[INFO] ChromeDriver updated: {driver_path}")
    return driver_path


# ====== Initialize Browser ======
def init_browser(headless=False):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")

    service = Service(update_chromedriver())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(10)
    browser.set_page_load_timeout(300)
    print("[INFO] Browser initialized.")
    return browser


# ====== Cookie Management ======
def save_cookies(browser, path="cookies.pkl"):
    """Save cookies to a file."""
    with open(path, "wb") as file:
        pickle.dump(browser.get_cookies(), file)
    print("[✅] Cookies saved!")


def load_cookies(browser, path="cookies.pkl"):
    """Load cookies from a file."""
    if os.path.exists(path):
        with open(path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                browser.add_cookie(cookie)
        print("[✅] Cookies loaded!")


# ====== Register and Login ======
def register_and_login(browser, email, password, first_name="John", last_name="Doe"):
    """Register and log in to Europages."""
    try:
        print("[INFO] Attempting login...")

        browser.get("https://www.europages.co.uk/login/")
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "email")))

        browser.find_element(By.ID, "email").send_keys(email)
        browser.find_element(By.ID, "password").send_keys(password)
        browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Wait for login to complete
        time.sleep(5)

        # Save cookies after successful login
        save_cookies(browser)

        print("[✅] Logged in successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return False


# ====== Accept Cookies ======
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


# ====== Enhanced Scrolling ======
def enhanced_scroll_to_load(browser, max_attempts=10):
    """ Thorough scrolling to load all dynamic content. """
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
            attempts = 0

    print("[✅] Enhanced scrolling complete.")


# ====== Extract Company Links ======
def get_company_links(browser, niche, max_pages):
    search_url = f"https://www.europages.co.uk/en/search?cserpRedirect=1&q={niche}"
    browser.get(search_url)
    accept_cookies(browser)

    all_links = []

    for page in range(1, max_pages + 1):
        try:
            enhanced_scroll_to_load(browser)
            links = browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")
            for link in links:
                href = link.get_attribute("href")
                if href and href not in all_links:
                    all_links.append(href)

            print(f"[INFO] Scraped page {page} - Total links collected: {len(all_links)}")

            try:
                next_button = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label='Next page']"))
                )
                next_button.click()
                time.sleep(10)
            except:
                print(f"[INFO] No 'Next Page' button found on page {page}. Ending scraping.")
                break

        except Exception as e:
            print(f"[ERROR] Issue on page {page}: {e}")
            traceback.print_exc()
            break

    return all_links


# ====== Export Results ======
def export_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Name", "Email", "Phone", "Location", "Profile URL"])
        writer.writeheader()
        writer.writerows(data)
    print(f"[✅] Data exported to '{filename}'")


# ====== Main Execution ======
def main():
    browser = init_browser()

    niche = input("Enter the niche to search for: ").strip()
    max_pages = int(input("Enter the number of pages to scrape: ").strip())
    scrape_with_account = input("Scrape with account? (yes/no): ").strip().lower()

    if scrape_with_account == "yes":
        email = input("Enter your Europages email: ").strip()
        password = input("Enter your Europages password: ").strip()

        # Load cookies if available
        print("[INFO] Checking for saved cookies...")
        browser.get("https://www.europages.co.uk/")
        load_cookies(browser)

        # Refresh to apply cookies
        browser.refresh()
        time.sleep(3)

        # Check if already logged in
        if "/account" not in browser.current_url:
            print("[INFO] Not logged in. Attempting login...")
            if not register_and_login(browser, email, password):
                print("[ERROR] Could not log in.")
                browser.quit()
                return

    company_links = get_company_links(browser, niche, max_pages)
    export_to_csv([{"Profile URL": link} for link in company_links], f"{niche}_company_links.csv")

    print(f"[✅] Scraping complete! Extracted {len(company_links)} links.")
    browser.quit()


if __name__ == "__main__":
    main()
