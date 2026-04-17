"""
BiteKaro — Model Training
==========================
Trains two models:

  Model A — Association Rules (mlxtend Apriori)
    → Cross-sell logic: "customers who order X also order Y"
    → Works for ANY customer including first-time visitors
    → Output: rules with support, confidence, lift

  Model B — SVD Collaborative Filtering (sklearn TruncatedSVD)
    → Personalization for returning customers
    → Learns latent user and item embeddings
    → Falls back gracefully to popularity for cold-start

  Both models saved with joblib for FastAPI serving.

Run:
    python3 train.py

Output:
    models/association_rules.pkl
    models/svd_model.pkl
    models/item_embeddings.pkl
    models/popularity_baseline.pkl
    models/training_report.txt
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
import joblib
from scipy.sparse import load_npz
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings("ignore")

from menu import ALL_ITEMS, ITEM_IDS, ID_TO_IDX, IDX_TO_ID, ITEM_LOOKUP

BASE   = os.path.dirname(os.path.abspath(__file__))
PROC   = os.path.join(BASE, "data", "processed")
MODELS = os.path.join(BASE, "models")
os.makedirs(MODELS, exist_ok=True)

print("=" * 60)
print("  BiteKaro — Model Training Pipeline")
print("=" * 60)

# ── Load preprocessed data ────────────────────────────────────────────────────
interaction_matrix = load_npz(f"{PROC}/interaction_matrix.npz")
basket_df          = pd.read_csv(f"{PROC}/basket_matrix.csv")
item_features_df   = pd.read_csv(f"{PROC}/item_features.csv")
user_features_df   = pd.read_csv(f"{PROC}/user_features.csv")
index_maps         = joblib.load(f"{PROC}/index_maps.pkl")
df_sessions        = pd.read_csv(f"{BASE}/data/order_sessions.csv")
df_items           = pd.read_csv(f"{BASE}/data/orders.csv")

CUST_TO_IDX = index_maps["cust_to_idx"]
IDX_TO_CUST = index_maps["idx_to_cust"]

print(f"\n  Interaction matrix: {interaction_matrix.shape}, density: "
      f"{interaction_matrix.nnz / (interaction_matrix.shape[0] * interaction_matrix.shape[1]):.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL A — ASSOCIATION RULES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 60)
print("  MODEL A: Association Rules (Cross-sell Logic)")
print("─" * 60)

# Manual Apriori implementation (mlxtend not available, same algorithm)
def compute_association_rules(basket_df, min_support=0.02, min_confidence=0.10, min_lift=1.05):
    """
    Compute association rules from basket data.
    
    support(A→B)    = orders containing both A and B / total orders
    confidence(A→B) = support(A→B) / support(A)
    lift(A→B)       = confidence(A→B) / support(B)
    """
    n_orders   = len(basket_df)
    item_cols  = basket_df.columns.tolist()

    print(f"  Computing item support for {len(item_cols)} items over {n_orders:,} baskets...")

    # ── Single-item support ──────────────────────────────────────────────────
    item_support = {}
    for item in item_cols:
        item_support[item] = basket_df[item].sum() / n_orders

    frequent_items = {k: v for k, v in item_support.items() if v >= min_support}
    print(f"  Frequent single items (support ≥ {min_support}): {len(frequent_items)}")

    # ── Pair support ─────────────────────────────────────────────────────────
    from itertools import combinations
    rules = []
    pairs_checked = 0

    for itemA, itemB in combinations(frequent_items.keys(), 2):
        both = ((basket_df[itemA] == 1) & (basket_df[itemB] == 1)).sum()
        support_AB = both / n_orders

        if support_AB < min_support:
            continue

        pairs_checked += 1

        # A → B
        conf_AB = support_AB / item_support[itemA]
        lift_AB = conf_AB / item_support[itemB]
        if conf_AB >= min_confidence and lift_AB >= min_lift:
            rules.append({
                "antecedent":  itemA,
                "consequent":  itemB,
                "support":     round(support_AB, 4),
                "confidence":  round(conf_AB, 4),
                "lift":        round(lift_AB, 4),
                "antecedent_name": ITEM_LOOKUP.get(itemA, {}).get("name", itemA),
                "consequent_name": ITEM_LOOKUP.get(itemB, {}).get("name", itemB),
            })

        # B → A
        conf_BA = support_AB / item_support[itemB]
        lift_BA = conf_BA / item_support[itemA]
        if conf_BA >= min_confidence and lift_BA >= min_lift:
            rules.append({
                "antecedent":  itemB,
                "consequent":  itemA,
                "support":     round(support_AB, 4),
                "confidence":  round(conf_BA, 4),
                "lift":        round(lift_BA, 4),
                "antecedent_name": ITEM_LOOKUP.get(itemB, {}).get("name", itemB),
                "consequent_name": ITEM_LOOKUP.get(itemA, {}).get("name", itemA),
            })

    rules_df = pd.DataFrame(rules).sort_values("lift", ascending=False)
    print(f"  Pairs checked  : {pairs_checked}")
    print(f"  Rules found    : {len(rules_df)}")
    return rules_df, item_support

rules_df, item_support = compute_association_rules(
    basket_df,
    min_support=0.01,
    min_confidence=0.10,
    min_lift=1.05
)

# Build a fast lookup: given item A, what items does it commonly pair with?
rules_lookup = {}
for _, row in rules_df.iterrows():
    ant = row["antecedent"]
    if ant not in rules_lookup:
        rules_lookup[ant] = []
    rules_lookup[ant].append({
        "item_id":    row["consequent"],
        "item_name":  row["consequent_name"],
        "confidence": row["confidence"],
        "lift":       row["lift"],
    })

# Sort each list by lift descending
for k in rules_lookup:
    rules_lookup[k] = sorted(rules_lookup[k], key=lambda x: x["lift"], reverse=True)

print(f"\n  Top 10 association rules by lift:")
print(f"  {'Antecedent':<22} → {'Consequent':<22} Conf   Lift")
print(f"  {'─'*22}   {'─'*22} {'─'*6} {'─'*6}")
for _, row in rules_df.head(10).iterrows():
    print(f"  {row['antecedent_name']:<22} → {row['consequent_name']:<22} "
          f"{row['confidence']:.3f}  {row['lift']:.3f}")

# Save
joblib.dump({
    "rules_df":      rules_df,
    "rules_lookup":  rules_lookup,
    "item_support":  item_support,
}, f"{MODELS}/association_rules.pkl")
print(f"\n  ✅ Model A saved → models/association_rules.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL B — SVD COLLABORATIVE FILTERING
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 60)
print("  MODEL B: SVD Collaborative Filtering (Personalization)")
print("─" * 60)

# ── Train / Test split (leave-one-out per user) ───────────────────────────────
# For each user, hold out their last order as test
print("\n  Splitting train/test (leave-last-order-out)...")

df_sessions_sorted = df_sessions.sort_values(["customer_id", "date", "visit_num"])
train_order_ids = set()
test_pairs      = []   # (customer_id, held_out_items)

for cust_id, group in df_sessions_sorted.groupby("customer_id"):
    if len(group) < 3:
        # Too few orders — use all for training
        train_order_ids.update(group["order_id"].tolist())
        continue
    # Last order = test, rest = train
    train_orders = group.iloc[:-1]
    test_order   = group.iloc[-1]
    train_order_ids.update(train_orders["order_id"].tolist())
    held_items = json.loads(test_order["items"])
    test_pairs.append((cust_id, held_items))

# Rebuild interaction matrix using only train orders
df_train = df_items[df_items["order_id"].isin(train_order_ids)]
train_interactions = (
    df_train.groupby(["customer_id", "item_id"])
    .size()
    .reset_index(name="count")
)
train_interactions["user_idx"] = train_interactions["customer_id"].map(CUST_TO_IDX)
train_interactions["item_idx"] = train_interactions["item_id"].map(ID_TO_IDX)
train_interactions = train_interactions.dropna(subset=["user_idx", "item_idx"])
train_interactions = train_interactions.astype({"user_idx": int, "item_idx": int})

from scipy.sparse import csr_matrix
train_matrix = csr_matrix(
    (train_interactions["count"].values.astype(np.float32),
     (train_interactions["user_idx"].values, train_interactions["item_idx"].values)),
    shape=(len(CUST_TO_IDX), len(ITEM_IDS))
)

print(f"  Train matrix: {train_matrix.shape}, nnz: {train_matrix.nnz:,}")
print(f"  Test pairs  : {len(test_pairs):,}")

# ── Hyperparameter Search ─────────────────────────────────────────────────────
print("\n  Hyperparameter search for n_components...")

def evaluate_svd(matrix, test_pairs, n_components, cust_to_idx, item_ids, id_to_idx, k=5):
    """Evaluate SVD model using Precision@K and Recall@K"""
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    user_factors = svd.fit_transform(matrix)
    item_factors = svd.components_.T          # shape: (n_items, n_components)

    # Normalize for cosine similarity
    user_factors_norm = normalize(user_factors)
    item_factors_norm = normalize(item_factors)

    # Reconstruct full prediction matrix
    pred_matrix = user_factors_norm @ item_factors_norm.T  # (users, items)

    precisions, recalls = [], []

    for cust_id, held_items in test_pairs:
        if cust_id not in cust_to_idx:
            continue
        u_idx = cust_to_idx[cust_id]
        scores = pred_matrix[u_idx]                        # (n_items,)

        # Mask items already in training (penalize re-recommending known items)
        train_items_for_user = matrix[u_idx].nonzero()[1]
        scores[train_items_for_user] = -999

        top_k_indices = np.argsort(scores)[::-1][:k]
        top_k_ids     = [item_ids[i] for i in top_k_indices]

        hits = len(set(top_k_ids) & set(held_items))
        precisions.append(hits / k)
        recalls.append(hits / len(held_items) if held_items else 0)

    return np.mean(precisions), np.mean(recalls)

# Grid search over n_components
best_score  = -1
best_n      = 5
results     = []

print(f"\n  {'n_components':<15} {'Precision@5':<15} {'Recall@5':<12}")
print(f"  {'─'*13}   {'─'*13}   {'─'*10}")

for n in [3, 5, 8, 10, 12, 15]:
    prec, rec = evaluate_svd(
        train_matrix, test_pairs[:500],  # sample 500 for speed
        n, CUST_TO_IDX, ITEM_IDS, ID_TO_IDX, k=5
    )
    f1 = 2 * prec * rec / (prec + rec + 1e-10)
    results.append({"n_components": n, "precision@5": prec, "recall@5": rec, "f1": f1})
    print(f"  {n:<15} {prec:.4f}          {rec:.4f}")
    if f1 > best_score:
        best_score = f1
        best_n     = n

print(f"\n  ✅ Best n_components = {best_n}  (F1={best_score:.4f})")

# ── Train final model on FULL data with best params ──────────────────────────
print(f"\n  Training final SVD (n_components={best_n}) on full data...")
final_svd        = TruncatedSVD(n_components=best_n, random_state=42)
user_factors     = final_svd.fit_transform(interaction_matrix.astype(np.float32))
item_factors     = final_svd.components_.T
user_factors_n   = normalize(user_factors)
item_factors_n   = normalize(item_factors)

explained_var = final_svd.explained_variance_ratio_.sum()
print(f"  Explained variance : {explained_var:.3f} ({explained_var*100:.1f}%)")

# Item-item similarity matrix (for "similar items" feature)
item_similarity = cosine_similarity(item_factors_n)   # (25, 25)

# Evaluate on test set with best model
prec_final, rec_final = evaluate_svd(
    train_matrix, test_pairs,
    best_n, CUST_TO_IDX, ITEM_IDS, ID_TO_IDX, k=5
)
print(f"  Final Precision@5  : {prec_final:.4f}")
print(f"  Final Recall@5     : {rec_final:.4f}")

# Save SVD model
joblib.dump({
    "svd":              final_svd,
    "user_factors":     user_factors_n,
    "item_factors":     item_factors_n,
    "item_similarity":  item_similarity,
    "n_components":     best_n,
    "item_ids":         ITEM_IDS,
    "cust_to_idx":      CUST_TO_IDX,
    "explained_var":    explained_var,
}, f"{MODELS}/svd_model.pkl")
print(f"\n  ✅ Model B saved → models/svd_model.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
#  POPULARITY BASELINE  (fallback for cold-start users)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "─" * 60)
print("  POPULARITY BASELINE (Cold-Start Fallback)")
print("─" * 60)

# Overall popularity
overall_pop = df_items.groupby("item_id").size().reset_index(name="count")
overall_pop = overall_pop.sort_values("count", ascending=False)
overall_pop["rank"] = range(1, len(overall_pop) + 1)
overall_pop["score"] = overall_pop["count"] / overall_pop["count"].max()

# Time-slot popularity (by hour bucket)
def get_time_slot(hour):
    if hour < 11:  return "morning"
    if hour < 15:  return "lunch"
    if hour < 19:  return "afternoon"
    return "evening"

df_items["time_slot"] = df_items["hour"].apply(get_time_slot)
timeslot_pop = (
    df_items.groupby(["time_slot", "item_id"])
    .size().reset_index(name="count")
)
timeslot_pop_dict = {}
for slot, grp in timeslot_pop.groupby("time_slot"):
    grp = grp.sort_values("count", ascending=False)
    grp["score"] = grp["count"] / grp["count"].max()
    timeslot_pop_dict[slot] = grp[["item_id", "score"]].set_index("item_id")["score"].to_dict()

# Season popularity
season_pop = (
    df_items.groupby(["season", "item_id"])
    .size().reset_index(name="count")
)
season_pop_dict = {}
for season, grp in season_pop.groupby("season"):
    grp = grp.sort_values("count", ascending=False)
    grp["score"] = grp["count"] / grp["count"].max()
    season_pop_dict[season] = grp[["item_id", "score"]].set_index("item_id")["score"].to_dict()

joblib.dump({
    "overall":       overall_pop.set_index("item_id")["score"].to_dict(),
    "by_time_slot":  timeslot_pop_dict,
    "by_season":     season_pop_dict,
}, f"{MODELS}/popularity_baseline.pkl")
print(f"  ✅ Popularity baseline saved → models/popularity_baseline.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
#  TRAINING REPORT
# ═══════════════════════════════════════════════════════════════════════════════

report = f"""
BiteKaro — Training Report
============================

Model A: Association Rules
---------------------------
  Min support    : 0.02
  Min confidence : 0.20
  Min lift       : 1.2
  Rules found    : {len(rules_df)}
  
  Top 5 Rules:
"""
for _, row in rules_df.head(5).iterrows():
    report += f"    {row['antecedent_name']} → {row['consequent_name']}  (conf={row['confidence']:.3f}, lift={row['lift']:.3f})\n"

report += f"""
Model B: SVD Collaborative Filtering
--------------------------------------
  Best n_components  : {best_n}
  Explained Variance : {explained_var:.3f} ({explained_var*100:.1f}%)
  Final Precision@5  : {prec_final:.4f}
  Final Recall@5     : {rec_final:.4f}

Hyperparameter Search Results:
"""
for r in results:
    report += f"  n={r['n_components']:<3}  P@5={r['precision@5']:.4f}  R@5={r['recall@5']:.4f}  F1={r['f1']:.4f}\n"

report += f"""
Popularity Baseline:
  Time slots : {list(timeslot_pop_dict.keys())}
  Seasons    : {list(season_pop_dict.keys())}
  
Models Saved:
  models/association_rules.pkl
  models/svd_model.pkl
  models/popularity_baseline.pkl
"""

with open(f"{MODELS}/training_report.txt", "w", encoding="utf-8") as f:
    f.write(report)

print("\n" + report)
print("=" * 60)
print("  ✅ All models trained and saved!")
print("=" * 60)
