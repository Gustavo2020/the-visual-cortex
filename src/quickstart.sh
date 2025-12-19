#!/bin/bash
# Quick Start Script for CLIP Image Search
# This script sets up and runs the search service

set -e

echo "=========================================="
echo "CLIP Image Search - Quick Start"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file from template...${NC}"
    cp .env.example .env
    echo "Edit .env to customize configuration"
fi

# Check if embeddings exist
if [ ! -f "../data/embeddings/image_embeddings.npy" ]; then
    echo -e "${YELLOW}Warning: Embeddings not found at ../data/embeddings/${NC}"
    echo "You need to run embed_images.py first to generate embeddings."
    echo "See README.md for instructions."
    echo ""
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Choose how to run the service:"
echo ""
echo "1. Interactive CLI (Development):"
echo "   python search.py"
echo ""
echo "2. REST API (Production):"
echo "   uvicorn api:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. REST API with auto-reload (Development):"
echo "   uvicorn api:app --reload"
echo ""
echo "4. Run tests:"
echo "   pytest test_search.py -v"
echo ""
echo "5. View API documentation:"
echo "   Start API and visit http://localhost:8000/docs"
echo ""
echo "6. Docker (Production):"
echo "   docker build -t clip-search ."
echo "   docker run -p 8000:8000 -v \$(pwd)/data:/app/data clip-search"
echo ""
echo "7. Docker Compose (Full Stack):"
echo "   docker-compose up -d"
echo ""
