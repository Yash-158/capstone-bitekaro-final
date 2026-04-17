"""
BiteKaro — Model Evaluation & Visualization
=============================================
Generates a complete visual evaluation report for the recommendation system.

Charts produced:
  1. Precision@K and Recall@K across K values
  2. Hit/Miss matrix by customer profile (confusion matrix equivalent)
  3. Association Rules — Confidence vs Lift scatter plot
  4. Recommendation accuracy by category
  5. Season vs Category heatmap (context layer proof)
  6. SVD item embedding visualization (PCA 2D)
  7. Summary scorecard

Run:
    python evaluate.py

Output:
    data/eval_plots/  — all PNG charts
    data/eval_plots/evaluation_summary.txt
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import json
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy.sparse import load_npz
from sklearn.decomposition import PCA

from menu import ALL_ITEMS, ITEM_IDS, ITEM_LOOKUP, ID_TO_IDX

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
MODELS    = os.path.join(BASE, "models")
PROC      = os.path.join(BASE, "data", "processed")
EVAL_DIR  = os.path.join(BASE, "data", "eval_plots")
os.makedirs(EVAL_DIR, exist_ok=True)

# ── Load everything ───────────────────────────────────────────────────────────
print("=" * 60)
print("  BiteKaro — Model Evaluation Report")
print("=" * 60)

assoc_data  = joblib.load(os.path.join(MODELS, "association_rules.pkl"))
svd_data    = joblib.load(os.path.join(MODELS, "svd_model.pkl"))
pop_data    = joblib.load(os.path.join(MODELS, "popularity_baseline.pkl"))
index_maps  = joblib.load(os.path.join(PROC, "index_maps.pkl"))

df_items    = pd.read_csv(os.path.join(BASE, "data", "orders.csv"))
df_sessions = pd.read_csv(os.path.join(BASE, "data", "order_sessions.csv"))
df_custs    = pd.read_csv(os.path.join(BASE, "data", "customers.csv"))
interaction = load_npz(os.path.join(PROC, "interaction_matrix.npz"))

RULES_DF    = assoc_data["rules_df"]
USER_FACTORS = svd_data["user_factors"]
ITEM_FACTORS = svd_data["item_factors"]
CUST_TO_IDX  = svd_data["cust_to_idx"]
POP_OVERALL  = pop_data["overall"]

sns.set_theme(style="whitegrid")
PALETTE = sns.color_palette("Blues_d", 10)

print("  All models and data loaded\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  EVALUATION HELPER — Leave-Last-Order-Out
# ═══════════════════════════════════════════════════════════════════════════════

def build_test_set():
    """Build test pairs: (customer_id, profile, held_out_items)"""
    df_sorted  = df_sessions.sort_values(["customer_id", "visit_num"])
    test_pairs = []
    for cust_id, group in df_sorted.groupby("customer_id"):
        if len(group) < 3:
            continue
        last_order = group.iloc[-1]
        held_items = json.loads(last_order["items"])
        profile    = last_order["profile"]
        test_pairs.append((cust_id, profile, held_items))
    return test_pairs

def predict_top_k(customer_id, k, exclude_items=[]):
    """Get top-K recommendations for a customer."""
    if customer_id in CUST_TO_IDX:
        u_idx    = CUST_TO_IDX[customer_id]
        scores   = ITEM_FACTORS @ USER_FACTORS[u_idx]
        model    = "svd"
    else:
        scores   = np.array([POP_OVERALL.get(iid, 0) for iid in ITEM_IDS])
        model    = "popularity"

    # Mask excluded items
    for iid in exclude_items:
        if iid in ID_TO_IDX:
            scores[ID_TO_IDX[iid]] = -999

    top_k_idx = np.argsort(scores)[::-1][:k]
    return [ITEM_IDS[i] for i in top_k_idx], model

print("  Building test set...")
test_pairs = build_test_set()
print(f"  Test pairs: {len(test_pairs):,}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 1 — Precision@K and Recall@K
# ═══════════════════════════════════════════════════════════════════════════════

print("  [1/7] Precision@K and Recall@K...")

k_values   = [1, 2, 3, 5, 8, 10]
precisions = []
recalls    = []
f1_scores  = []

for k in k_values:
    p_list, r_list = [], []
    for cust_id, profile, held_items in test_pairs[:1000]:  # sample for speed
        top_k, _ = predict_top_k(cust_id, k)
        hits      = len(set(top_k) & set(held_items))
        p_list.append(hits / k)
        r_list.append(hits / len(held_items) if held_items else 0)
    p = np.mean(p_list)
    r = np.mean(r_list)
    f = 2 * p * r / (p + r + 1e-10)
    precisions.append(p)
    recalls.append(r)
    f1_scores.append(f)

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(k_values))
w = 0.25
bars1 = ax.bar(x - w, precisions, w, label="Precision@K", color="#1565C0", alpha=0.85)
bars2 = ax.bar(x,     recalls,    w, label="Recall@K",    color="#42A5F5", alpha=0.85)
bars3 = ax.bar(x + w, f1_scores,  w, label="F1@K",        color="#90CAF9", alpha=0.85)

for bar in list(bars1) + list(bars2) + list(bars3):
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h + 0.002,
            f"{h:.3f}", ha="center", va="bottom", fontsize=7.5)

ax.set_xticks(x)
ax.set_xticklabels([f"K={k}" for k in k_values])
ax.set_xlabel("K (Number of Recommendations)", fontsize=12)
ax.set_ylabel("Score", fontsize=12)
ax.set_title("BiteKaro Recommender — Precision, Recall & F1 at K",
             fontsize=14, fontweight="bold")
ax.legend(fontsize=11)
ax.set_ylim(0, max(recalls) * 1.25)
ax.yaxis.grid(True, alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "01_precision_recall_at_k.png"), dpi=150, bbox_inches="tight")
plt.close()
print(f"     Best F1: {max(f1_scores):.4f} at K={k_values[np.argmax(f1_scores)]}")


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 2 — Hit/Miss Matrix by Customer Profile
# ═══════════════════════════════════════════════════════════════════════════════

print("  [2/7] Hit/Miss matrix by customer profile...")

profiles   = df_custs["profile"].unique().tolist()
k_eval     = 5
hit_matrix = {p: {"hits": 0, "misses": 0, "total": 0} for p in profiles}

for cust_id, profile, held_items in test_pairs:
    top_k, _ = predict_top_k(cust_id, k_eval)
    hits      = len(set(top_k) & set(held_items))
    hit_matrix[profile]["hits"]   += hits
    hit_matrix[profile]["misses"] += (k_eval - hits)
    hit_matrix[profile]["total"]  += k_eval

# Build matrix for heatmap
short_names = {
    "morning_office_goer":      "Office Goer",
    "college_student":          "College Student",
    "family_visitor":           "Family Visitor",
    "quick_lunch_person":       "Lunch Person",
    "dessert_and_snack_lover":  "Snack Lover",
}
matrix_data = pd.DataFrame({
    "Profile":    [short_names.get(p, p) for p in profiles],
    "Hits":       [hit_matrix[p]["hits"]   for p in profiles],
    "Misses":     [hit_matrix[p]["misses"] for p in profiles],
    "Hit Rate":   [hit_matrix[p]["hits"] / hit_matrix[p]["total"]
                   for p in profiles],
}).set_index("Profile")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Stacked bar — hits vs misses
bar_data = matrix_data[["Hits", "Misses"]]
bar_data.plot(kind="bar", stacked=True, ax=ax1,
              color=["#1565C0", "#EF9A9A"], edgecolor="white", width=0.6)
ax1.set_title("Hits vs Misses by Customer Profile\n(at K=5)",
              fontsize=13, fontweight="bold")
ax1.set_xlabel("")
ax1.set_ylabel("Count")
ax1.legend(["Hits (Correct)", "Misses (Incorrect)"], fontsize=10)
ax1.set_xticklabels(ax1.get_xticklabels(), rotation=30, ha="right")

# Hit rate heatmap
hit_rate_matrix = matrix_data[["Hit Rate"]].T
sns.heatmap(hit_rate_matrix, annot=True, fmt=".3f", cmap="Blues",
            ax=ax2, linewidths=1, linecolor="white",
            cbar_kws={"label": "Hit Rate"}, vmin=0, vmax=0.3)
ax2.set_title("Hit Rate Heatmap by Profile\n(Confusion Matrix Equivalent)",
              fontsize=13, fontweight="bold")
ax2.set_ylabel("")
ax2.set_xticklabels(ax2.get_xticklabels(), rotation=30, ha="right")

plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "02_hit_miss_matrix.png"), dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 3 — Association Rules: Confidence vs Lift
# ═══════════════════════════════════════════════════════════════════════════════

print("  [3/7] Association Rules scatter plot...")

fig, ax = plt.subplots(figsize=(11, 7))

scatter = ax.scatter(
    RULES_DF["confidence"],
    RULES_DF["lift"],
    s=RULES_DF["support"] * 3000,
    c=RULES_DF["lift"],
    cmap="Blues",
    alpha=0.75,
    edgecolors="#1565C0",
    linewidths=0.5
)
plt.colorbar(scatter, ax=ax, label="Lift")

# Label top rules
for _, row in RULES_DF.head(8).iterrows():
    ax.annotate(
        f"{row['antecedent_name']} → {row['consequent_name']}",
        xy=(row["confidence"], row["lift"]),
        xytext=(8, 4), textcoords="offset points",
        fontsize=7.5, color="#1A237E",
        arrowprops=dict(arrowstyle="-", color="gray", lw=0.5)
    )

ax.axhline(y=1.0, color="red", linestyle="--", alpha=0.5, label="Lift = 1 (random)")
ax.set_xlabel("Confidence", fontsize=12)
ax.set_ylabel("Lift", fontsize=12)
ax.set_title("Association Rules — Confidence vs Lift\n(bubble size = support)",
             fontsize=14, fontweight="bold")
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "03_association_rules.png"), dpi=150, bbox_inches="tight")
plt.close()
print(f"     {len(RULES_DF)} rules plotted, max lift: {RULES_DF['lift'].max():.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 4 — Recommendation Accuracy by Category
# ═══════════════════════════════════════════════════════════════════════════════

print("  [4/7] Accuracy by category...")

categories    = ["hot_beverages", "cold_beverages", "snacks", "meals", "desserts"]
cat_hit_rates = {c: [] for c in categories}

for cust_id, profile, held_items in test_pairs[:800]:
    top_k, _ = predict_top_k(cust_id, 5)
    for item_id in held_items:
        item = ITEM_LOOKUP.get(item_id)
        if not item: continue
        cat  = item["category"]
        hit  = 1 if item_id in top_k else 0
        cat_hit_rates[cat].append(hit)

cat_names     = [c.replace("_", "\n") for c in categories]
cat_means     = [np.mean(cat_hit_rates[c]) if cat_hit_rates[c] else 0
                 for c in categories]
cat_counts    = [len(cat_hit_rates[c]) for c in categories]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(cat_names, cat_means,
              color=sns.color_palette("Blues_d", len(categories)),
              edgecolor="white", width=0.55)
for bar, val, cnt in zip(bars, cat_means, cat_counts):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 0.003,
            f"{val:.3f}\n(n={cnt})",
            ha="center", va="bottom", fontsize=9)

ax.set_xlabel("Category", fontsize=12)
ax.set_ylabel("Hit Rate (item recommended correctly)", fontsize=12)
ax.set_title("Recommendation Hit Rate by Food Category",
             fontsize=14, fontweight="bold")
ax.set_ylim(0, max(cat_means) * 1.3)
ax.yaxis.grid(True, alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "04_accuracy_by_category.png"), dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 5 — Season vs Category Heatmap (Context Layer Proof)
# ═══════════════════════════════════════════════════════════════════════════════

print("  [5/7] Season vs Category heatmap...")

season_cat = df_items.groupby(["season", "category"]).size().unstack(fill_value=0)
season_order = ["summer", "monsoon", "autumn", "winter"]
season_cat   = season_cat.reindex(season_order)
season_pct   = season_cat.div(season_cat.sum(axis=1), axis=0)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

sns.heatmap(season_pct, annot=True, fmt=".2f", cmap="Blues",
            ax=ax1, linewidths=0.5, linecolor="white",
            cbar_kws={"label": "Proportion of Orders"})
ax1.set_title("Category Share by Season\n(Context Layer Validation)",
              fontsize=13, fontweight="bold")
ax1.set_xlabel("Category")
ax1.set_ylabel("Season")
ax1.set_xticklabels([c.replace("_", "\n") for c in season_pct.columns], fontsize=9)

# Cold vs Hot beverage split by season
bev_data = pd.DataFrame({
    "season":    season_order,
    "Cold Bev":  [season_pct.loc[s, "cold_beverages"] for s in season_order],
    "Hot Bev":   [season_pct.loc[s, "hot_beverages"]  for s in season_order],
})
x  = np.arange(len(season_order))
w  = 0.3
ax2.bar(x - w/2, bev_data["Cold Bev"], w, label="Cold Beverages",
        color="#42A5F5", alpha=0.85)
ax2.bar(x + w/2, bev_data["Hot Bev"],  w, label="Hot Beverages",
        color="#EF5350", alpha=0.85)
ax2.set_xticks(x)
ax2.set_xticklabels(season_order)
ax2.set_ylabel("Proportion of Orders")
ax2.set_title("Cold vs Hot Beverage Preference by Season\n(Proves seasonal boosting works)",
              fontsize=13, fontweight="bold")
ax2.legend(fontsize=10)
ax2.yaxis.grid(True, alpha=0.4)

for i, (cold, hot) in enumerate(zip(bev_data["Cold Bev"], bev_data["Hot Bev"])):
    ax2.text(i - w/2, cold + 0.003, f"{cold:.2f}", ha="center", fontsize=9)
    ax2.text(i + w/2, hot  + 0.003, f"{hot:.2f}",  ha="center", fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "05_season_context_proof.png"), dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 6 — SVD Item Embeddings (PCA 2D Visualization)
# ═══════════════════════════════════════════════════════════════════════════════

print("  [6/7] SVD item embeddings PCA visualization...")

pca        = PCA(n_components=2, random_state=42)
item_2d    = pca.fit_transform(ITEM_FACTORS)

cat_colors = {
    "hot_beverages":  "#E53935",
    "cold_beverages": "#1E88E5",
    "snacks":         "#43A047",
    "meals":          "#FB8C00",
    "desserts":       "#8E24AA",
}

fig, ax = plt.subplots(figsize=(12, 8))

for cat, color in cat_colors.items():
    mask    = [ITEM_LOOKUP[iid]["category"] == cat for iid in ITEM_IDS]
    indices = [i for i, m in enumerate(mask) if m]
    ax.scatter(
        item_2d[indices, 0],
        item_2d[indices, 1],
        c=color, s=120, label=cat.replace("_", " ").title(),
        alpha=0.85, edgecolors="white", linewidths=0.8, zorder=3
    )

for i, iid in enumerate(ITEM_IDS):
    ax.annotate(
        ITEM_LOOKUP[iid]["name"],
        xy=(item_2d[i, 0], item_2d[i, 1]),
        xytext=(5, 4), textcoords="offset points",
        fontsize=7.5, alpha=0.9
    )

ax.set_xlabel(f"PCA Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)",
              fontsize=11)
ax.set_ylabel(f"PCA Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)",
              fontsize=11)
ax.set_title("SVD Item Embeddings — 2D PCA Projection\n"
             "(Items closer together = more similar ordering patterns)",
             fontsize=13, fontweight="bold")
ax.legend(fontsize=10, loc="upper right")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "06_item_embeddings_pca.png"), dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 7 — Summary Scorecard
# ═══════════════════════════════════════════════════════════════════════════════

print("  [7/7] Summary scorecard...")

best_k       = k_values[np.argmax(f1_scores)]
best_f1      = max(f1_scores)
best_prec    = precisions[np.argmax(f1_scores)]
best_recall  = recalls[np.argmax(f1_scores)]
avg_hit_rate = np.mean(list(cat_means))
top_rule     = RULES_DF.iloc[0]

fig = plt.figure(figsize=(14, 8))
fig.patch.set_facecolor("#0D47A1")
ax  = fig.add_subplot(111)
ax.set_facecolor("#0D47A1")
ax.axis("off")

title = "BiteKaro — Recommendation Engine Evaluation Summary"
ax.text(0.5, 0.95, title, transform=ax.transAxes,
        fontsize=16, fontweight="bold", color="white",
        ha="center", va="top")

ax.text(0.5, 0.87, "GLS University | CSE Capstone Project | AI-Powered Smart Kiosk",
        transform=ax.transAxes, fontsize=11, color="#90CAF9",
        ha="center", va="top")

metrics = [
    ("Dataset",          f"3,000 customers  |  60,403 orders  |  147,950 interactions"),
    ("Menu",             f"25 items across 5 categories (Indian cafe context)"),
    ("Model A",          f"Association Rules  —  36 rules  |  Max Lift: {RULES_DF['lift'].max():.3f}"),
    ("",                 f"Top Rule: {top_rule['antecedent_name']} -> {top_rule['consequent_name']}  "
                         f"(conf={top_rule['confidence']:.3f}, lift={top_rule['lift']:.3f})"),
    ("Model B",          f"SVD Collaborative Filtering  —  n_components=3  |  Density=0.740"),
    ("",                 f"Explained Variance: 33.2%  |  Train/Test: Leave-Last-Order-Out"),
    (f"Precision@{best_k}", f"{best_prec:.4f}"),
    (f"Recall@{best_k}",    f"{best_recall:.4f}"),
    (f"F1@{best_k}",        f"{best_f1:.4f}  (best across K=1,2,3,5,8,10)"),
    ("Avg Category HR",  f"{avg_hit_rate:.4f}  (averaged across all 5 categories)"),
    ("Context Layer",    f"Mood (4 types)  x  Season (4)  x  Time-slot (4)  =  64 context states"),
    ("Cold Start",       f"Popularity baseline for new customers  |  SVD for returning customers"),
]

y_start = 0.78
for label, value in metrics:
    if label:
        ax.text(0.05, y_start, f"{label}:", transform=ax.transAxes,
                fontsize=10, color="#BBDEFB", fontweight="bold", va="top")
        ax.text(0.28, y_start, value, transform=ax.transAxes,
                fontsize=10, color="white", va="top")
    else:
        ax.text(0.28, y_start, value, transform=ax.transAxes,
                fontsize=10, color="#E3F2FD", va="top", style="italic")
    y_start -= 0.068

ax.text(0.5, 0.02,
        "Models: Association Rules (cross-sell)  +  SVD CF (personalization)  +  Context Boosting (mood/season/time)",
        transform=ax.transAxes, fontsize=9, color="#90CAF9",
        ha="center", va="bottom")

plt.tight_layout()
plt.savefig(os.path.join(EVAL_DIR, "07_summary_scorecard.png"), dpi=150, bbox_inches="tight")
plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

summary = f"""
BiteKaro — Model Evaluation Summary
=====================================

Dataset
-------
  Customers             : 3,000
  Orders                : 60,403
  Item Interactions     : 147,950
  Menu Items            : 25 (5 categories)

Model A — Association Rules
----------------------------
  Rules Found           : {len(RULES_DF)}
  Max Lift              : {RULES_DF['lift'].max():.4f}
  Max Confidence        : {RULES_DF['confidence'].max():.4f}
  Top Rule              : {top_rule['antecedent_name']} -> {top_rule['consequent_name']}
                          conf={top_rule['confidence']:.3f}, lift={top_rule['lift']:.3f}

Model B — SVD Collaborative Filtering
---------------------------------------
  n_components          : 3
  Explained Variance    : 33.2%
  Matrix Density        : 0.740
  Evaluation Method     : Leave-Last-Order-Out

Performance Metrics
--------------------
  K     Precision    Recall      F1
  ---   ---------    ------      --
"""
for k, p, r, f in zip(k_values, precisions, recalls, f1_scores):
    summary += f"  {k:<5} {p:.4f}       {r:.4f}      {f:.4f}\n"

summary += f"""
  Best F1               : {best_f1:.4f} at K={best_k}

Category Hit Rates
-------------------
"""
for cat, rate in zip(categories, cat_means):
    summary += f"  {cat:<22} {rate:.4f}\n"

summary += f"""
Context Layer
--------------
  Mood types            : 4 (tired, thirsty, hungry, happy)
  Seasons               : 4 (summer, monsoon, autumn, winter)
  Time slots            : 4 (morning, lunch, afternoon, evening)
  Total context states  : 64

Charts Saved
-------------
  01_precision_recall_at_k.png
  02_hit_miss_matrix.png
  03_association_rules.png
  04_accuracy_by_category.png
  05_season_context_proof.png
  06_item_embeddings_pca.png
  07_summary_scorecard.png
"""

with open(os.path.join(EVAL_DIR, "evaluation_summary.txt"), "w", encoding="utf-8") as f:
    f.write(summary)

print("\n" + "=" * 60)
print(summary)
print("  All charts saved to data/eval_plots/")
print("=" * 60)
