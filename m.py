from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run headless if needed
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

def get_company_links(browser, niche, max_pages):
    base_url = "https://www.europages.co.uk/"
    search_url = f"{base_url}en/showroom/machine"
    
    print(f"[INFO] Opening {search_url}")
    browser.get(search_url)
    time.sleep(5)
    
    company_links = []

    for page in range(1, max_pages + 1):
        print(f"[INFO] Scraping page {page}...")
        try:
            cards = browser.find_elements(By.CSS_SELECTOR, "div.ep-Products-item a")
            if not cards:
                print(f"[WARNING] No company cards found on page {page}")
                break

            for card in cards:
                link = card.get_attribute("href")
                if link:
                    company_links.append(link)

            # Click "Next Page" button if available
            next_buttons = browser.find_elements(By.CSS_SELECTOR, "a[aria-label='Next page']")
            if next_buttons:
                try:
                    next_buttons[0].click()
                    time.sleep(5)  # Wait for next page to load
                except Exception as e:
                    print(f"[WARNING] Couldn't click 'Next Page' button on page {page}: {e}")
                    break
            else:
                print(f"[INFO] No 'Next Page' button found on page {page}. Ending scraping.")
                break

        except Exception as e:
            print(f"[ERROR] Issue on page {page}: {e}")
            break

    print(f"[INFO] Total companies found: {len(company_links)}")
    return company_links

def scrape_company_details(browser, links):
    companies_with_emails = []
    companies_without_emails = []

    for i, link in enumerate(links):
        print(f"[INFO] Scraping company {i + 1}/{len(links)}: {link}")
        try:
            browser.get(link)
            time.sleep(3)

            # Extract company name
            name = "N/A"
            try:
                name_elem = browser.find_element(By.CSS_SELECTOR, "h1.ep-CompanyPage-companyName")
                name = name_elem.text if name_elem else "N/A"
            except:
                print("[WARNING] Company name not found")

            # Extract email (if available)
            email = "N/A"
            try:
                email_elem = browser.find_element(By.XPATH, "//a[contains(@href, 'mailto:')]")
                email = email_elem.get_attribute("href").replace("mailto:", "") if email_elem else "N/A"
            except:
                print("[WARNING] Email not found")

            # Append data to respective lists
            if email != "N/A":
                companies_with_emails.append((name, email, link))
            else:
                companies_without_emails.append((name, link))

        except Exception as e:
            print(f"[ERROR] Failed to scrape company at {link}: {e}")

    return companies_with_emails, companies_without_emails

def save_to_csv(filename, data, headers):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(data)
        print(f"[✅] File saved as '{filename}'")
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")

def main():
    niche = input("Enter the niche to search for: ").strip()
    max_pages = int(input("Enter the number of pages to scrape (e.g., 5): ").strip())
    
    browser = setup_browser()

    try:
        links = get_company_links(browser, niche, max_pages)
        companies_with_emails, companies_without_emails = scrape_company_details(browser, links)

        save_to_csv(f"{niche}_companies_with_emails.csv", companies_with_emails, ["Name", "Email", "Link"])
        save_to_csv(f"{niche}_companies_without_emails.csv", companies_without_emails, ["Name", "Link"])
    
        print("[✅] Scraping complete!")
        print(f"Extracted {len(companies_with_emails)} companies with emails and {len(companies_without_emails)} without emails.")
    
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    
    finally:
        browser.quit()

if __name__ == "__main__":
    main()
