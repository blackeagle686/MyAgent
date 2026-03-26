import pandas as pd
import numpy as np

# Set seed for reproducibility
np.random.seed(42)

# Generate 1000 rows
n_rows = 1000

data = {
    "id": np.arange(1, n_rows + 1),
    "category": np.random.choice(["Electronics", "Clothing", "Home", "Toys"], size=n_rows),
    "ad_spend": np.random.uniform(100, 5000, size=n_rows),
    "website_visits": np.random.randint(50, 10000, size=n_rows),
    "sales": np.zeros(n_rows)
}

# Create a relationship for sales
# sales = 50 + 0.5 * ad_spend + 0.01 * website_visits + noise
data["sales"] = 50 + (0.5 * data["ad_spend"]) + (0.01 * data["website_visits"]) + np.random.normal(0, 100, size=n_rows)

# Create a target for classification (high_sales = 1 if sales > median)
median_sales = np.median(data["sales"])
data["high_performance"] = (data["sales"] > median_sales).astype(int)

df = pd.DataFrame(data)

# Save to CSV
df.to_csv("test_data.csv", index=False)
print(f"Created 'test_data.csv' with {len(df)} rows and {len(df.columns)} columns.")
