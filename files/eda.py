"""
BiteKaro — Exploratory Data Analysis
=====================================
Validates that our synthetic data has the right real-world patterns.
Generates charts saved to data/eda_plots/

Run:
    python3 eda.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from itertools import combinations
from collections import Counter
import json

from menu import ALL_ITEMS, ITEM_LOOKUP, ITEM_NAMES

# ── Load data ─────────────────────────────────────────────────────────────────
BASE  = os.path.join(os.path.dirname(__file__), "..")
PLOTS = os.path.join(BASE, "data", "eda_plots")
os.makedirs(PLOTS, exist_ok=True)

df_items    = pd.read_csv(f"{BASE}/data/orders.csv")
df_sessions = pd.read_csv(f"{BASE}/data/order_sessions.csv")
df_custs    = pd.read_csv(f"{BASE}/data/customers.csv")

sns.set_theme(style="whitegrid", palette="Blues_d")
COLORS = sns.color_palette("Blues_d", 10)

print("=" * 60)
print("  BiteKaro — Exploratory Data Analysis")
print("=" * 60)
print(f"\n📦 Dataset Shape:")
print(f"   orders.csv      : {df_items.shape}")
print(f"   order_sessions  : {df_sessions.shape}")
print(f"   customers.csv   : {df_custs.shape}")

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 1 — Item popularity (overall)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n📊 [1/6] Item Popularity...")
item_counts = df_items["item_name"].value_counts()

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(item_counts.index[::-1], item_counts.values[::-1],
               color=sns.color_palette("Blues_d", len(item_counts)))
ax.set_xlabel("Total Orders", fontsize=12)
ax.set_title("Item Popularity — Overall Order Frequency", fontsize=14, fontweight="bold")
for bar, val in zip(bars, item_counts.values[::-1]):
    ax.text(val + 100, bar.get_y() + bar.get_height()/2,
            f"{val:,}", va="center", fontsize=9)
plt.tight_layout()
plt.savefig(f"{PLOTS}/01_item_popularity.png", dpi=150, bbox_inches="tight")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 2 — Category distribution by hour (time-of-day pattern)
# ═══════════════════════════════════════════════════════════════════════════════

print("📊 [2/6] Time-of-Day Patterns...")
hour_cat = df_items.groupby(["hour", "category"]).size().unstack(fill_value=0)
hour_cat_pct = hour_cat.div(hour_cat.sum(axis=1), axis=0)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

hour_cat.plot(kind="bar", stacked=True, ax=ax1,
              colormap="tab10", width=0.85)
ax1.set_title("Orders by Hour and Category (Absolute)", fontsize=13, fontweight="bold")
ax1.set_xlabel("Hour of Day")
ax1.set_ylabel("Number of Orders")
ax1.legend(loc="upper right", fontsize=9)
ax1.set_xticklabels([str(h) for h in hour_cat.index], rotation=0)

hour_cat_pct.plot(kind="bar", stacked=True, ax=ax2,
                  colormap="tab10", width=0.85)
ax2.set_title("Category Share by Hour (Percentage)", fontsize=13, fontweight="bold")
ax2.set_xlabel("Hour of Day")
ax2.set_ylabel("Proportion")
ax2.legend(loc="upper right", fontsize=9)
ax2.set_xticklabels([str(h) for h in hour_cat_pct.index], rotation=0)

plt.tight_layout()
plt.savefig(f"{PLOTS}/02_time_of_day.png", dpi=150, bbox_inches="tight")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 3 — Seasonal patterns
# ═══════════════════════════════════════════════════════════════════════════════

print("📊 [3/6] Seasonal Patterns...")
season_cat = df_items.groupby(["season", "category"]).size().unstack(fill_value=0)
season_order = ["summer", "monsoon", "autumn", "winter"]
season_cat   = season_cat.reindex(season_order)
season_cat_pct = season_cat.div(season_cat.sum(axis=1), axis=0)

fig, ax = plt.subplots(figsize=(10, 6))
season_cat_pct.plot(kind="bar", stacked=False, ax=ax,
                    colormap="Set2", width=0.7)
ax.set_title("Category Preference by Season (Ahmedabad)", fontsize=13, fontweight="bold")
ax.set_xlabel("Season")
ax.set_ylabel("Proportion of Orders")
ax.legend(loc="upper right", fontsize=9)
ax.set_xticklabels(season_order, rotation=0)
plt.tight_layout()
plt.savefig(f"{PLOTS}/03_seasonal.png", dpi=150, bbox_inches="tight")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 4 — Co-occurrence heatmap (cross-sell validation)
# ═══════════════════════════════════════════════════════════════════════════════

print("📊 [4/6] Co-occurrence Heatmap...")
item_names_list = [i["name"] for i in ALL_ITEMS]
cooc_matrix     = pd.DataFrame(0, index=item_names_list, columns=item_names_list)

for _, row in df_sessions.iterrows():
    basket = json.loads(row["items"])
    names  = [ITEM_LOOKUP[i]["name"] for i in basket if i in ITEM_LOOKUP]
    for a, b in combinations(names, 2):
        cooc_matrix.loc[a, b] += 1
        cooc_matrix.loc[b, a] += 1

fig, ax = plt.subplots(figsize=(14, 12))
mask = np.eye(len(item_names_list), dtype=bool)
sns.heatmap(cooc_matrix, ax=ax, cmap="Blues", mask=mask,
            xticklabels=True, yticklabels=True,
            linewidths=0.3, linecolor="lightgray")
ax.set_title("Item Co-occurrence Matrix\n(How often items are ordered together)",
             fontsize=13, fontweight="bold")
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8)
plt.tight_layout()
plt.savefig(f"{PLOTS}/04_cooccurrence.png", dpi=150, bbox_inches="tight")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 5 — Customer profile distribution + orders per customer
# ═══════════════════════════════════════════════════════════════════════════════

print("📊 [5/6] Customer Profiles...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

profile_counts = df_custs["profile"].value_counts()
ax1.pie(profile_counts.values, labels=profile_counts.index,
        autopct="%1.1f%%", startangle=140,
        colors=sns.color_palette("Set2", len(profile_counts)))
ax1.set_title("Customer Profile Distribution", fontsize=13, fontweight="bold")

ax2.hist(df_custs["n_orders"], bins=30, color=COLORS[4], edgecolor="white")
ax2.set_title("Orders per Customer Distribution", fontsize=13, fontweight="bold")
ax2.set_xlabel("Number of Orders per Customer")
ax2.set_ylabel("Number of Customers")
ax2.axvline(df_custs["n_orders"].mean(), color="red",
            linestyle="--", label=f"Mean: {df_custs['n_orders'].mean():.1f}")
ax2.legend()

plt.tight_layout()
plt.savefig(f"{PLOTS}/05_customers.png", dpi=150, bbox_inches="tight")
plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 6 — Mood × Category heatmap
# ═══════════════════════════════════════════════════════════════════════════════

print("📊 [6/6] Mood Patterns...")
mood_cat = df_items.groupby(["mood", "category"]).size().unstack(fill_value=0)
mood_cat_pct = mood_cat.div(mood_cat.sum(axis=1), axis=0)

fig, ax = plt.subplots(figsize=(9, 5))
sns.heatmap(mood_cat_pct, annot=True, fmt=".2f", cmap="Blues",
            ax=ax, linewidths=0.5, linecolor="lightgray")
ax.set_title("Category Ordering Probability by Mood", fontsize=13, fontweight="bold")
ax.set_xlabel("Category")
ax.set_ylabel("Mood")
plt.tight_layout()
plt.savefig(f"{PLOTS}/06_mood_category.png", dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  SUMMARY STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("  KEY STATISTICS")
print("=" * 60)
print(f"\n  Top 5 Most Ordered Items:")
for name, cnt in item_counts.head(5).items():
    print(f"    {name:<22} {cnt:>6,} orders")

print(f"\n  Peak ordering hours (top 3):")
hourly = df_items["hour"].value_counts().head(3)
for h, cnt in hourly.items():
    print(f"    {h:02d}:00  →  {cnt:,} items")

print(f"\n  Category revenue share:")
cat_rev = df_items.groupby("category")["price"].sum().sort_values(ascending=False)
total   = cat_rev.sum()
for cat, rev in cat_rev.items():
    print(f"    {cat:<20} ₹{rev:>8,.0f}  ({rev/total*100:.1f}%)")

print(f"\n  Average basket size by profile:")
profile_basket = df_sessions.groupby("profile")["n_items"].mean().sort_values(ascending=False)
for p, avg in profile_basket.items():
    print(f"    {p:<30} {avg:.2f} items/order")

print(f"\n  Season vs cold/hot beverage check:")
for season in ["summer", "monsoon", "winter"]:
    sub = df_items[df_items["season"] == season]
    cold = (sub["category"] == "cold_beverages").sum()
    hot  = (sub["category"] == "hot_beverages").sum()
    total_s = len(sub)
    print(f"    {season:<10}: cold={cold/total_s*100:.1f}%  hot={hot/total_s*100:.1f}%")

print("\n  ✅ All 6 plots saved to data/eda_plots/")
print("=" * 60)
