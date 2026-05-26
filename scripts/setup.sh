#!/bin/bash
# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
# AladdinAI - One-command setup script
# Автоматически настраивает всё окружение

set -e  # Exit on error

echo "🚀 AladdinAI Setup"
echo "=================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is running"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠${NC}  .env file not found. Creating from .env.example..."
    cp .env.example .env

    # Generate Fernet key
    echo -e "${YELLOW}⚠${NC}  Generating encryption key..."
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")

    if [ -n "$FERNET_KEY" ]; then
        # Update .env with generated key
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|FERNET_KEY=.*|FERNET_KEY=$FERNET_KEY|" .env
        else
            sed -i "s|FERNET_KEY=.*|FERNET_KEY=$FERNET_KEY|" .env
        fi
        echo -e "${GREEN}✓${NC} Encryption key generated"
    else
        echo -e "${YELLOW}⚠${NC}  Could not generate Fernet key automatically. Please install cryptography:"
        echo "    pip install cryptography"
        echo "    Then run: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        echo "    And update FERNET_KEY in .env"
    fi
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p backend/traefik-dynamic
mkdir -p backend/guacamole-config
echo -e "${GREEN}✓${NC} Directories created"

# Setup Guacamole config if not exists
if [ ! -f backend/guacamole-config/guacamole.properties ]; then
    echo ""
    echo "🔧 Setting up Guacamole config..."
    cp backend/guacamole-config/guacamole.properties.example backend/guacamole-config/guacamole.properties
    cp backend/guacamole-config/user-mapping.xml.example backend/guacamole-config/user-mapping.xml
    echo -e "${GREEN}✓${NC} Guacamole config created"
fi

# Start core services
echo ""
echo "🐳 Starting core services..."
docker-compose up -d postgres guacd guacamole-db

echo ""
echo "⏳ Waiting for databases to be ready..."
sleep 10

# Check if Guacamole DB is initialized
GUAC_TABLES=$(docker exec guacamole-db mysql -uguacamole -pguacamole guacamole_db -e "SHOW TABLES;" 2>/dev/null | wc -l)

if [ "$GUAC_TABLES" -lt 2 ]; then
    echo ""
    echo "🔧 Initializing Guacamole database..."

    # Download schema
    docker run --rm guacamole/guacamole:1.5.4 /opt/guacamole/bin/initdb.sh --mysql > /tmp/guacamole-initdb.sql

    # Apply schema
    docker exec -i guacamole-db mysql -uguacamole -pguacamole guacamole_db < /tmp/guacamole-initdb.sql

    echo -e "${GREEN}✓${NC} Guacamole database initialized"
    echo -e "   Default login: ${YELLOW}guacadmin / guacadmin${NC}"
else
    echo -e "${GREEN}✓${NC} Guacamole database already initialized"
fi

# Start all services
echo ""
echo "🚀 Starting all services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service health
echo ""
echo "🏥 Checking service health..."

# Check backend
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running (http://localhost:8000)"
else
    echo -e "${YELLOW}⚠${NC}  Backend is starting... (check logs: docker-compose logs backend)"
fi

# Check frontend
if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is running (http://localhost:3000)"
else
    echo -e "${YELLOW}⚠${NC}  Frontend is starting... (check logs: docker-compose logs frontend)"
fi

# Check Traefik
if curl -s http://localhost:8086/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Traefik is running (http://localhost:8086)"
else
    echo -e "${YELLOW}⚠${NC}  Traefik is starting..."
fi

echo ""
echo "============================================"
echo -e "${GREEN}✅ AladdinAI setup complete!${NC}"
echo "============================================"
echo ""
echo "📍 Access points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   Traefik:   http://localhost:8086"
echo "   Dashboard: http://localhost:8081"
echo ""
echo "📚 Next steps:"
echo "   1. Open http://localhost:3000"
echo "   2. Create an account"
echo "   3. Install terminal providers (ttyd, wetty, etc.)"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:    docker-compose logs -f"
echo "   Stop:         docker-compose down"
echo "   Restart:      docker-compose restart"
echo ""
echo "============================================"
echo "💬 One favor — tell me how it went."
echo "============================================"
echo ""
echo "   Quick form:  https://aliyev.site/AladdinAI/feedback"
echo "   Email:       aladdin@aliyev.site"
echo ""
echo "   Even 'this is broken' helps. I read every message."
echo "   — Aladdin"
echo ""
