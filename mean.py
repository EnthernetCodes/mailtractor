import asyncio
import aiohttp
import pandas as pd
import numpy as np
import re
import random
import joblib
from bs4 import BeautifulSoup
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from playwright.async_api import async_playwright

# List of User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

# Function to scrape Google & Europages
async def scrape_companies(niche, pages):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = await context.new_page()
        all_links = set()

        for page_number in range(1, pages + 1):
            search_query = f"{niche} site:europages.co.uk"
            url = f"https://www.google.com/search?q={search_query}&start={page_number * 10}"
            print(f"[INFO] Scraping Google page {page_number}...")

            await page.goto(url, timeout=30000)
            await asyncio.sleep(2)

            # Extract company links
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(href => href.includes('europages.co.uk') && href.includes('/en/company/'))
            """)
            all_links.update(links)

        await browser.close()
        return list(all_links)

# Function to extract company details
async def get_company_details(session, url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with session.get(url, headers=headers, timeout=10) as response:
        html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    name = soup.find("h1").text.strip() if soup.find("h1") else "N/A"
    email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.get_text())
    phone = soup.find("span", class_="tel-number").text.strip() if soup.find("span", class_="tel-number") else "N/A"
    location = soup.find("div", class_="company-card__info--address").text.strip() if soup.find("div", class_="company-card__info--address") else "N/A"

    return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone, "Location": location, "Profile URL": url}

# Function to train an email verification model
def train_email_classifier(df):
    df["Is Fake"] = df["Email"].apply(lambda x: 1 if "noreply" in x or "info@" in x else 0)
    
    X = df[["Profile URL Length", "Phone Length"]]
    y = df["Is Fake"]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, "email_classifier.pkl")

    print(f"[✅] Email Classifier Trained")

# Function to predict missing emails using deep learning
def train_email_prediction_model(df):
    X = df[["Profile URL Length", "Phone Length", "Location Length"]].values
    y = df["Has Email"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Sequential([
        Dense(64, activation="relu", input_shape=(X_scaled.shape[1],)),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid")
    ])

    model.compile(optimizer=Adam(learning_rate=0.001), loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(X_scaled, y, epochs=10, batch_size=16, validation_split=0.2)

    model.save("email_prediction_model.h5")
    joblib.dump(scaler, "scaler.pkl")

    print(f"[✅] Email Prediction Model Trained")

# Function to cluster companies using KMeans
def train_company_clustering(df):
    X = df[["Profile URL Length", "Phone Length", "Location Length"]].values
    kmeans = KMeans(n_clusters=4, random_state=42)
    df["Cluster"] = kmeans.fit_predict(X)
    
    joblib.dump(kmeans, "company_clusters.pkl")

    print(f"[✅] Companies Clustered into Groups")

# Function to generate a detailed report
def generate_report(df):
    report_name = "company_analysis_report.xlsx"
    df.to_excel(report_name, index=False)
    print(f"[✅] Report saved as {report_name}")

# Main execution function
async def main():
    niche = input("Enter the niche to search for: ").strip()
    pages = int(input("Enter number of pages to scrape (e.g., 5): ").strip())

    async with aiohttp.ClientSession() as session:
        company_links = await scrape_companies(niche, pages)

        # Scrape details from extracted links
        tasks = [get_company_details(session, link) for link in company_links]
        companies = await asyncio.gather(*tasks)

        df = pd.DataFrame(companies)
        df["Has Email"] = df["Email"].apply(lambda x: 1 if x != "N/A" else 0)
        df["Profile URL Length"] = df["Profile URL"].apply(lambda x: len(str(x)))
        df["Phone Length"] = df["Phone"].apply(lambda x: len(str(x)))
        df["Location Length"] = df["Location"].apply(lambda x: len(str(x)))

        # Train & apply ML models
        train_email_classifier(df)
        train_email_prediction_model(df)
        train_company_clustering(df)

        # Generate & save final report
        generate_report(df)

# Run the async event loop
if __name__ == "__main__":
    asyncio.run(main())
