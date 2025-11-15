#!/bin/bash
# Quick start script for Finclator local setup

set -e

echo "🚀 Finclator Local Setup"
echo "========================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}✗ Python 3.11+ not found. Please install Python 3.11 or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $(python3.11 --version | cut -d' ' -f2) found${NC}"
echo ""

# Check PostgreSQL
echo -e "${BLUE}Checking PostgreSQL...${NC}"

# Try to add PostgreSQL to PATH if installed via Homebrew
if ! command -v psql &> /dev/null; then
    # Check if Homebrew PostgreSQL is installed
    if [ -d "/opt/homebrew/opt/postgresql@15/bin" ]; then
        # Apple Silicon Mac
        export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
        echo -e "${GREEN}✓ PostgreSQL found (added to PATH)${NC}"
    elif [ -d "/usr/local/opt/postgresql@15/bin" ]; then
        # Intel Mac
        export PATH="/usr/local/opt/postgresql@15/bin:$PATH"
        echo -e "${GREEN}✓ PostgreSQL found (added to PATH)${NC}"
    else
        echo -e "${RED}✗ PostgreSQL not found!${NC}"
        echo -e "${YELLOW}Please run: ./scripts/setup_postgres_mac.sh${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ PostgreSQL found${NC}"
fi
echo ""

# Create virtual environment
echo -e "${BLUE}Setting up virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi
echo ""

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
echo "  → Step 1/3: Upgrading pip..."
python -m pip install --upgrade pip > /dev/null 2>&1

echo "  → Step 2/3: Installing build tools..."
python -m pip install setuptools wheel > /dev/null 2>&1

echo "  → Step 3/3: Installing Finclator packages..."
# Use requirements-style installation as fallback for editable mode issues
python -m pip install \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "sqlalchemy>=2.0.0" \
    "asyncpg>=0.29.0" \
    "alembic>=1.12.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "httpx>=0.25.0" \
    "requests>=2.31.0" \
    "huggingface-hub>=0.19.0" \
    "python-dotenv>=1.0.0" \
    "pytest>=7.4.0" \
    "pytest-asyncio>=0.21.0" \
    "ruff>=0.1.0" \
    "mypy>=1.7.0" > /dev/null 2>&1

echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql+asyncpg://localhost/finclator

# External API Keys
X_API_BEARER_TOKEN=your_x_bearer_token_here
ALPHAVANTAGE_API_KEY=your_alphavantage_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠ Using default configuration. Edit .env to add real API keys.${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi
echo ""

# Check if database exists
echo -e "${BLUE}Checking database connection...${NC}"
if python -c "import sys; sys.path.insert(0, 'src'); from services.config import settings; print(settings.database_url)" &> /dev/null; then
    echo -e "${GREEN}✓ Configuration loaded${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify configuration${NC}"
fi
echo ""

# Ensure finclator database exists
echo -e "${BLUE}Checking finclator database...${NC}"
if psql postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw finclator; then
    echo -e "${GREEN}✓ Database 'finclator' exists${NC}"
else
    echo -e "${YELLOW}Creating database 'finclator'...${NC}"
    createdb finclator 2>/dev/null || {
        echo -e "${RED}✗ Could not create database${NC}"
        echo "Please run: createdb finclator"
        exit 1
    }
    echo -e "${GREEN}✓ Database 'finclator' created${NC}"
fi
echo ""

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
if alembic upgrade head 2>&1 | grep -q "ERROR"; then
    echo -e "${RED}✗ Migration failed. Please check your DATABASE_URL in .env${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Ensure PostgreSQL is running"
    echo "2. Create database: createdb finclator"
    echo "3. Update DATABASE_URL in .env"
    exit 1
else
    echo -e "${GREEN}✓ Migrations applied${NC}"
fi
echo ""

# Seed data
echo -e "${BLUE}Seeding initial data...${NC}"
python scripts/seed_data.py
echo ""

# Summary
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit influencer handles in scripts/seed_data.py (optional)"
echo "2. Add real API keys to .env (optional for testing)"
echo "3. Run the pipeline:"
echo -e "   ${BLUE}./scripts/run_pipeline.sh${NC}"
echo "4. Start the API:"
echo -e "   ${BLUE}uvicorn src.api.main:app --reload${NC}"
echo "5. Visit: http://localhost:8000/docs"
echo ""
echo "Quick test:"
echo -e "   ${BLUE}curl 'http://localhost:8000/health'${NC}"
echo ""

