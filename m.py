from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def init_driver():
    """Initialize the Chrome driver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run headless if you don't want the browser window to appear
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

def scrape_links(driver, search_url, pages_to_scrape):
    """Collect company links across multiple pages."""
    driver.get(search_url)
    company_links = []
    
    for page in range(pages_to_scrape):
        print(f"[INFO] Scraping page {page + 1}...")

        # Wait for links to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.company-link"))  # Adjust selector
            )
        except Exception as e:
            print(f"[WARNING] No links found on page {page + 1}. Error: {e}")
            break

        # Collect links on the current page
        links = driver.find_elements(By.CSS_SELECTOR, "a.company-link")  # Adjust selector
        for link in links:
            company_links.append(link.get_attribute("href"))

        print(f"[INFO] Links collected so far: {len(company_links)}")

        # Try to click the "Next Page" button, if available
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.next-page")  # Adjust selector
            next_button.click()
            WebDriverWait(driver, 10).until(EC.staleness_of(next_button))  # Wait for page refresh
        except:
            print("[INFO] No 'Next Page' button found. Ending link collection.")
            break

        time.sleep(2)  # Avoid rate limiting

    print(f"[✅] Total company links collected: {len(company_links)}")
    return company_links

def scrape_company_details(driver, links):
    """Visit each company link and scrape details."""
    for i, link in enumerate(links):
        driver.get(link)
        print(f"[INFO] Scraping company {i + 1}/{len(links)}: {link}")

        # Example: Extract company name (adjust selector)
        try:
            company_name = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.company-name"))  # Adjust selector
            ).text
            print(f"    Company Name: {company_name}")
        except:
            print("    [WARNING] Company name not found.")

        time.sleep(2)  # Avoid triggering rate limiting
    
    print("[✅] Company details scraping completed.")

def main():
    search_url = input("Enter the search URL: ").strip()
    pages_to_scrape = int(input("Enter the number of pages to scrape: "))

    driver = init_driver()

    try:
        # Step 1: Gather all links
        company_links = scrape_links(driver, search_url, pages_to_scrape)

        # Step 2: Scrape details after collecting all links
        if company_links:
            scrape_company_details(driver, company_links)
        else:
            print("[INFO] No links found to scrape.")

    finally:
        driver.quit()
        print("[INFO] Browser closed.")

if __name__ == "__main__":
    main()
