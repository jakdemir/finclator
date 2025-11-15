#!/bin/bash
# Run the complete Finclator pipeline locally

set -e

echo "🚀 Running Finclator pipeline..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Tweet Ingestion
echo -e "${BLUE}📥 Step 1/5: Ingesting tweets...${NC}"
python -m src.workers.tweet_ingestion
echo -e "${GREEN}✓ Tweet ingestion complete${NC}"
echo ""

# 2. Sentiment Classification
echo -e "${BLUE}🧠 Step 2/5: Classifying sentiment...${NC}"
python -m src.workers.sentiment
echo -e "${GREEN}✓ Sentiment classification complete${NC}"
echo ""

# 3. Price Ingestion
echo -e "${BLUE}💰 Step 3/5: Fetching price data...${NC}"
python -m src.workers.price_ingestion
echo -e "${GREEN}✓ Price ingestion complete${NC}"
echo ""

# 4. Prediction Evaluation
echo -e "${BLUE}📊 Step 4/5: Evaluating predictions...${NC}"
python -m src.workers.evaluation
echo -e "${GREEN}✓ Evaluation complete${NC}"
echo ""

# 5. Signal Aggregation
echo -e "${BLUE}🎯 Step 5/5: Aggregating signals...${NC}"
python -m src.workers.aggregation
echo -e "${GREEN}✓ Signal aggregation complete${NC}"
echo ""

echo -e "${GREEN}✅ Pipeline complete! Signals are ready.${NC}"
echo ""
echo "You can now query signals via the API:"
echo "  curl 'http://localhost:8000/signals?asset=BTC&horizon=SHORT'"

