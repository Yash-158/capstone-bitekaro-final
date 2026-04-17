"""
BiteKaro — Feature Engineering & Preprocessing
================================================
Prepares data for:
  1. Association Rules model  (basket-level co-occurrence)
  2. Collaborative Filtering  (user-item interaction matrix)
  3. Context Layer            (time + season + mood features)

Run:
    python3 preprocess.py

Output:
    data/processed/interaction_matrix.npz
    data/processed/basket_matrix.csv
    data/processed/user_features.csv
    data/processed/item_features.csv
    data/processed/feature_report.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from scipy.sparse import csr_matrix, save_npz
import joblib

from menu import ALL_ITEMS, ITEM_IDS, ID_TO_IDX, ITEM_LOOKUP

BASE  = os.path.dirname(os.path.abspath(__file__))
PROC  = os.path.join(BASE, "data", "processed")
os.makedirs(PROC, exist_ok=True)

print("=" * 60)
print("  BiteKaro — Preprocessing Pipeline")
print("=" * 60)

# ── Load raw data ─────────────────────────────────────────────────────────────
df_items    = pd.read_csv(f"{BASE}/data/orders.csv")
df_sessions = pd.read_csv(f"{BASE}/data/order_sessions.csv")
df_custs    = pd.read_csv(f"{BASE}/data/customers.csv")

print(f"\n  Loaded {len(df_items):,} item rows, {len(df_sessions):,} orders")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — Build Customer Index
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[1/5] Building customer index...")

all_customer_ids = df_sessions["customer_id"].unique().tolist()
CUST_TO_IDX      = {cid: idx for idx, cid in enumerate(all_customer_ids)}
IDX_TO_CUST      = {idx: cid for cid, idx in CUST_TO_IDX.items()}
N_CUSTOMERS      = len(all_customer_ids)
N_ITEMS          = len(ITEM_IDS)

print(f"  Customers : {N_CUSTOMERS}")
print(f"  Items     : {N_ITEMS}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — User-Item Interaction Matrix  (for Collaborative Filtering)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[2/5] Building user-item interaction matrix...")

# Count how many times each customer ordered each item
interaction_counts = (
    df_items.groupby(["customer_id", "item_id"])
    .size()
    .reset_index(name="count")
)

# Map to indices
interaction_counts["user_idx"] = interaction_counts["customer_id"].map(CUST_TO_IDX)
interaction_counts["item_idx"] = interaction_counts["item_id"].map(ID_TO_IDX)

# Drop any unmapped (shouldn't happen but defensive)
interaction_counts = interaction_counts.dropna(subset=["user_idx", "item_idx"])
interaction_counts = interaction_counts.astype({"user_idx": int, "item_idx": int})

# Build sparse matrix
row  = interaction_counts["user_idx"].values
col  = interaction_counts["item_idx"].values
data = interaction_counts["count"].values.astype(np.float32)

interaction_matrix = csr_matrix((data, (row, col)), shape=(N_CUSTOMERS, N_ITEMS))
save_npz(f"{PROC}/interaction_matrix.npz", interaction_matrix)

# Sparsity check
n_interactions = interaction_matrix.nnz
sparsity = 1 - n_interactions / (N_CUSTOMERS * N_ITEMS)
print(f"  Matrix shape  : {interaction_matrix.shape}")
print(f"  Non-zero cells: {n_interactions:,}")
print(f"  Sparsity      : {sparsity:.3f}  (lower = more data, good)")

# Save mapping
joblib.dump({"cust_to_idx": CUST_TO_IDX, "idx_to_cust": IDX_TO_CUST,
             "item_ids": ITEM_IDS, "id_to_idx": ID_TO_IDX},
            f"{PROC}/index_maps.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Basket Matrix  (for Association Rules)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[3/5] Building basket matrix for association rules...")

# One-hot encode each basket: rows=orders, columns=items, value=1/0
basket_rows = []
for _, row in df_sessions.iterrows():
    basket = json.loads(row["items"])
    entry  = {iid: 0 for iid in ITEM_IDS}
    for iid in basket:
        if iid in entry:
            entry[iid] = 1
    basket_rows.append(entry)

basket_df = pd.DataFrame(basket_rows)
basket_df.to_csv(f"{PROC}/basket_matrix.csv", index=False)
print(f"  Basket matrix shape: {basket_df.shape}")
print(f"  Avg items per basket: {basket_df.sum(axis=1).mean():.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — Item Feature Matrix  (for hybrid / cold-start)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[4/5] Building item feature matrix...")

# All unique tags across all items
all_tags = set()
for item in ALL_ITEMS:
    all_tags.update(item["tags"])
all_tags = sorted(all_tags)

# All categories
categories = ["hot_beverages", "cold_beverages", "snacks", "meals", "desserts"]

item_feature_rows = []
for iid in ITEM_IDS:
    item = ITEM_LOOKUP[iid]
    row  = {"item_id": iid, "item_name": item["name"]}

    # Category one-hot
    for cat in categories:
        row[f"cat_{cat}"] = 1 if item["category"] == cat else 0

    # Tag one-hot
    for tag in all_tags:
        row[f"tag_{tag}"] = 1 if tag in item["tags"] else 0

    # Numerical features (normalized)
    row["price_norm"] = item["price"] / 200.0   # max price ~200
    row["cal_norm"]   = item["cal"]  / 600.0    # max cal ~600

    item_feature_rows.append(row)

item_features_df = pd.DataFrame(item_feature_rows)
item_features_df.to_csv(f"{PROC}/item_features.csv", index=False)
feature_cols = [c for c in item_features_df.columns
                if c not in ["item_id", "item_name"]]
print(f"  Item features shape : {item_features_df.shape}")
print(f"  Feature columns     : {len(feature_cols)}")
print(f"  Tags encoded        : {len(all_tags)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — User Feature Matrix  (for hybrid / cold-start)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[5/5] Building user feature matrix...")

# Aggregate per-customer behavioral features from order history
cust_features = df_items.groupby("customer_id").agg(
    total_orders      = ("order_id", "nunique"),
    avg_order_value   = ("price", "mean"),
    pct_hot_bev       = ("category", lambda x: (x == "hot_beverages").mean()),
    pct_cold_bev      = ("category", lambda x: (x == "cold_beverages").mean()),
    pct_snacks        = ("category", lambda x: (x == "snacks").mean()),
    pct_meals         = ("category", lambda x: (x == "meals").mean()),
    pct_desserts      = ("category", lambda x: (x == "desserts").mean()),
    avg_hour          = ("hour", "mean"),
    pct_morning       = ("hour", lambda x: (x < 12).mean()),
    pct_afternoon     = ("hour", lambda x: ((x >= 12) & (x < 17)).mean()),
    pct_evening       = ("hour", lambda x: (x >= 17).mean()),
    pct_summer        = ("season", lambda x: (x == "summer").mean()),
    pct_monsoon       = ("season", lambda x: (x == "monsoon").mean()),
    pct_winter        = ("season", lambda x: (x == "winter").mean()),
).reset_index()

# Add profile from customers table
cust_features = cust_features.merge(
    df_custs[["customer_id", "profile", "is_vegetarian"]],
    on="customer_id", how="left"
)

# Profile one-hot
for p in ["morning_office_goer", "college_student", "family_visitor",
          "quick_lunch_person", "dessert_and_snack_lover"]:
    cust_features[f"profile_{p}"] = (cust_features["profile"] == p).astype(int)

# Normalize numerical
cust_features["total_orders_norm"] = (
    cust_features["total_orders"] / cust_features["total_orders"].max()
)
cust_features["avg_order_value_norm"] = (
    cust_features["avg_order_value"] / 200.0
)

cust_features.to_csv(f"{PROC}/user_features.csv", index=False)
print(f"  User features shape : {cust_features.shape}")


# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

report = f"""
BiteKaro — Feature Engineering Report
======================================

Dataset Summary
---------------
  Customers             : {N_CUSTOMERS:,}
  Menu Items            : {N_ITEMS}
  Total Interactions    : {len(df_items):,}
  Total Orders (baskets): {len(df_sessions):,}

Interaction Matrix
------------------
  Shape     : {N_CUSTOMERS} × {N_ITEMS}
  Non-zero  : {n_interactions:,}
  Sparsity  : {sparsity:.4f}
  Density   : {(1-sparsity):.4f}

Item Features  ({len(feature_cols)} features per item)
--------------
  Categories  : {len(categories)} one-hot columns
  Tags        : {len(all_tags)} one-hot columns
  Numerical   : price_norm, cal_norm (2 columns)
  All tags    : {', '.join(all_tags)}

User Features  ({cust_features.shape[1] - 2} features per user)
-------------
  Category pcts : pct_hot_bev, pct_cold_bev, pct_snacks, pct_meals, pct_desserts
  Time pcts     : pct_morning, pct_afternoon, pct_evening
  Season pcts   : pct_summer, pct_monsoon, pct_winter
  Profiles      : 5 one-hot columns
  Numerical     : total_orders_norm, avg_order_value_norm

Files Saved
-----------
  data/processed/interaction_matrix.npz
  data/processed/basket_matrix.csv
  data/processed/item_features.csv
  data/processed/user_features.csv
  data/processed/index_maps.pkl
"""

with open(f"{PROC}/feature_report.txt", "w") as f:
    f.write(report)

print(report)
print("  ✅ Preprocessing complete!")
print("=" * 60)
