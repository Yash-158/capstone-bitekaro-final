"""
BiteKaro — Synthetic Dataset Generator
======================================
Generates realistic cafe ordering data for Ahmedabad, India.

Design philosophy:
  - Customer profiles drive 70% of ordering behavior (realistic bias)
  - Real-world patterns baked in: time-of-day, season, pairings
  - 30% random "exploration" orders to prevent perfect overfitting
  - Target: ~3000 customers × avg 20 orders = ~60,000 rows

Run:
    python3 generate_dataset.py
    
Output:
    ../data/orders.csv          — one row per item per order
    ../data/customers.csv       — customer profiles
    ../data/order_sessions.csv  — one row per order (basket level)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import json

from menu import ALL_ITEMS, ITEM_IDS, ITEM_LOOKUP, NATURAL_PAIRINGS

# ── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Configuration ─────────────────────────────────────────────────────────────
N_CUSTOMERS       = 3000
DATE_RANGE_DAYS   = 365        # 1 full year of data
START_DATE        = datetime(2024, 1, 1)
EXPLORATION_RATE  = 0.30       # 30% orders are "random exploration"
PAIRING_PROB      = 0.65       # 65% chance of adding a natural pair item


# ═══════════════════════════════════════════════════════════════════════════════
#  1. CUSTOMER PROFILES
# ═══════════════════════════════════════════════════════════════════════════════

CUSTOMER_PROFILES = {
    "morning_office_goer": {
        "weight":           0.22,
        "preferred_cats":   ["hot_beverages", "snacks"],
        "avoid_cats":       ["desserts"],
        "peak_hours":       list(range(7, 11)),          # 7–10am
        "visit_frequency":  (18, 30),                    # (min, max) orders/year
        "avg_items":        (1, 3),
        "mood_dist":        {"tired": 0.5, "hungry": 0.3, "happy": 0.2, "thirsty": 0.0},
    },
    "college_student": {
        "weight":           0.28,
        "preferred_cats":   ["cold_beverages", "snacks", "desserts"],
        "avoid_cats":       [],
        "peak_hours":       list(range(13, 19)),         # 1–6pm
        "visit_frequency":  (12, 25),
        "avg_items":        (2, 4),
        "mood_dist":        {"happy": 0.4, "thirsty": 0.35, "hungry": 0.25, "tired": 0.0},
    },
    "family_visitor": {
        "weight":           0.18,
        "preferred_cats":   ["meals", "hot_beverages", "desserts"],
        "avoid_cats":       [],
        "peak_hours":       list(range(11, 14)) + list(range(18, 21)),
        "visit_frequency":  (6, 15),
        "avg_items":        (3, 6),                      # families order more
        "mood_dist":        {"happy": 0.6, "hungry": 0.4, "tired": 0.0, "thirsty": 0.0},
    },
    "quick_lunch_person": {
        "weight":           0.18,
        "preferred_cats":   ["meals", "cold_beverages"],
        "avoid_cats":       ["desserts"],
        "peak_hours":       list(range(12, 15)),
        "visit_frequency":  (20, 40),                    # workday regulars
        "avg_items":        (1, 2),
        "mood_dist":        {"hungry": 0.6, "tired": 0.3, "happy": 0.1, "thirsty": 0.0},
    },
    "dessert_and_snack_lover": {
        "weight":           0.14,
        "preferred_cats":   ["desserts", "snacks", "cold_beverages"],
        "avoid_cats":       ["meals"],
        "peak_hours":       list(range(15, 20)),         # evening crowd
        "visit_frequency":  (10, 20),
        "avg_items":        (2, 4),
        "mood_dist":        {"happy": 0.5, "thirsty": 0.3, "hungry": 0.2, "tired": 0.0},
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#  2. TIME-OF-DAY WEIGHTS  (per category)
# ═══════════════════════════════════════════════════════════════════════════════

def time_weight(category: str, hour: int) -> float:
    """Returns a multiplier for how likely a category is at a given hour."""
    weights = {
        "hot_beverages":  {range(6,11): 2.5, range(11,15): 0.8, range(15,18): 1.2,
                           range(18,22): 1.5, range(22,24): 0.3, range(0,6): 0.1},
        "cold_beverages": {range(6,11): 0.5, range(11,15): 1.5, range(15,20): 2.5,
                           range(20,24): 1.0, range(0,6): 0.1},
        "snacks":         {range(6,11): 1.5, range(11,12): 1.0, range(12,15): 0.8,
                           range(15,20): 2.0, range(20,24): 1.2, range(0,6): 0.1},
        "meals":          {range(6,11): 0.4, range(11,15): 3.0, range(15,18): 0.5,
                           range(18,22): 2.5, range(22,24): 0.3, range(0,6): 0.1},
        "desserts":       {range(6,11): 0.3, range(11,15): 1.0, range(15,20): 1.8,
                           range(20,24): 2.0, range(0,6): 0.1},
    }
    for time_range, w in weights.get(category, {}).items():
        if hour in time_range:
            return w
    return 1.0


# ═══════════════════════════════════════════════════════════════════════════════
#  3. SEASONAL WEIGHTS  (Ahmedabad climate)
# ═══════════════════════════════════════════════════════════════════════════════

def season_weight(category: str, month: int) -> float:
    """
    Ahmedabad seasons:
      Summer  : Mar–Jun  (hot and dry, up to 45°C)
      Monsoon : Jul–Sep  (humid, occasional rain)
      Winter  : Nov–Feb  (cool, 10–25°C)
      Autumn  : Oct      (transition)
    """
    summer  = month in [3, 4, 5, 6]
    monsoon = month in [7, 8, 9]
    winter  = month in [11, 12, 1, 2]

    if category == "cold_beverages":
        if summer:  return 2.8
        if monsoon: return 1.4
        if winter:  return 0.5
    elif category == "hot_beverages":
        if summer:  return 0.6
        if monsoon: return 1.3
        if winter:  return 2.2
    elif category == "snacks":
        if monsoon: return 1.8   # pakoda + chai in monsoon is iconic
        if winter:  return 1.4
    elif category == "desserts":
        if summer:  return 1.5   # kulfi, cold desserts
        if winter:  return 1.2   # warm gulab jamun
    return 1.0


# ═══════════════════════════════════════════════════════════════════════════════
#  4. ITEM SELECTOR
# ═══════════════════════════════════════════════════════════════════════════════

# Pre-group items by category for fast access
ITEMS_BY_CAT = {}
for item in ALL_ITEMS:
    ITEMS_BY_CAT.setdefault(item["category"], []).append(item["id"])


def pick_items_for_order(profile_name: str, hour: int, month: int,
                          n_items: int, previous_orders: list) -> list:
    """
    Returns a list of item IDs for one order.
    
    Logic:
      1. Decide which categories to draw from (profile preference + time + season)
      2. Pick a primary item
      3. With PAIRING_PROB, add its natural pair
      4. If n_items > 2, add more items (biased by profile, time, season)
      5. 30% chance of pure random exploration item
    """
    profile  = CUSTOMER_PROFILES[profile_name]
    selected = []

    # ── Step 1: Score all categories ────────────────────────────────────────
    cat_scores = {}
    for cat in ITEMS_BY_CAT:
        base = 2.0 if cat in profile["preferred_cats"] else 1.0
        base = 0.1 if cat in profile["avoid_cats"]    else base
        cat_scores[cat] = base * time_weight(cat, hour) * season_weight(cat, month)

    cats       = list(cat_scores.keys())
    cat_probs  = np.array([cat_scores[c] for c in cats], dtype=float)
    cat_probs /= cat_probs.sum()

    # ── Step 2: Pick primary category and item ──────────────────────────────
    primary_cat  = np.random.choice(cats, p=cat_probs)
    primary_item = random.choice(ITEMS_BY_CAT[primary_cat])
    selected.append(primary_item)

    # ── Step 3: Add natural pair ─────────────────────────────────────────────
    if random.random() < PAIRING_PROB and primary_item in NATURAL_PAIRINGS:
        pair_candidates = NATURAL_PAIRINGS[primary_item]
        pair = random.choice(pair_candidates)
        if pair not in selected:
            selected.append(pair)

    # ── Step 4: Add more items up to n_items ────────────────────────────────
    attempts = 0
    while len(selected) < n_items and attempts < 20:
        attempts += 1
        if random.random() < EXPLORATION_RATE:
            # Pure random exploration
            candidate = random.choice(ITEM_IDS)
        else:
            # Biased by profile + time + season
            extra_cat  = np.random.choice(cats, p=cat_probs)
            candidate  = random.choice(ITEMS_BY_CAT[extra_cat])
        if candidate not in selected:
            selected.append(candidate)

    # ── Step 5: Repeat item boost (returning customers) ─────────────────────
    # 40% chance to include something from their last order (habit)
    if previous_orders and random.random() < 0.40:
        recent_items = [item for order in previous_orders[-3:] for item in order]
        if recent_items:
            repeat_item = random.choice(recent_items)
            if repeat_item not in selected:
                selected[0] = repeat_item   # replace primary with habit item

    return selected[:n_items]


# ═══════════════════════════════════════════════════════════════════════════════
#  5. MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dataset():
    print("=" * 60)
    print("  BiteKaro Synthetic Dataset Generator")
    print("=" * 60)

    all_orders      = []   # order-level (basket)
    all_order_items = []   # item-level (one row per item)
    all_customers   = []   # customer profiles

    order_id_counter = 1

    profile_names   = list(CUSTOMER_PROFILES.keys())
    profile_weights = [CUSTOMER_PROFILES[p]["weight"] for p in profile_names]

    for cust_idx in range(N_CUSTOMERS):
        if cust_idx % 500 == 0:
            print(f"  Generating customer {cust_idx}/{N_CUSTOMERS}...")

        # ── Assign customer profile ──────────────────────────────────────────
        profile_name = random.choices(profile_names, weights=profile_weights, k=1)[0]
        profile      = CUSTOMER_PROFILES[profile_name]
        customer_id  = f"C{cust_idx+1:05d}"

        # ── Determine visit frequency for this customer ──────────────────────
        min_v, max_v  = profile["visit_frequency"]
        n_visits      = random.randint(min_v, max_v)

        # ── Track dietary preference (vegetarian — all our items are veg,
        #    but we store it for future non-veg extension) ────────────────────
        is_vegetarian = random.random() < 0.75   # 75% veg (Ahmedabad demographic)

        all_customers.append({
            "customer_id":   customer_id,
            "profile":       profile_name,
            "is_vegetarian": is_vegetarian,
            "n_orders":      n_visits,
        })

        previous_orders = []

        for visit_num in range(n_visits):
            # ── Pick a random date within the year ──────────────────────────
            order_date = START_DATE + timedelta(days=random.randint(0, DATE_RANGE_DAYS - 1))
            month      = order_date.month

            # ── Pick hour from profile's peak hours (with some noise) ────────
            if random.random() < 0.70:
                hour = random.choice(profile["peak_hours"])
            else:
                hour = random.randint(8, 21)   # off-peak visit

            # ── Mood (influences context layer later, stored for analysis) ───
            mood_dist = profile["mood_dist"]
            mood = random.choices(
                list(mood_dist.keys()),
                weights=list(mood_dist.values())
            )[0]

            # ── Number of items in this order ────────────────────────────────
            min_i, max_i = profile["avg_items"]
            n_items      = random.randint(min_i, max_i)

            # ── Pick items ───────────────────────────────────────────────────
            items = pick_items_for_order(
                profile_name, hour, month, n_items, previous_orders
            )
            previous_orders.append(items)

            # ── Compute order total ──────────────────────────────────────────
            total = sum(ITEM_LOOKUP[i]["price"] for i in items)

            order_id = f"ORD{order_id_counter:07d}"
            order_id_counter += 1

            # ── Order-level record ───────────────────────────────────────────
            all_orders.append({
                "order_id":    order_id,
                "customer_id": customer_id,
                "profile":     profile_name,
                "date":        order_date.strftime("%Y-%m-%d"),
                "hour":        hour,
                "month":       month,
                "day_of_week": order_date.weekday(),   # 0=Mon, 6=Sun
                "season":      get_season(month),
                "mood":        mood,
                "n_items":     len(items),
                "total":       total,
                "items":       json.dumps(items),       # stored as JSON array
                "visit_num":   visit_num + 1,
                "is_repeat":   visit_num > 0,
            })

            # ── Item-level records (one row per item) ─────────────────────────
            for item_id in items:
                item = ITEM_LOOKUP[item_id]
                all_order_items.append({
                    "order_id":    order_id,
                    "customer_id": customer_id,
                    "profile":     profile_name,
                    "item_id":     item_id,
                    "item_name":   item["name"],
                    "category":    item["category"],
                    "price":       item["price"],
                    "date":        order_date.strftime("%Y-%m-%d"),
                    "hour":        hour,
                    "month":       month,
                    "day_of_week": order_date.weekday(),
                    "season":      get_season(month),
                    "mood":        mood,
                    "is_repeat_customer": visit_num > 0,
                    "visit_num":   visit_num + 1,
                })

    # ── Save to CSV ──────────────────────────────────────────────────────────
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    base = os.path.join(os.path.dirname(__file__), "..")

    df_orders  = pd.DataFrame(all_orders)
    df_items   = pd.DataFrame(all_order_items)
    df_custs   = pd.DataFrame(all_customers)

    df_orders.to_csv( f"{base}/data/order_sessions.csv", index=False)
    df_items.to_csv(  f"{base}/data/orders.csv",         index=False)
    df_custs.to_csv(  f"{base}/data/customers.csv",      index=False)

    print("\n" + "=" * 60)
    print(f"  ✅ Customers   : {len(df_custs):,}")
    print(f"  ✅ Orders      : {len(df_orders):,}")
    print(f"  ✅ Order-Items : {len(df_items):,}")
    print(f"  ✅ Avg items/order: {df_orders['n_items'].mean():.2f}")
    print(f"  ✅ Avg orders/customer: {df_custs['n_orders'].mean():.1f}")
    print("=" * 60)
    print("\n  Files saved:")
    print(f"    data/customers.csv")
    print(f"    data/order_sessions.csv")
    print(f"    data/orders.csv")
    print("=" * 60)

    return df_orders, df_items, df_custs


def get_season(month: int) -> str:
    if month in [3, 4, 5, 6]:  return "summer"
    if month in [7, 8, 9]:     return "monsoon"
    if month in [10]:           return "autumn"
    return "winter"


if __name__ == "__main__":
    generate_dataset()
