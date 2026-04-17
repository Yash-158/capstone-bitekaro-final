"""
BiteKaro — Recommendation API v2.0 (FastAPI)
=============================================
Updated with order_history support for real customer personalisation.

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


def get_season(month):
    if month in [3,4,5,6]: return "summer"
    if month in [7,8,9]:   return "monsoon"
    if month in [10]:       return "autumn"
    return "winter"

def get_time_slot(hour):
    if hour < 11:  return "morning"
    if hour < 15:  return "lunch"
    if hour < 19:  return "afternoon"
    return "evening"

MOOD_BOOSTS = {
    "tired": {
        "tags":       ["energizing", "strong", "coffee"],
        "categories": ["hot_beverages"],
        "multiplier": 2.0,
    },
    "thirsty": {
        "tags":       ["refreshing", "cold", "light", "tangy"],
        "categories": ["cold_beverages"],
        "multiplier": 2.2,
    },
    "hungry": {
        "tags":       ["filling", "meal", "heavy", "spicy", "indian"],
        "categories": ["meals", "snacks"],
        "multiplier": 2.0,
    },
    "happy": {
        "tags":       ["sweet", "popular", "indulgent", "baked"],
        "categories": ["desserts", "snacks"],
        "multiplier": 1.8,
    },
}


def apply_order_history_boost(base_scores, order_history):
    """Boost items from real order history. More orders = stronger preference signal."""
    if not order_history:
        return base_scores
    scores  = dict(base_scores)
    freq    = Counter(order_history)
    max_freq = max(freq.values())
    for item_id, count in freq.items():
        if item_id in scores:
            boost = 1.2 + (0.6 * (count / max_freq))
            scores[item_id] *= boost
    return scores


def apply_context_boost(base_scores, mood, hour, month, cart_items):
    season    = get_season(month)
    time_slot = get_time_slot(hour)
    scores    = dict(base_scores)
    cart_cats = [ITEM_LOOKUP[i]["category"] for i in cart_items if i in ITEM_LOOKUP]
    bev_count  = cart_cats.count("cold_beverages") + cart_cats.count("hot_beverages")
    food_count = cart_cats.count("meals") + cart_cats.count("snacks")

    for item_id, score in scores.items():
        item = ITEM_LOOKUP.get(item_id)
        if not item: continue
        tags = item["tags"]
        cat  = item["category"]
        if mood and mood in MOOD_BOOSTS:
            mood_cfg = MOOD_BOOSTS[mood]
            boosted_cats = mood_cfg["categories"]
            boosted_tags = mood_cfg["tags"]
            mult = mood_cfg["multiplier"]
            
            item_matches_mood = (
                cat in boosted_cats or 
                any(t in tags for t in boosted_tags)
            )
            
            if item_matches_mood:
                score *= mult
            else:
                score *= 0.4
        season_score = POP_SEASON.get(season, {}).get(item_id, 0.5)
        score *= (0.7 + 0.6 * season_score)
        ts_score = POP_TIMESLOT.get(time_slot, {}).get(item_id, 0.5)
        score *= (0.8 + 0.4 * ts_score)
        if bev_count >= 2 and cat in ["cold_beverages","hot_beverages"]: score *= 0.3
        if food_count >= 2 and cat == "meals": score *= 0.4
        if item_id in cart_items: score = -999
        scores[item_id] = float(score)
    return scores


def get_reason(item_id, item, mood, hour, month, cart_items, order_history):
    season    = get_season(month)
    time_slot = get_time_slot(hour)
    tags      = item["tags"]
    freq      = Counter(order_history) if order_history else {}

    if freq.get(item_id, 0) >= 3: return "Your absolute favourite!"
    if freq.get(item_id, 0) >= 2: return "You have ordered this before and loved it"
    if freq.get(item_id, 0) == 1: return "One of your past favourites"
    if mood == "tired"   and ("energizing" in tags or "coffee" in tags): return "Great pick when you need an energy boost"
    if mood == "thirsty" and item["category"] == "cold_beverages":       return "Perfect to quench your thirst"
    if mood == "hungry"  and ("filling" in tags or "meal" in tags):      return "This should hit the spot"
    if mood == "happy"   and ("sweet" in tags or "popular" in tags):     return "A fan favourite for happy moments"
    if season == "summer"  and "cold" in tags: return "Cool down with this summer favourite"
    if season in ["winter","monsoon"] and "hot" in tags: return f"Perfect warm treat for {season}"
    if time_slot == "morning" and "breakfast" in tags: return "A great way to start your morning"
    if time_slot == "lunch"   and "meal" in tags:      return "Popular lunch choice"
    if "popular" in tags: return "One of our bestsellers"
    if any(c in RULES_LOOKUP and any(r["item_id"] == item_id for r in RULES_LOOKUP.get(c,[])) for c in cart_items):
        return "Pairs perfectly with your order"
    return "You might enjoy this"


def get_recommendations(customer_id, cart_items, mood, hour, month, top_k=5, order_history=None):
    order_history = order_history or []
    is_synthetic  = customer_id and customer_id in CUST_TO_IDX
    has_history   = len(order_history) > 0
    customer_type = "returning" if (is_synthetic or has_history) else "new"

    if is_synthetic:
        u_idx       = CUST_TO_IDX[customer_id]
        raw_scores  = ITEM_FACTORS @ USER_FACTORS[u_idx]
        base_scores = {ITEM_IDS[i]: float(raw_scores[i]) for i in range(len(ITEM_IDS))}
        model_used  = "svd"
    else:
        base_scores = dict(POP_OVERALL)
        model_used  = "popularity"

    if has_history:
        base_scores = apply_order_history_boost(base_scores, order_history)
        model_used  = "history_personalised"

    adjusted  = apply_context_boost(base_scores, mood, hour, month, cart_items)
    ranked    = sorted(adjusted.items(), key=lambda x: x[1], reverse=True)
    ranked    = [(iid, sc) for iid, sc in ranked if iid not in cart_items]
    def get_diverse_top_k(ranked_items, k, mood):
        result = []
        cat_counts = {}
        
        if mood == "hungry":
            max_per_cat = {"meals": 3, "snacks": 2,
                           "cold_beverages": 1, "hot_beverages": 1,
                           "desserts": 1}
        elif mood == "thirsty":
            max_per_cat = {"cold_beverages": 3, "hot_beverages": 1,
                           "meals": 1, "snacks": 1, "desserts": 1}
        elif mood == "tired":
            max_per_cat = {"hot_beverages": 3, "cold_beverages": 1,
                           "snacks": 1, "meals": 1, "desserts": 1}
        elif mood == "happy":
            max_per_cat = {"desserts": 2, "snacks": 2,
                           "cold_beverages": 1, "hot_beverages": 1,
                           "meals": 1}
        else:
            max_per_cat = {c: 2 for c in
                           ["meals","snacks","desserts",
                            "cold_beverages","hot_beverages"]}
        
        for item_id, score in ranked_items:
            if len(result) >= k:
                break
            item = ITEM_LOOKUP.get(item_id)
            if not item:
                continue
            cat = item["category"]
            limit = max_per_cat.get(cat, 2)
            if cat_counts.get(cat, 0) < limit:
                result.append((item_id, score))
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        
        if len(result) < k:
            existing_ids = [r[0] for r in result]
            for item_id, score in ranked_items:
                if len(result) >= k:
                    break
                if item_id not in existing_ids:
                    result.append((item_id, score))
        
        return result

    top_items = get_diverse_top_k(ranked, top_k, mood)

    assoc_injections = []
    for cart_item in cart_items:
        if cart_item in RULES_LOOKUP:
            for rule in RULES_LOOKUP[cart_item][:2]:
                if rule["item_id"] not in cart_items:
                    assoc_injections.append((rule["item_id"], rule["lift"] * 1.5))

    if assoc_injections:
        existing_ids = [i[0] for i in top_items]
        injected = [(iid, b) for iid, b in assoc_injections[:2] if iid not in existing_ids]
        top_items = injected + top_items
        top_items = list(dict.fromkeys([i[0] for i in top_items]))[:top_k]
        top_items = [(iid, adjusted.get(iid, 0)) for iid in top_items]

    recommendations = []
    for item_id, score in top_items[:top_k]:
        item = ITEM_LOOKUP.get(item_id)
        if not item: continue
        source = "association" if any(item_id == inj[0] for inj in assoc_injections[:2]) \
                 else ("history" if item_id in order_history else model_used)
        recommendations.append({
            "item_id":   item_id,
            "item_name": item["name"],
            "category":  item["category"],
            "price":     item["price"],
            "score":     round(min(max(score, 0), 1), 4),
            "reason":    get_reason(item_id, item, mood, hour, month, cart_items, order_history),
            "source":    source,
        })

    return {"recommendations": recommendations, "model_used": model_used, "customer_type": customer_type}


if HAS_FASTAPI:
    app = FastAPI(title="BiteKaro Recommendation API", version="2.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
        return {"status": "ok", "models_loaded": True, "n_items": len(ITEM_IDS), "version": "2.0.0"}

    @app.post("/recommend")
    def recommend(req: RecommendRequest):
        now   = datetime.now()
        hour  = req.hour  if req.hour  is not None else now.hour
        month = req.month if req.month is not None else now.month
        return get_recommendations(
            customer_id=req.customer_id, cart_items=req.cart_items or [],
            mood=req.mood or "happy", hour=hour, month=month,
            top_k=req.top_k or 5, order_history=req.order_history or []
        )

    @app.get("/items")
    def list_items():
        from menu import ALL_ITEMS
        return {"items": ALL_ITEMS}


if __name__ == "__main__":
    print("\nBiteKaro Recommendation API v2.0 - CLI Test\n")
    result = get_recommendations(
        customer_id="real-uuid", cart_items=[], mood="hungry", hour=13, month=2,
        order_history=["HB03","SN01","HB03","ML01","HB03","CB01"]
    )
    print(f"Model: {result['model_used']} | Type: {result['customer_type']}")
    for rec in result["recommendations"]:
        print(f"  {rec['item_name']:<22} {rec['source']:<20} {rec['reason']}")
    print("\nTo start: uvicorn serve:app --host 0.0.0.0 --port 5000 --reload")