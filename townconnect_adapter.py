# townconnect_adapter.py
# This adds TownConnect-specific endpoints to work with Firebase
# It REUSES the business_catalog and recommendation logic

import pickle
import math
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os

# ============================================
# HELPER FUNCTIONS (Reused from your main file)
# ============================================

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# ============================================
# LOAD DATA (Same as your main file)
# ============================================

DATA_PATH = r"C:\Users\user\Downloads\TownConnect_Handover"

# Load business catalog
business_catalog = pd.read_pickle(os.path.join(DATA_PATH, "business_catalog.pkl"))

# Load user preferences
user_df = pd.read_csv(os.path.join(DATA_PATH, "user_preferences_expanded.csv"))

# Convert string representation of list to actual list (same as your code)
import ast
user_df['liked_categories'] = user_df['liked_categories'].apply(ast.literal_eval)

print(f"[Adapter] Loaded {len(user_df)} users")
print(f"[Adapter] Loaded {len(business_catalog)} businesses")
print(f"[Adapter] Business columns: {list(business_catalog.columns)}")


# ============================================
# TOWNCONNECT SPECIFIC REQUEST MODELS
# ============================================

class TownConnectRecommendationRequest(BaseModel):
    """Request format from Firebase Cloud Function"""
    user_id: str
    user_preferences: Optional[Dict[str, Any]] = None
    user_history: Optional[List[Dict[str, Any]]] = None
    location: Optional[Dict[str, float]] = None  # {"latitude": -1.28, "longitude": 36.82}
    limit: int = 20


class TownConnectRecommendationResponse(BaseModel):
    """Response format for Firebase"""
    success: bool
    user_id: str
    recommended_business_ids: List[str]
    scores: List[float]
    source: str
    error: Optional[str] = None


# ============================================
# MAIN RECOMMENDATION ENDPOINT FOR TOWNCONNECT
# ============================================

def get_recommendations_for_user(
    user_id: str, 
    user_latitude: Optional[float] = None, 
    user_longitude: Optional[float] = None,
    limit: int = 20
) -> tuple[List[str], List[float]]:
    """
    Core recommendation logic - REUSES your existing algorithm
    Returns (business_ids, scores)
    """
    
    # Find user in your dataset
    user_row = user_df[user_df['user_id'] == user_id]
    
    if len(user_row) == 0:
        # User not found in synthetic data - use default preferences
        print(f"[Adapter] User {user_id} not found, using default preferences")
        preferred_cats = ["Food", "Retail", "Services"]  # Default categories
    else:
        preferred_cats = user_row.iloc[0]['liked_categories']
    
    # Use provided location or default to Nairobi
    if user_latitude and user_longitude:
        center_lat = user_latitude
        center_lon = user_longitude
    else:
        # Default to Nairobi city center (same as your original code)
        center_lat = -1.15518
        center_lon = 36.95910
    
    # Calculate scores for each business (YOUR EXISTING ALGORITHM)
    results = []
    for idx, biz in business_catalog.iterrows():
        # Get business ID (handle different column names)
        if 'business_id' in biz:
            biz_id = biz['business_id']
        else:
            # Generate an ID from name if not present
            biz_id = biz.get('Business Name', f"biz_{idx}").replace(' ', '_').lower()
        
        # Category matching score (80% weight - YOUR LOGIC)
        biz_category = biz.get('Category', '')
        cat_match = 1 if biz_category in preferred_cats else 0
        
        # Distance score (20% weight - YOUR LOGIC)
        biz_lat = biz.get('Latitude', 0)
        biz_lon = biz.get('Longitude', 0)
        
        if biz_lat and biz_lon and center_lat and center_lon:
            distance = haversine(center_lat, center_lon, biz_lat, biz_lon)
            prox_score = 1 / (1 + distance)  # Closer = higher score
        else:
            prox_score = 0.5  # Default if no coordinates
        
        # Final score: 80% category match, 20% proximity (YOUR EXACT FORMULA)
        final_score = (cat_match * 0.8) + (prox_score * 0.2)
        
        results.append({
            'business_id': biz_id,
            'business_name': biz.get('Business Name', 'Unknown'),
            'score': final_score,
            'distance_km': round(distance, 2) if biz_lat else None
        })
    
    # Sort by score (highest first) - YOUR LOGIC
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top N
    top_results = results[:limit]
    business_ids = [r['business_id'] for r in top_results]
    scores = [r['score'] for r in top_results]
    
    return business_ids, scores


# ============================================
# FASTAPI ENDPOINT - This is what Firebase will call
# ============================================

async def townconnect_recommendations_endpoint(request: TownConnectRecommendationRequest):
    """
    Endpoint for Firebase Cloud Function to call.
    This is the bridge between your ML model and TownConnect.
    """
    
    print(f"[Adapter] Received request for user: {request.user_id}")
    print(f"[Adapter] Location: {request.location}")
    
    try:
        # Extract location if provided
        user_lat = None
        user_lon = None
        if request.location:
            user_lat = request.location.get('latitude')
            user_lon = request.location.get('longitude')
        
        # Get recommendations using YOUR existing algorithm
        business_ids, scores = get_recommendations_for_user(
            user_id=request.user_id,
            user_latitude=user_lat,
            user_longitude=user_lon,
            limit=request.limit
        )
        
        print(f"[Adapter] Generated {len(business_ids)} recommendations")
        
        return TownConnectRecommendationResponse(
            success=True,
            user_id=request.user_id,
            recommended_business_ids=business_ids,
            scores=scores,
            source="ml_engine_category_80_location_20"
        )
        
    except Exception as e:
        print(f"[Adapter] Error: {str(e)}")
        return TownConnectRecommendationResponse(
            success=False,
            user_id=request.user_id,
            recommended_business_ids=[],
            scores=[],
            source="error",
            error=str(e)
        )


# ============================================
# HELPER ENDPOINT - List all businesses (for debugging)
# ============================================

async def get_all_businesses_endpoint():
    """Return all businesses in catalog (for Firebase team to map IDs)"""
    businesses = []
    for idx, biz in business_catalog.iterrows():
        # Generate business ID if not present
        biz_id = biz.get('business_id', biz.get('Business Name', f"biz_{idx}").replace(' ', '_').lower())
        businesses.append({
            'business_id': biz_id,
            'name': biz.get('Business Name', 'Unknown'),
            'category': biz.get('Category', 'Unknown'),
            'latitude': biz.get('Latitude'),
            'longitude': biz.get('Longitude')
        })
    
    return {
        "count": len(businesses),
        "businesses": businesses
    }


# ============================================
# TEST ENDPOINT - Verify adapter is working
# ============================================

async def test_endpoint():
    """Simple test endpoint to verify adapter is loaded"""
    return {
        "status": "adapter_loaded",
        "businesses_loaded": len(business_catalog),
        "users_loaded": len(user_df),
        "sample_businesses": business_catalog.head(3).to_dict('records')
    }