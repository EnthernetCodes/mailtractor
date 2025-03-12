from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time

def scrape_companies(niche, pages):
    # Set up the browser
    driver = webdriver.Chrome()
    driver.get(f"https://www.europages.co.uk/en/showroom/{niche}")
    
    companies_with_emails = []
    companies_without_emails = []

    try:
        for page in range(1, pages + 1):
            print(f"Scraping page {page}/{pages}...")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.ep-product')))

            products = driver.find_elements(By.CSS_SELECTOR, '.ep-product')

            for product in products:
                try:
                    # Extract company name
                    company_name = product.find_element(By.CSS_SELECTOR, '.ep-product-title').text

                    # Check for email button
                    try:
                        email_button = product.find_element(By.CSS_SELECTOR, 'a[data-track="Email"]')
                        email_button.click()
                        time.sleep(1)  # Give time for email to pop up
                        email = driver.find_element(By.CSS_SELECTOR, '.ep-email-link').text
                        companies_with_emails.append((company_name, email))
                        print(f"[✅] {company_name} - {email}")
                    except:
                        companies_without_emails.append((company_name,))
                        print(f"[❌] {company_name} - No email found")

                except Exception as e:
                    print(f"[ERROR] Skipping company due to error: {e}")

            # Go to next page
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Next"]')
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                ActionChains(driver).move_to_element(next_button).click().perform()
                time.sleep(2)  # Give time for the next page to load
            except:
                print("[⚠️] No 'Next' button found. Stopping.")
                break

    except Exception as e:
        print(f"[ERROR] Unexpected issue: {e}")
    
    finally:
        # Save results to CSV
        with open(f'{niche}_companies_with_emails.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Company', 'Email'])
            writer.writerows(companies_with_emails)

        with open(f'{niche}_companies_without_emails.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Company'])
            writer.writerows(companies_without_emails)

        print(f"[✅] Files saved as '{niche}_companies_with_emails.csv' and '{niche}_companies_without_emails.csv'")
        driver.quit()
        print("[✅] Scraping complete!")

# Run the script
if __name__ == "__main__":
    niche = input("Enter the niche to search for: ")
    pages = int(input("Enter the number of pages to scrape: "))
    scrape_companies(niche, pages)
