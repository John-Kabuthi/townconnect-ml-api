# TOWNCONNECT ML MODULE - HANDOVER DOCUMENTATION

## Files Included
- recommendation_engine_final.pkl - Trained recommendation model
- business_catalog.pkl - Business database (97 Kenyan businesses)
- user_preferences_expanded.csv - User preference data (500 synthetic users)
- bert_aspect_model/ - BERT model for sentiment analysis
- feature_tags.json - Aspect categories mapping
- label_encoder.pkl - Sentiment label encoder
- main_flask_style.py - FastAPI application
- requirements.txt - Python dependencies
- Dockerfile - Container configuration
- docker-compose.yml - Multi-container setup

## Quick Start

### 1. Install dependencies
pip install -r requirements.txt

### 2. Run the API
uvicorn main_flask_style:app --reload --host 0.0.0.0 --port 8000

### 3. Test the API
curl -X POST http://localhost:8000/api/recommendations -H "Content-Type: application/json" -d "{\"user_id\": \"user_001\", \"top_n\": 5}"

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /api/recommendations | Get business recommendations |
| GET | / | List available endpoints |

## Docker Deployment
docker-compose up --build

## Available User IDs
user_001 through user_500 (500 synthetic users)

## Contact
For issues, contact the ML Engineer who built this module.
