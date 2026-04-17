"""
BiteKaro — Recommendation API v2.0 (FastAPI)
=============================================
Fixed version:
  - Stronger mood multipliers (4x vs old 2x)
  - Score normalisation so popularity doesn't dominate
  - Stronger history boost (up to 3x)
  - Harder penalty for non-mood items (0.05x vs old 0.4x)

POST /recommend accepts:
{
    "customer_id":   "any-string-or-uuid",
    "cart_items":    ["HB02", "SN01"],
    "mood":          "tired",
    "hour":          14,
    "month":         6,
    "top_k":         5,
    "order_history": ["HB02", "SN01", "HB03", "CB01"]
}

Run:
    uvicorn serve:app --host 0.0.0.0 --port 5000 --reload
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from collections import Counter
import numpy as np
import joblib
from typing import Optional, List

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("FastAPI not installed. Run: pip install fastapi uvicorn")

from menu import ITEM_IDS, ITEM_LOOKUP, IDX_TO_ID, ID_TO_IDX

BASE   = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(BASE, "models")

print("Loading models...")
assoc_data = joblib.load(os.path.join(MODELS, "association_rules.pkl"))
svd_data   = joblib.load(os.path.join(MODELS, "svd_model.pkl"))
pop_data   = joblib.load(os.path.join(MODELS, "popularity_baseline.pkl"))
print("All models loaded")

RULES_LOOKUP = assoc_data["rules_lookup"]
POP_OVERALL  = pop_data["overall"]
POP_TIMESLOT = pop_data["by_time_slot"]
POP_SEASON   = pop_data["by_season"]
USER_FACTORS = svd_data["user_factors"]
ITEM_FACTORS = svd_data["item_factors"]
CUST_TO_IDX  = svd_data["cust_to_idx"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_season(month):
    if month in [3, 4, 5, 6]: return "summer"
    if month in [7, 8, 9]:    return "monsoon"
    if month in [10]:          return "autumn"
    return "winter"

def get_time_slot(hour):
    if hour < 11:  return "morning"
    if hour < 15:  return "lunch"
    if hour < 19:  return "afternoon"
    return "evening"

def normalize_scores(scores: dict) -> dict:
    """
    Normalize scores to 0-1 range so popularity baseline
    doesn't completely dominate mood/history boosts.
    Without this, Cappuccino (score=0.95) always beats
    everything even after 4x mood boost on cold beverages.
    """
    if not scores:
        return scores
    vals = list(scores.values())
    min_v = min(vals)
    max_v = max(vals)
    if max_v == min_v:
        return {k: 0.5 for k in scores}
    return {
        k: (v - min_v) / (max_v - min_v)
        for k, v in scores.items()
    }


# ── Mood boost config — STRONGER than before ──────────────────────────────────
# multiplier: how much to boost matching items
# penalty:    how much to suppress non-matching items
# This ensures mood CLEARLY changes the top 5

MOOD_BOOSTS = {
    "tired": {
        "tags":        ["energizing", "strong", "coffee", "hot"],
        "categories":  ["hot_beverages"],
        "multiplier":  4.0,    # was 2.0
        "penalty":     0.05,   # was 0.4 — much harder suppression
    },
    "thirsty": {
        "tags":        ["refreshing", "cold", "light", "tangy", "fruity"],
        "categories":  ["cold_beverages"],
        "multiplier":  4.5,    # was 2.2
        "penalty":     0.05,
    },
    "hungry": {
        "tags":        ["filling", "meal", "heavy", "spicy", "indian"],
        "categories":  ["meals", "snacks"],
        "multiplier":  4.0,    # was 2.0
        "penalty":     0.05,
    },
    "happy": {
        "tags":        ["sweet", "popular", "indulgent", "baked", "cold"],
        "categories":  ["desserts", "snacks"],
        "multiplier":  3.5,    # was 1.8
        "penalty":     0.08,
    },
}


# ── History boost — STRONGER than before ──────────────────────────────────────

def apply_order_history_boost(base_scores: dict, order_history: list) -> dict:
    """
    Boost items from real order history.
    More orders of an item = stronger boost.
    Max boost raised from 1.8x to 3.0x.
    """
    if not order_history:
        return base_scores

    scores  = dict(base_scores)
    freq    = Counter(order_history)
    max_freq = max(freq.values()) if freq else 1

    for item_id, count in freq.items():
        if item_id in scores:
            # Boost formula: 1.5 + 1.5*(count/max_freq)
            # Min boost: 1.5x (ordered once)
            # Max boost: 3.0x (most frequently ordered)
            boost = 1.5 + 1.5 * (count / max_freq)
            scores[item_id] *= boost

    return scores


# ── Context boost ─────────────────────────────────────────────────────────────

def apply_context_boost(
    base_scores: dict,
    mood: str,
    hour: int,
    month: int,
    cart_items: list
) -> dict:
    season    = get_season(month)
    time_slot = get_time_slot(hour)
    scores    = dict(base_scores)

    cart_cats  = [ITEM_LOOKUP[i]["category"] for i in cart_items if i in ITEM_LOOKUP]
    bev_count  = cart_cats.count("cold_beverages") + cart_cats.count("hot_beverages")
    food_count = cart_cats.count("meals") + cart_cats.count("snacks")

    for item_id in list(scores.keys()):
        score = scores[item_id]
        item  = ITEM_LOOKUP.get(item_id)
        if not item:
            continue

        tags = item["tags"]
        cat  = item["category"]

        # ── Mood boost (strongest signal) ─────────────────────────────────
        if mood and mood in MOOD_BOOSTS:
            mood_cfg = MOOD_BOOSTS[mood]
            boosted_cats = mood_cfg["categories"]
            boosted_tags = mood_cfg["tags"]
            multiplier   = mood_cfg["multiplier"]
            penalty      = mood_cfg["penalty"]

            item_matches_mood = (
                cat in boosted_cats or
                any(t in tags for t in boosted_tags)
            )

            if item_matches_mood:
                score *= multiplier
            else:
                score *= penalty   # hard suppression of non-mood items

        # ── Season boost (secondary signal) ───────────────────────────────
        season_score = POP_SEASON.get(season, {}).get(item_id, 0.5)
        score *= (0.6 + 0.8 * season_score)

        # ── Time slot boost (tertiary signal) ─────────────────────────────
        ts_score = POP_TIMESLOT.get(time_slot, {}).get(item_id, 0.5)
        score   *= (0.7 + 0.6 * ts_score)

        # ── Cart suppression ───────────────────────────────────────────────
        if bev_count >= 2 and cat in ["cold_beverages", "hot_beverages"]:
            score *= 0.2
        if food_count >= 2 and cat == "meals":
            score *= 0.3

        # ── Suppress already-in-cart items ─────────────────────────────────
        if item_id in cart_items:
            score = -999

        scores[item_id] = float(score)

    return scores


# ── Reason string ─────────────────────────────────────────────────────────────

def get_reason(item_id, item, mood, hour, month, cart_items, order_history):
    season    = get_season(month)
    time_slot = get_time_slot(hour)
    tags      = item["tags"]
    freq      = Counter(order_history) if order_history else {}

    # History-based reasons (most specific)
    if freq.get(item_id, 0) >= 5:  return "Your absolute favourite!"
    if freq.get(item_id, 0) >= 3:  return "You have ordered this before and loved it"
    if freq.get(item_id, 0) >= 1:  return "One of your past favourites"

    # Mood-based reasons
    if mood == "tired"   and ("energizing" in tags or "coffee" in tags or "hot" in tags):
        return "Perfect energy boost for when you're tired"
    if mood == "thirsty" and item["category"] == "cold_beverages":
        return "Perfect to quench your thirst"
    if mood == "hungry"  and ("filling" in tags or "meal" in tags):
        return "This should hit the spot when you're hungry"
    if mood == "happy"   and ("sweet" in tags or "popular" in tags):
        return "A fan favourite for happy moments"

    # Season-based reasons
    if season == "summer"  and "cold" in tags:
        return "Cool down with this summer favourite"
    if season in ["winter", "monsoon"] and "hot" in tags:
        return f"Perfect warm treat for {season}"

    # Time-based reasons
    if time_slot == "morning" and ("breakfast" in tags or "hot" in tags):
        return "A great way to start your morning"
    if time_slot == "lunch" and "meal" in tags:
        return "Popular lunch choice"

    # Association rule reason
    if any(
        c_item in RULES_LOOKUP and
        any(r["item_id"] == item_id for r in RULES_LOOKUP.get(c_item, []))
        for c_item in cart_items
    ):
        return "Pairs perfectly with your order"

    if "popular" in tags:
        return "One of our bestsellers"

    return "You might enjoy this"


# ── Diversity enforcement ─────────────────────────────────────────────────────

def get_diverse_top_k(ranked_items: list, k: int, mood: str) -> list:
    """
    Enforce category diversity so we don't show 5 hot beverages
    even when tired mood is selected.
    Per-mood limits ensure variety while respecting mood preference.
    """
    if mood == "tired":
        max_per_cat = {
            "hot_beverages":  3,
            "snacks":         1,
            "cold_beverages": 1,
            "meals":          1,
            "desserts":       1,
        }
    elif mood == "thirsty":
        max_per_cat = {
            "cold_beverages": 3,
            "snacks":         1,
            "hot_beverages":  1,
            "desserts":       1,
            "meals":          1,
        }
    elif mood == "hungry":
        max_per_cat = {
            "meals":          3,
            "snacks":         2,
            "cold_beverages": 1,
            "hot_beverages":  1,
            "desserts":       1,
        }
    elif mood == "happy":
        max_per_cat = {
            "desserts":       2,
            "snacks":         2,
            "cold_beverages": 1,
            "hot_beverages":  1,
            "meals":          1,
        }
    else:
        max_per_cat = {c: 2 for c in [
            "meals", "snacks", "desserts",
            "cold_beverages", "hot_beverages"
        ]}

    result    = []
    cat_count = {}

    for item_id, score in ranked_items:
        if len(result) >= k:
            break
        item  = ITEM_LOOKUP.get(item_id)
        if not item:
            continue
        cat   = item["category"]
        limit = max_per_cat.get(cat, 2)
        if cat_count.get(cat, 0) < limit:
            result.append((item_id, score))
            cat_count[cat] = cat_count.get(cat, 0) + 1

    # Fill remaining slots if diversity left gaps
    if len(result) < k:
        existing_ids = [r[0] for r in result]
        for item_id, score in ranked_items:
            if len(result) >= k:
                break
            if item_id not in existing_ids:
                result.append((item_id, score))

    return result


# ── Main recommendation function ──────────────────────────────────────────────

def get_recommendations(
    customer_id,
    cart_items,
    mood,
    hour,
    month,
    top_k=5,
    order_history=None
):
    order_history = order_history or []
    is_synthetic  = customer_id and customer_id in CUST_TO_IDX
    has_history   = len(order_history) > 0
    customer_type = "returning" if (is_synthetic or has_history) else "new"

    # ── Step 1: Base scores ───────────────────────────────────────────────────
    if is_synthetic:
        u_idx      = CUST_TO_IDX[customer_id]
        raw_scores = ITEM_FACTORS @ USER_FACTORS[u_idx]
        base_scores = {ITEM_IDS[i]: float(raw_scores[i]) for i in range(len(ITEM_IDS))}
        model_used  = "svd"
    else:
        base_scores = dict(POP_OVERALL)
        model_used  = "popularity"

    # ── Step 2: Normalize so popularity doesn't dominate ─────────────────────
    base_scores = normalize_scores(base_scores)

    # ── Step 3: History boost ─────────────────────────────────────────────────
    if has_history:
        base_scores = apply_order_history_boost(base_scores, order_history)
        model_used  = "history_personalised"

    # ── Step 4: Context boost (mood + time + season) ──────────────────────────
    adjusted = apply_context_boost(base_scores, mood, hour, month, cart_items)

    # ── Step 5: Rank and enforce diversity ────────────────────────────────────
    ranked   = sorted(adjusted.items(), key=lambda x: x[1], reverse=True)
    ranked   = [(iid, sc) for iid, sc in ranked if iid not in cart_items]
    top_items = get_diverse_top_k(ranked, top_k, mood)

    # ── Step 6: Association rule injections for cart items ────────────────────
    assoc_injections = []
    for cart_item in cart_items:
        if cart_item in RULES_LOOKUP:
            for rule in RULES_LOOKUP[cart_item][:2]:
                if rule["item_id"] not in cart_items:
                    assoc_injections.append((rule["item_id"], rule["lift"] * 2.0))

    if assoc_injections:
        existing_ids = [i[0] for i in top_items]
        injected = [
            (iid, b) for iid, b in assoc_injections[:2]
            if iid not in existing_ids
        ]
        top_items = injected + top_items
        top_items = list(dict.fromkeys([i[0] for i in top_items]))[:top_k]
        top_items = [(iid, adjusted.get(iid, 0)) for iid in top_items]

    # ── Step 7: Build response ────────────────────────────────────────────────
    recommendations = []
    for item_id, score in top_items[:top_k]:
        item = ITEM_LOOKUP.get(item_id)
        if not item:
            continue

        source = "association" if any(
            item_id == inj[0] for inj in assoc_injections[:2]
        ) else (
            "history" if item_id in order_history else model_used
        )

        recommendations.append({
            "item_id":   item_id,
            "item_name": item["name"],
            "category":  item["category"],
            "price":     item["price"],
            "score":     round(min(max(score, 0), 1), 4),
            "reason":    get_reason(
                item_id, item, mood, hour, month, cart_items, order_history
            ),
            "source":    source,
        })

    return {
        "recommendations": recommendations,
        "model_used":      model_used,
        "customer_type":   customer_type,
    }


# ── FastAPI app ───────────────────────────────────────────────────────────────

if HAS_FASTAPI:
    app = FastAPI(
        title="BiteKaro Recommendation API",
        version="2.0.0"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class RecommendRequest(BaseModel):
        customer_id:   Optional[str]       = None
        cart_items:    List[str]           = []
        mood:          Optional[str]       = "happy"
        hour:          Optional[int]       = None
        month:         Optional[int]       = None
        top_k:         Optional[int]       = 5
        order_history: Optional[List[str]] = []

    @app.get("/health")
    def health():
        return {
            "status":        "ok",
            "models_loaded": True,
            "n_items":       len(ITEM_IDS),
            "version":       "2.0.0"
        }

    @app.post("/recommend")
    def recommend(req: RecommendRequest):
        now   = datetime.now()
        hour  = req.hour  if req.hour  is not None else now.hour
        month = req.month if req.month is not None else now.month
        return get_recommendations(
            customer_id   = req.customer_id,
            cart_items    = req.cart_items or [],
            mood          = req.mood or "happy",
            hour          = hour,
            month         = month,
            top_k         = req.top_k or 5,
            order_history = req.order_history or [],
        )

    @app.get("/items")
    def list_items():
        from menu import ALL_ITEMS
        return {"items": ALL_ITEMS}


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nBiteKaro Recommendation API v2.0 — CLI Test\n")

    test_cases = [
        {
            "label":         "New customer — TIRED mood (expect hot beverages)",
            "customer_id":   None,
            "mood":          "tired",
            "hour":          9,
            "month":         4,
            "order_history": [],
        },
        {
            "label":         "New customer — THIRSTY mood (expect cold beverages)",
            "customer_id":   None,
            "mood":          "thirsty",
            "hour":          15,
            "month":         5,
            "order_history": [],
        },
        {
            "label":         "New customer — HUNGRY mood (expect meals)",
            "customer_id":   None,
            "mood":          "hungry",
            "hour":          13,
            "month":         2,
            "order_history": [],
        },
        {
            "label":         "New customer — HAPPY mood (expect desserts/snacks)",
            "customer_id":   None,
            "mood":          "happy",
            "hour":          17,
            "month":         12,
            "order_history": [],
        },
        {
            "label":         "Returning customer — TIRED + strong chai history",
            "customer_id":   None,
            "mood":          "tired",
            "hour":          9,
            "month":         4,
            "order_history": ["HB03","HB03","HB03","SN01","HB03","SN04","HB04","HB03"],
        },
    ]

    for tc in test_cases:
        print(f"\n  Test: {tc['label']}")
        result = get_recommendations(
            customer_id   = tc["customer_id"],
            cart_items    = [],
            mood          = tc["mood"],
            hour          = tc["hour"],
            month         = tc["month"],
            order_history = tc["order_history"],
        )
        print(f"  Model: {result['model_used']} | Type: {result['customer_type']}")
        for i, rec in enumerate(result["recommendations"]):
            print(f"  {i+1}. {rec['item_name']:<22} [{rec['category']:<16}] {rec['reason']}")
    print()
