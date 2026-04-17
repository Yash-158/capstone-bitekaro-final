"""
BiteKaro — Real Data Adapter (Bakery Dataset → BiteKaro Format)
================================================================
Takes the real UK Bakery dataset (9,465 transactions) and converts it
into the exact same CSV format that preprocess.py and train.py expect.

What is REAL (from actual cafe transactions):
  - Basket co-occurrence patterns
  - Time of day purchase behavior
  - Item popularity rankings
  - Basket size distribution
  - Seasonal patterns (from real dates)

What is SYNTHETICALLY ADDED (BiteKaro context):
  - Indian item names (mapped from bakery items)
  - Customer IDs (generated with realistic return behavior)
  - Mood labels (derived from Daypart)
  - Customer profiles (assigned based on visit patterns)
  - Loyalty points behavior

Usage:
  1. Place Bakery.csv inside files/data/
  2. Run: python adapt_bakery.py
  3. Then run: python preprocess.py
  4. Then run: python train.py

Output files (in files/data/):
  - orders.csv          (item-level, one row per item per order)
  - order_sessions.csv  (basket-level, one row per order)
  - customers.csv       (customer profiles)
"""

import os
import sys
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

INPUT_CSV = os.path.join(DATA_DIR, "Bakery.csv")
if not os.path.exists(INPUT_CSV):
    print(f"ERROR: {INPUT_CSV} not found.")
    print("Please place Bakery.csv inside the files/data/ folder.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 1 — ITEM MAPPING
#  Maps real bakery items → BiteKaro's 25 Indian cafe items
#  Mapping logic: functional similarity
#  (e.g. Coffee → Cappuccino, Hot chocolate → Hot Chocolate direct match)
# ─────────────────────────────────────────────────────────────────────────────

ITEM_MAP = {
    # HOT BEVERAGES
    "Coffee":              "HB02",   # Cappuccino — closest coffee match
    "Tea":                 "HB03",   # Masala Chai — tea equivalent
    "Hot chocolate":       "HB05",   # Hot Chocolate — direct match
    "Gingerbread syrup":   "HB03",   # Masala Chai — spiced flavour
    "Drinking chocolate spoons": "HB05",  # Hot Chocolate
    "Coffee granules":     "HB01",   # Espresso — concentrated coffee

    # COLD BEVERAGES
    "Juice":               "CB02",   # Mango Shake — fruit drink
    "Coke":                "CB03",   # Lemonade — cold drink
    "Mineral water":       "CB04",   # Iced Tea — light cold drink
    "Smoothies":           "CB05",   # Cold Brew — premium cold drink
    "My-5 Fruit Shoot":    "CB02",   # Mango Shake — fruit drink

    # SNACKS
    "Pastry":              "SN01",   # Samosa — fried pastry snack
    "Medialuna":           "SN01",   # Samosa — crescent pastry
    "Scone":               "SN04",   # Dhokla — light baked snack
    "Toast":               "SN05",   # Poha — light breakfast item
    "Baguette":            "SN02",   # Vada Pav — bread-based snack
    "Bread":               "SN02",   # Vada Pav — bread snack
    "Jam":                 "SN05",   # Poha — light accompaniment
    "Tartine":             "SN03",   # Bread Pakoda — bread-based
    "Granola":             "SN05",   # Poha — light grain breakfast
    "Crisps":              "SN01",   # Samosa — crunchy snack
    "Bare Popcorn":        "SN04",   # Dhokla — light snack
    "Scandinavian":        "SN03",   # Bread Pakoda — baked snack
    "Alfajores":           "SN04",   # Dhokla — light sweet snack

    # MEALS
    "Sandwich":            "ML03",   # Paneer Wrap — wrap/sandwich
    "Farm House":          "ML01",   # Masala Dosa — full hearty meal
    "Soup":                "ML02",   # Pav Bhaji — hot thick meal
    "Spanish Brunch":      "ML05",   # Upma — brunch meal
    "Chicken Stew":        "ML02",   # Pav Bhaji — thick stew equivalent
    "Hearty & Seasonal":   "ML01",   # Masala Dosa — hearty meal
    "Salad":               "SN04",   # Dhokla — light healthy option
    "Frittata":            "ML05",   # Upma — egg/grain dish
    "Tiffin":              "ML05",   # Upma — tiffin box meal
    "Eggs":                "ML05",   # Upma — breakfast meal
    "Tacos/Fajita":        "ML03",   # Paneer Wrap — wrap equivalent
    "Empanadas":           "SN01",   # Samosa — filled pastry
    "Vegan Feast":         "ML01",   # Masala Dosa — full veg meal
    "Focaccia":            "SN03",   # Bread Pakoda — bread snack
    "Pintxos":             "SN01",   # Samosa — small snack bites
    "Crepes":              "ML05",   # Upma — light flat meal
    "Muesli":              "SN05",   # Poha — grain breakfast

    # DESSERTS
    "Cake":                "DS02",   # Gulab Jamun — sweet dessert
    "Brownie":             "DS03",   # Brownie — direct match
    "Muffin":              "DS01",   # Chocolate Muffin — direct match
    "Cookies":             "DS05",   # Rasgulla — round sweet
    "Fudge":               "DS04",   # Kulfi — dense sweet confection
    "Truffles":            "DS04",   # Kulfi — rich chocolate sweet
    "Jammie Dodgers":      "DS05",   # Rasgulla — round sweet biscuit
    "Tiffin":              "DS01",   # Chocolate Muffin — chocolate treat
    "Bakewell":            "DS02",   # Gulab Jamun — sweet almond tart
    "Victorian Sponge":    "DS02",   # Gulab Jamun — sponge cake
    "Lemon and coconut":   "DS05",   # Rasgulla — light sweet
    "Caramel bites":       "DS04",   # Kulfi — caramel sweet
    "Dulce de Leche":      "DS04",   # Kulfi — milk sweet
    "Chocolates":          "DS03",   # Brownie — chocolate
    "Raspberry shortbread sandwich": "DS05",  # Rasgulla
    "Cherry me Dried fruit": "DS02", # Gulab Jamun
    "Bread Pudding":       "DS01",   # Chocolate Muffin — bread dessert
    "Panatone":            "DS01",   # Chocolate Muffin — sweet bread
    "Vegan mincepie":      "DS02",   # Gulab Jamun — small sweet pie
    "Art Tray":            "DS03",   # Brownie — dessert tray
    "Half slice Monster":  "DS03",   # Brownie — large cake slice
    "Mighty Protein":      "DS01",   # Chocolate Muffin — protein snack
    "Afternoon with the baker": "DS02",  # Gulab Jamun — afternoon sweet
    "Pick and Mix Bowls":  "DS05",   # Rasgulla — mixed sweets
    "Kids biscuit":        "DS05",   # Rasgulla — sweet biscuit
    "Keeping It Local":    "ML01",   # Masala Dosa — local special
    "The Nomad":           "ML03",   # Paneer Wrap — nomad meal
    "Extra Salami or Feta": "ML03",  # Paneer Wrap — extra topping
    "Brioche and salami":  "ML03",   # Paneer Wrap — bread + filling
    "Chicken sand":        "ML03",   # Paneer Wrap — sandwich
    "The BART":            "ML03",   # Paneer Wrap — sandwich special

    # IGNORE these (non-food, gift items, misc)
    "Tshirt":              None,
    "Valentine's card":    None,
    "Postcard":            None,
    "Basket":              None,
    "Nomad bag":           None,
    "Fairy Doors":         None,
    "Bowl Nic Pitt":       None,
    "Chimichurri Oil":     None,
    "Spread":              None,
    "Siblings":            None,
    "Hack the stack":      None,
    "Adjustment":          None,
    "Gift voucher":        None,
    "Raw bars":            None,
    "Duck egg":            None,
    "Ella's Kitchen Pouches": None,
    "Honey":               None,
    "Olum & polenta":      None,
    "Polenta":             None,
    "Argentina Night":     None,
    "Christmas common":    None,
    "Mortimer":            None,
    "Bacon":               None,
    "Corn syrup":          None,
}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 2 — BITEKARO ITEM METADATA
#  Prices, categories, names for all 25 items
# ─────────────────────────────────────────────────────────────────────────────

ITEM_META = {
    "HB01": {"name": "Espresso",          "category": "hot_beverages",  "price": 80},
    "HB02": {"name": "Cappuccino",         "category": "hot_beverages",  "price": 120},
    "HB03": {"name": "Masala Chai",        "category": "hot_beverages",  "price": 60},
    "HB04": {"name": "Filter Coffee",      "category": "hot_beverages",  "price": 70},
    "HB05": {"name": "Hot Chocolate",      "category": "hot_beverages",  "price": 130},
    "CB01": {"name": "Cold Coffee",        "category": "cold_beverages", "price": 140},
    "CB02": {"name": "Mango Shake",        "category": "cold_beverages", "price": 120},
    "CB03": {"name": "Lemonade",           "category": "cold_beverages", "price": 80},
    "CB04": {"name": "Iced Tea",           "category": "cold_beverages", "price": 90},
    "CB05": {"name": "Cold Brew",          "category": "cold_beverages", "price": 160},
    "SN01": {"name": "Samosa",             "category": "snacks",         "price": 30},
    "SN02": {"name": "Vada Pav",           "category": "snacks",         "price": 40},
    "SN03": {"name": "Bread Pakoda",       "category": "snacks",         "price": 50},
    "SN04": {"name": "Dhokla",             "category": "snacks",         "price": 60},
    "SN05": {"name": "Poha",               "category": "snacks",         "price": 60},
    "ML01": {"name": "Masala Dosa",        "category": "meals",          "price": 120},
    "ML02": {"name": "Pav Bhaji",          "category": "meals",          "price": 110},
    "ML03": {"name": "Paneer Wrap",        "category": "meals",          "price": 130},
    "ML04": {"name": "Chole Bhature",      "category": "meals",          "price": 140},
    "ML05": {"name": "Upma",               "category": "meals",          "price": 80},
    "DS01": {"name": "Chocolate Muffin",   "category": "desserts",       "price": 80},
    "DS02": {"name": "Gulab Jamun",        "category": "desserts",       "price": 60},
    "DS03": {"name": "Brownie",            "category": "desserts",       "price": 90},
    "DS04": {"name": "Kulfi",              "category": "desserts",       "price": 70},
    "DS05": {"name": "Rasgulla",           "category": "desserts",       "price": 50},
}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 3 — CONTEXT MAPPINGS
# ─────────────────────────────────────────────────────────────────────────────

def get_season(month):
    """Ahmedabad seasonal mapping"""
    if month in [3, 4, 5, 6]:  return "summer"
    if month in [7, 8, 9]:     return "monsoon"
    if month in [10]:           return "autumn"
    return "winter"                              # Nov, Dec, Jan, Feb

def get_daypart_hour(daypart):
    """Convert Daypart string to representative hour + range"""
    mapping = {
        "Morning":   (random.randint(7, 10),  "morning"),
        "Afternoon": (random.randint(12, 16), "afternoon"),
        "Evening":   (random.randint(17, 20), "evening"),
        "Night":     (random.randint(20, 22), "evening"),
    }
    return mapping.get(daypart, (random.randint(9, 18), "afternoon"))

def assign_mood(daypart, items_in_basket):
    """
    Assign mood based on Daypart + items ordered.
    Logic mirrors real customer behavior.
    """
    has_hot_bev  = any(ITEM_META.get(i, {}).get("category") == "hot_beverages"
                       for i in items_in_basket)
    has_cold_bev = any(ITEM_META.get(i, {}).get("category") == "cold_beverages"
                       for i in items_in_basket)
    has_meal     = any(ITEM_META.get(i, {}).get("category") == "meals"
                       for i in items_in_basket)
    has_dessert  = any(ITEM_META.get(i, {}).get("category") == "desserts"
                       for i in items_in_basket)

    if daypart == "Morning":
        if has_hot_bev: return "tired"      # morning coffee = tired customer
        return random.choice(["tired", "hungry"])
    elif daypart == "Afternoon":
        if has_cold_bev: return "thirsty"
        if has_dessert:  return "happy"
        return random.choice(["thirsty", "happy"])
    elif daypart in ["Evening", "Night"]:
        if has_meal:    return "hungry"
        if has_dessert: return "happy"
        return random.choice(["hungry", "happy"])
    return random.choice(["happy", "thirsty", "hungry", "tired"])

def assign_profile(visit_count, preferred_daypart, preferred_category):
    """
    Assign one of 5 customer profiles based on behavioral patterns.
    """
    if preferred_daypart == "Morning" and preferred_category in ["hot_beverages", "snacks"]:
        return "morning_office_goer"
    if preferred_daypart == "Afternoon" and preferred_category in ["cold_beverages", "desserts"]:
        return "college_student"
    if preferred_category == "meals" and visit_count <= 10:
        return "family_visitor"
    if preferred_category in ["meals", "cold_beverages"] and visit_count >= 15:
        return "quick_lunch_person"
    if preferred_category in ["desserts", "snacks"]:
        return "dessert_and_snack_lover"
    # Default based on visit frequency
    if visit_count >= 20:
        return "morning_office_goer"
    return random.choice([
        "morning_office_goer", "college_student",
        "quick_lunch_person", "dessert_and_snack_lover"
    ])

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 4 — CUSTOMER ASSIGNMENT
#  The bakery dataset has NO customer IDs.
#  We generate realistic customer IDs using a power-law distribution
#  (few customers visit very often, most visit rarely — real cafe pattern).
# ─────────────────────────────────────────────────────────────────────────────

def generate_customer_assignments(n_transactions, n_customers=2500):
    """
    Assign customer IDs to transactions using power-law distribution.
    This simulates: regulars (visit 20+ times) + occasionals + one-timers.
    
    Distribution roughly:
      - 10% customers = heavy users (15-40 visits each)
      - 30% customers = medium users (5-14 visits each)
      - 60% customers = light users  (1-4 visits each)
    """
    customer_ids = [f"C{i+1:05d}" for i in range(n_customers)]

    # Build visit probability weights using power law
    weights = np.array([1 / (i + 1) ** 0.6 for i in range(n_customers)],
                       dtype=float)
    weights /= weights.sum()

    assignments = np.random.choice(customer_ids, size=n_transactions, p=weights)
    return assignments.tolist()

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 5 — MAIN ADAPTER
# ─────────────────────────────────────────────────────────────────────────────

def adapt():
    print("=" * 60)
    print("  BiteKaro — Bakery Data Adapter")
    print("=" * 60)

    # ── Load raw bakery data ─────────────────────────────────────────────────
    print(f"\n  Loading {INPUT_CSV}...")
    df_raw = pd.read_csv(INPUT_CSV)
    df_raw["DateTime"] = pd.to_datetime(df_raw["DateTime"])
    df_raw["month"]    = df_raw["DateTime"].dt.month
    df_raw["day_of_week"] = df_raw["DateTime"].dt.dayofweek

    print(f"  Raw rows       : {len(df_raw):,}")
    print(f"  Transactions   : {df_raw['TransactionNo'].nunique():,}")
    print(f"  Unique items   : {df_raw['Items'].nunique()}")

    # ── Map items ────────────────────────────────────────────────────────────
    print("\n  Mapping items to BiteKaro IDs...")
    df_raw["item_id"] = df_raw["Items"].map(ITEM_MAP)

    # Show mapping coverage
    unmapped = df_raw[df_raw["item_id"].isna()]["Items"].value_counts()
    mapped_count = df_raw["item_id"].notna().sum()
    print(f"  Mapped rows    : {mapped_count:,} / {len(df_raw):,} "
          f"({mapped_count/len(df_raw)*100:.1f}%)")
    print(f"  Dropped (non-food/misc): {df_raw['item_id'].isna().sum():,}")

    # Drop unmapped rows (non-food items)
    df_mapped = df_raw[df_raw["item_id"].notna()].copy()
    df_mapped = df_mapped.reset_index(drop=True)

    # ── Build transaction-level baskets ──────────────────────────────────────
    print("\n  Building baskets...")
    baskets = df_mapped.groupby("TransactionNo").agg(
        items    = ("item_id",    list),
        datetime = ("DateTime",   "first"),
        daypart  = ("Daypart",    "first"),
        month    = ("month",      "first"),
        dow      = ("day_of_week","first"),
        daytype  = ("DayType",    "first"),
    ).reset_index()

    # Remove duplicates within each basket (same item mapped twice)
    baskets["items"] = baskets["items"].apply(
        lambda x: list(dict.fromkeys(x))   # preserves order, removes dupes
    )
    # Keep only baskets with at least 1 item
    baskets = baskets[baskets["items"].apply(len) >= 1].reset_index(drop=True)

    n_transactions = len(baskets)
    print(f"  Valid baskets  : {n_transactions:,}")
    print(f"  Avg basket size: {baskets['items'].apply(len).mean():.2f}")

    # ── Assign customer IDs ──────────────────────────────────────────────────
    print("\n  Assigning customer IDs (power-law distribution)...")
    customer_assignments = generate_customer_assignments(n_transactions, n_customers=2000)
    baskets["customer_id"] = customer_assignments

    # ── Build per-customer behavioral profile ────────────────────────────────
    print("  Building customer profiles...")
    cust_stats = defaultdict(lambda: {
        "visits": 0,
        "dayparts": [],
        "categories": [],
    })

    for _, row in baskets.iterrows():
        cid  = row["customer_id"]
        cats = [ITEM_META[i]["category"] for i in row["items"] if i in ITEM_META]
        cust_stats[cid]["visits"]    += 1
        cust_stats[cid]["dayparts"].append(row["daypart"])
        cust_stats[cid]["categories"].extend(cats)

    # Assign visit_num per customer (1st visit, 2nd visit, etc.)
    visit_counter = defaultdict(int)
    visit_nums    = []
    for _, row in baskets.iterrows():
        cid = row["customer_id"]
        visit_counter[cid] += 1
        visit_nums.append(visit_counter[cid])
    baskets["visit_num"] = visit_nums

    # ── Assign mood and profile per transaction ──────────────────────────────
    moods    = []
    profiles = []

    for _, row in baskets.iterrows():
        cid     = row["customer_id"]
        stats   = cust_stats[cid]
        mood    = assign_mood(row["daypart"], row["items"])

        # Dominant daypart and category for this customer
        if stats["dayparts"]:
            from collections import Counter
            dom_daypart = Counter(stats["dayparts"]).most_common(1)[0][0]
            dom_cat     = Counter(stats["categories"]).most_common(1)[0][0] \
                          if stats["categories"] else "hot_beverages"
        else:
            dom_daypart = "Morning"
            dom_cat     = "hot_beverages"

        profile = assign_profile(stats["visits"], dom_daypart, dom_cat)

        moods.append(mood)
        profiles.append(profile)

    baskets["mood"]    = moods
    baskets["profile"] = profiles

    # ── Build customer summary table ─────────────────────────────────────────
    print("  Building customers.csv...")
    cust_records = []
    all_cust_ids = baskets["customer_id"].unique()

    for cid in all_cust_ids:
        stats      = cust_stats[cid]
        n_orders   = stats["visits"]
        dom_daypart = "Morning"
        dom_cat     = "hot_beverages"

        if stats["dayparts"]:
            from collections import Counter
            dom_daypart = Counter(stats["dayparts"]).most_common(1)[0][0]
        if stats["categories"]:
            from collections import Counter
            dom_cat = Counter(stats["categories"]).most_common(1)[0][0]

        profile = assign_profile(n_orders, dom_daypart, dom_cat)
        cust_records.append({
            "customer_id":   cid,
            "profile":       profile,
            "is_vegetarian": True,     # All BiteKaro items are veg
            "n_orders":      n_orders,
        })

    df_customers = pd.DataFrame(cust_records)
    print(f"  Unique customers: {len(df_customers):,}")
    print(f"  Profile distribution:")
    for p, cnt in df_customers["profile"].value_counts().items():
        print(f"    {p:<35} {cnt}")

    # ── Build order_sessions.csv ─────────────────────────────────────────────
    print("\n  Building order_sessions.csv...")
    session_rows = []
    order_id_counter = 1

    for _, row in baskets.iterrows():
        items   = row["items"]
        total   = sum(ITEM_META[i]["price"] for i in items if i in ITEM_META)
        hour, _ = get_daypart_hour(row["daypart"])
        season  = get_season(row["month"])

        order_id = f"ORD{order_id_counter:07d}"
        order_id_counter += 1

        session_rows.append({
            "order_id":    order_id,
            "customer_id": row["customer_id"],
            "profile":     row["profile"],
            "date":        row["datetime"].strftime("%Y-%m-%d"),
            "hour":        hour,
            "month":       row["month"],
            "day_of_week": row["dow"],
            "season":      season,
            "mood":        row["mood"],
            "n_items":     len(items),
            "total":       total,
            "items":       json.dumps(items),
            "visit_num":   row["visit_num"],
            "is_repeat":   row["visit_num"] > 1,
        })

    df_sessions = pd.DataFrame(session_rows)

    # ── Build orders.csv (item-level) ────────────────────────────────────────
    print("  Building orders.csv...")
    item_rows = []
    for session in session_rows:
        items  = json.loads(session["items"])
        for item_id in items:
            if item_id not in ITEM_META:
                continue
            meta = ITEM_META[item_id]
            item_rows.append({
                "order_id":           session["order_id"],
                "customer_id":        session["customer_id"],
                "profile":            session["profile"],
                "item_id":            item_id,
                "item_name":          meta["name"],
                "category":           meta["category"],
                "price":              meta["price"],
                "date":               session["date"],
                "hour":               session["hour"],
                "month":              session["month"],
                "day_of_week":        session["day_of_week"],
                "season":             session["season"],
                "mood":               session["mood"],
                "is_repeat_customer": session["is_repeat"],
                "visit_num":          session["visit_num"],
            })

    df_items = pd.DataFrame(item_rows)

    # ── Save all three files ─────────────────────────────────────────────────
    print("\n  Saving output files...")

    sessions_path  = os.path.join(DATA_DIR, "order_sessions.csv")
    items_path     = os.path.join(DATA_DIR, "orders.csv")
    customers_path = os.path.join(DATA_DIR, "customers.csv")

    df_sessions.to_csv(sessions_path,  index=False)
    df_items.to_csv(items_path,        index=False)
    df_customers.to_csv(customers_path, index=False)

    # ── Final summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ADAPTER COMPLETE — Summary")
    print("=" * 60)
    print(f"  Source transactions : {df_raw['TransactionNo'].nunique():,} (real bakery data)")
    print(f"  Valid baskets       : {len(df_sessions):,}")
    print(f"  Item interactions   : {len(df_items):,}")
    print(f"  Unique customers    : {len(df_customers):,}")
    print(f"  Unique items used   : {df_items['item_id'].nunique()} / 25")
    print(f"  Date range          : {df_sessions['date'].min()} to {df_sessions['date'].max()}")
    print()
    print(f"  Category distribution:")
    for cat, cnt in df_items["category"].value_counts().items():
        print(f"    {cat:<22} {cnt:>5} items  ({cnt/len(df_items)*100:.1f}%)")
    print()
    print(f"  Top 10 most ordered items:")
    for item, cnt in df_items["item_name"].value_counts().head(10).items():
        print(f"    {item:<25} {cnt:>5}")
    print()
    print(f"  Mood distribution:")
    for mood, cnt in df_items["mood"].value_counts().items():
        print(f"    {mood:<12} {cnt:>5} ({cnt/len(df_items)*100:.1f}%)")
    print()
    print(f"  Season distribution:")
    for s, cnt in df_items["season"].value_counts().items():
        print(f"    {s:<12} {cnt:>5} ({cnt/len(df_items)*100:.1f}%)")
    print()
    print("  Files saved:")
    print(f"    {items_path}")
    print(f"    {sessions_path}")
    print(f"    {customers_path}")
    print()
    print("  NEXT STEPS:")
    print("    1. python preprocess.py")
    print("    2. python train.py")
    print("    3. python evaluate.py  (optional — check F1 improvement)")
    print("    4. uvicorn serve:app --host 0.0.0.0 --port 5000 --reload")
    print("=" * 60)


if __name__ == "__main__":
    adapt()