#!/bin/bash
# PostgreSQL setup script for macOS

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🐘 PostgreSQL Setup for macOS"
echo "=============================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. Installing Homebrew first...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo -e "${GREEN}✓ Homebrew installed${NC}"
    echo ""
fi

# Install PostgreSQL
echo -e "${BLUE}Installing PostgreSQL...${NC}"
if brew list postgresql@15 &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL already installed${NC}"
else
    brew install postgresql@15
    echo -e "${GREEN}✓ PostgreSQL installed${NC}"
fi
echo ""

# Add PostgreSQL to PATH for this session
echo -e "${BLUE}Setting up PATH...${NC}"
# Detect if Apple Silicon or Intel Mac
if [ -d "/opt/homebrew/opt/postgresql@15/bin" ]; then
    # Apple Silicon Mac
    export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
    PG_PATH="/opt/homebrew/opt/postgresql@15/bin"
elif [ -d "/usr/local/opt/postgresql@15/bin" ]; then
    # Intel Mac
    export PATH="/usr/local/opt/postgresql@15/bin:$PATH"
    PG_PATH="/usr/local/opt/postgresql@15/bin"
fi
echo -e "${GREEN}✓ PATH configured${NC}"

# Add to shell profile for future sessions
SHELL_RC="$HOME/.zshrc"
if ! grep -q "postgresql@15/bin" "$SHELL_RC" 2>/dev/null; then
    echo -e "${BLUE}Adding PostgreSQL to ~/.zshrc...${NC}"
    echo "" >> "$SHELL_RC"
    echo "# PostgreSQL (added by Finclator setup)" >> "$SHELL_RC"
    echo "export PATH=\"$PG_PATH:\$PATH\"" >> "$SHELL_RC"
    echo -e "${GREEN}✓ Added to ~/.zshrc${NC}"
    echo -e "${YELLOW}ℹ Note: Restart terminal or run 'source ~/.zshrc' for future sessions${NC}"
fi
echo ""

# Start PostgreSQL service
echo -e "${BLUE}Starting PostgreSQL service...${NC}"
brew services start postgresql@15
sleep 3
echo -e "${GREEN}✓ PostgreSQL service started${NC}"
echo ""

# Create finclator database
echo -e "${BLUE}Creating finclator database...${NC}"
if psql postgres -lqt | cut -d \| -f 1 | grep -qw finclator; then
    echo -e "${GREEN}✓ Database 'finclator' already exists${NC}"
else
    createdb finclator
    echo -e "${GREEN}✓ Database 'finclator' created${NC}"
fi
echo ""

# Test connection
echo -e "${BLUE}Testing database connection...${NC}"
if psql -d finclator -c "SELECT version();" &> /dev/null; then
    echo -e "${GREEN}✓ Connection successful${NC}"
    echo ""
    psql -d finclator -c "SELECT version();" | head -3
else
    echo -e "${RED}✗ Connection failed${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}✅ PostgreSQL setup complete!${NC}"
echo ""
echo "Your DATABASE_URL should be:"
echo -e "${BLUE}postgresql+asyncpg://localhost/finclator${NC}"
echo ""
echo "Next steps:"
echo "1. Continue with ./scripts/quickstart.sh"
echo "2. Or run migrations: alembic upgrade head"

