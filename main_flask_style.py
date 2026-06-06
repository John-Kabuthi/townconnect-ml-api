import pickle
import json
import math
import csv
import ast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import pandas as pd

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

DATA_PATH = r"C:\Users\user\Downloads\TownCo"

# Load using pandas (handles the list conversion properly)
business_catalog = pd.read_pickle(os.path.join(DATA_PATH, "business_catalog.pkl"))
user_df = pd.read_csv(os.path.join(DATA_PATH, "user_preferences_expanded.csv"))

# Convert string representation of list to actual list
user_df['liked_categories'] = user_df['liked_categories'].apply(ast.literal_eval)

print(f"Loaded {len(user_df)} users")
print(f"Loaded {len(business_catalog)} businesses")

app = FastAPI(title="TownConnect API")

class RecommendRequest(BaseModel):
    user_id: str
    top_n: int = 10

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/recommendations")
async def get_recommendations(request: RecommendRequest):
    user_row = user_df[user_df['user_id'] == request.user_id]
    if len(user_row) == 0:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
    
    preferred_cats = user_row.iloc[0]['liked_categories']
    center_lat = -1.15518
    center_lon = 36.95910
    
    results = []
    for _, biz in business_catalog.iterrows():
        cat_match = 1 if biz['Category'] in preferred_cats else 0
        distance = haversine(center_lat, center_lon, biz['Latitude'], biz['Longitude'])
        prox_score = 1 / (1 + distance)
        final_score = cat_match * 0.8 + prox_score * 0.2
        
        results.append({
            'business_name': biz['Business Name'],
            'category': biz['Category'],
            'distance_km': round(distance, 2),
            'score': round(final_score, 4)
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return {"user_id": request.user_id, "recommendations": results[:request.top_n]}

@app.get("/")
async def root():
    return {"message": "TownConnect API", "endpoints": ["/health", "/api/recommendations"]}

# ============================================
# INTEGRATE TOWNCONNECT ADAPTER
# ============================================

# Import and register the TownConnect adapter endpoints
from townconnect_adapter import (
    townconnect_recommendations_endpoint,
    get_all_businesses_endpoint,
    test_endpoint,
    TownConnectRecommendationRequest
)

# Register the new endpoints on the existing FastAPI app
app.add_api_route(
    "/api/townconnect/recommendations",
    townconnect_recommendations_endpoint,
    methods=["POST"],
    response_model=None
)

app.add_api_route(
    "/api/townconnect/businesses",
    get_all_businesses_endpoint,
    methods=["GET"]
)

app.add_api_route(
    "/api/townconnect/test",
    test_endpoint,
    methods=["GET"]
)

print("[Main] TownConnect adapter endpoints registered")
print("[Main] Available endpoints:")
print("  - POST /api/townconnect/recommendations")
print("  - GET  /api/townconnect/businesses")
print("  - GET  /api/townconnect/test")