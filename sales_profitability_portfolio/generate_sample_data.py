import csv
import random
from datetime import date, timedelta
from pathlib import Path

RANDOM_SEED = 20261004
ROW_COUNT = 2500
OUTPUT_PATH = Path("data") / "sales.csv"

products = [
    ("Laptop", "Technology", 900, 1400, 0.18),
    ("Phone", "Technology", 300, 900, 0.22),
    ("Printer", "Technology", 120, 400, 0.16),
    ("Accessories", "Technology", 15, 200, 0.35),
    ("Paper", "Office Supplies", 10, 50, 0.20),
    ("Binder", "Office Supplies", 5, 80, 0.30),
    ("Storage", "Office Supplies", 15, 180, 0.25),
    ("Labels", "Office Supplies", 5, 30, 0.28),
    ("Chair", "Furniture", 60, 600, 0.18),
    ("Desk", "Furniture", 100, 900, 0.15),
    ("Bookcase", "Furniture", 90, 700, 0.20),
    ("Table", "Furniture", 120, 1000, 0.17),
]
locations = {
    "West": ["California", "Washington", "Oregon", "Nevada"],
    "East": ["New York", "Massachusetts", "New Jersey", "Virginia"],
    "Central": ["Illinois", "Ohio", "Colorado", "Minnesota"],
    "South": ["Texas", "Florida", "Georgia", "North Carolina"],
}
discount_levels = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
randomizer = random.Random(RANDOM_SEED)
start_date = date(2023, 1, 1)
end_date = date(2025, 12, 31)
days = (end_date - start_date).days
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

columns = [
    "order_id", "order_date", "country", "region", "state", "category",
    "product_name", "quantity", "sales", "discount", "profit",
]
with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    for i in range(1, ROW_COUNT + 1):
        product, category, price_low, price_high, margin = randomizer.choice(products)
        region = randomizer.choice(list(locations))
        state = randomizer.choice(locations[region])
        quantity = randomizer.randint(1, 8)
        discount = randomizer.choices(
            discount_levels, weights=[42, 7, 12, 10, 11, 9, 6, 3], k=1
        )[0]
        unit_price = randomizer.uniform(price_low, price_high)
        sales = round(quantity * unit_price * (1 - discount), 2)
        profit = round(
            sales * (margin - discount * 0.70) + randomizer.gauss(0, max(3, sales * 0.025)),
            2,
        )
        order_date = start_date + timedelta(days=randomizer.randint(0, days))
        writer.writerow({
            "order_id": f"ORD{i:05d}",
            "order_date": order_date.isoformat(),
            "country": "United States",
            "region": region,
            "state": state,
            "category": category,
            "product_name": product,
            "quantity": quantity,
            "sales": sales,
            "discount": "" if randomizer.random() < 0.008 else discount,
            "profit": "" if randomizer.random() < 0.004 else profit,
        })

print(f"Created {ROW_COUNT:,} simulated sales rows at {OUTPUT_PATH}")
