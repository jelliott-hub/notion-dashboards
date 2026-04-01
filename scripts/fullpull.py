import requests
import pandas as pd
import os

# ✅ Set Save Path
SAVE_PATH = "real_estate_data/"
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

# 🔹 Census API Setup
CENSUS_API_KEY = "56187e1aef6be6febae097f5f19acf72fb2b2514"
BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

# Variables to Pull
variables = {
    "B19013_001E": "Median_Household_Income",
    "B01003_001E": "Total_Population",
    "B23025_004E": "Total_Employed",  # ✅ Replaces FRED Job Growth
    "B25077_001E": "Median_Home_Value",
    "B25001_001E": "Total_Housing_Units"  # ✅ Replaces HUD Building Permits
}

# Years to Pull (Last 20 Years)
years = list(range(2009, 2023))

# Function to Fetch Census Data
def fetch_census_data(year):
    url = f"{BASE_URL.format(year=year)}?get={','.join(variables.keys())}&for=tract:*&in=state:48&key={CENSUS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        df["Year"] = year
        return df.rename(columns=variables)
    else:
        print(f"❌ Error fetching Census data for {year}: {response.status_code}")
        return None

# Collect Census Data
census_data = pd.concat([fetch_census_data(year) for year in years if fetch_census_data(year) is not None])
census_data.to_csv(SAVE_PATH + "census_data_texas.csv", index=False)
print("✅ Census data saved!")

# 🔹 Fetch Mortgage Rates from FRED
FRED_API_KEY = "896699d09fdff8e25793194055f62afd"
FRED_MORTGAGE_URL = f"https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key={FRED_API_KEY}&file_type=json"

response = requests.get(FRED_MORTGAGE_URL)
if response.status_code == 200:
    mortgage_df = pd.DataFrame(response.json()['observations'])
    mortgage_df["value"] = mortgage_df["value"].astype(float)
    mortgage_df["date"] = pd.to_datetime(mortgage_df["date"])
    mortgage_df["Year"] = mortgage_df["date"].dt.year
    mortgage_rates = mortgage_df.groupby("Year")["value"].mean().reset_index()
    mortgage_rates.rename(columns={"value": "Mortgage_Rate"}, inplace=True)
    mortgage_rates.to_csv(SAVE_PATH + "mortgage_rates.csv", index=False)
    print("✅ Mortgage rates saved!")
else:
    print("❌ Error fetching mortgage rates:", response.status_code)

# 🔹 Merge Census Data & Mortgage Rates
census_data = pd.read_csv(SAVE_PATH + "census_data_texas.csv")
mortgage_rates = pd.read_csv(SAVE_PATH + "mortgage_rates.csv")

# Merge on "Year"
final_data = census_data.merge(mortgage_rates, on="Year", how="left")

# Save Final Data
final_data.to_csv(SAVE_PATH + "final_merged_data.csv", index=False)

print("✅ Final dataset saved with Mortgage Rates!")