#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/scripts/download_coding_models.sh
# Description: Download all pre-configured coding models
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     llamaCPPManager - Coding Models Download Script     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if llamacpp-manager is installed
if ! command -v llamacpp-manager &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} llamacpp-manager not found"
    echo "Install with: pipx install ."
    exit 1
fi

# Check if huggingface_hub is installed
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} Installing huggingface_hub..."
    pip install huggingface_hub
fi

# Show available space
echo -e "${BLUE}[INFO]${NC} Checking available disk space..."
AVAILABLE=$(df -h ~ | awk 'NR==2 {print $4}')
echo -e "  Available space: ${GREEN}${AVAILABLE}${NC}"
echo ""

# Total size needed
echo -e "${YELLOW}[INFO]${NC} Total download size: ~69 GB"
echo -e "${YELLOW}[INFO]${NC} Total RAM needed (one at a time): 22-40 GB"
echo ""

# Ask for confirmation
echo -e "${YELLOW}[QUESTION]${NC} Do you want to download all coding models? (y/N)"
read -r CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Download cancelled"
    exit 0
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Downloading Models (this will take a while...)${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""

# Download each model
MODELS=("qwen-coder-32b" "qwen-coder-14b" "deepseek-coder-lite")
FAILED=()

for MODEL in "${MODELS[@]}"; do
    echo -e "${BLUE}[1/3]${NC} Downloading ${MODEL}..."
    echo ""

    if llamacpp-manager models download "$MODEL"; then
        echo ""
        echo -e "${GREEN}✓${NC} Successfully downloaded ${MODEL}"
        echo ""
    else
        echo ""
        echo -e "${RED}✗${NC} Failed to download ${MODEL}"
        FAILED+=("$MODEL")
        echo ""
    fi

    echo -e "${BLUE}────────────────────────────────────────────────────────${NC}"
    echo ""
done

# Summary
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Download Summary${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""

if [ ${#FAILED[@]} -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All models downloaded successfully!"
else
    echo -e "${YELLOW}⚠${NC}  Some models failed to download:"
    for MODEL in "${FAILED[@]}"; do
        echo -e "  ${RED}✗${NC} $MODEL"
    done
fi

echo ""
echo -e "${BLUE}[INFO]${NC} Downloaded models location: ~/llms/"
echo ""
echo -e "${BLUE}[INFO]${NC} List downloaded models:"
echo "  llamacpp-manager models list"
echo ""
echo -e "${BLUE}[INFO]${NC} Add models to config:"
echo "  llamacpp-manager config add qwen-coder-32b ~/llms/qwen-coder-32b/*.gguf --port 8090"
echo "  llamacpp-manager config add qwen-coder-14b ~/llms/qwen-coder-14b/*.gguf --port 8091"
echo "  llamacpp-manager config add deepseek-coder-lite ~/llms/deepseek-coder-lite/*.gguf --port 8092"
echo ""
echo -e "${GREEN}Done!${NC}"
