#!/bin/bash
# =====================================================
#  Image Unity - One-Click GitHub Deploy
# =====================================================
# Usage: bash deploy-to-github.sh YOUR_GITHUB_TOKEN
# =====================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TOKEN="$1"
REPO_NAME="image-unity"
USERNAME=""

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Usage: bash deploy-to-github.sh YOUR_GITHUB_TOKEN${NC}"
    echo ""
    echo "Need a token? Here's how (takes 30 seconds):"
    echo "  1. Go to https://github.com/settings/tokens"
    echo "  2. Click 'Generate new token (classic)'"
    echo "  3. Check ONLY 'repo' scope"
    echo "  4. Click 'Generate token'"
    echo "  5. Copy the token and run this script again"
    echo ""
    echo -e "${BLUE}Shortcut:${NC} Visit https://github.com/settings/tokens/new?scopes=repo"
    echo "           Check 'repo', scroll down, click 'Generate token'"
    exit 1
fi

# Get username from token
echo -e "${BLUE}→ Authenticating with GitHub...${NC}"
USERNAME=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin).get('login',''))" 2>/dev/null)

if [ -z "$USERNAME" ]; then
    echo -e "${RED}Invalid token! Make sure you copied it correctly.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Authenticated as: $USERNAME${NC}"

# Navigate to project
cd "$(dirname "$0")"

# Create .gitignore
cat > .gitignore << 'GIEOF'
node_modules/
uploads/
.env
_cache_index.json
*.log
GIEOF

# Init git
echo -e "${BLUE}→ Initializing git repo...${NC}"
rm -rf .git
git init -b main
git config user.email "image-unity@deploy"
git config user.name "Image Unity"

# Add all files
git add -A
git commit -m "Initial commit: Image Unity - Free AI Image Generator API Server" --allow-empty

# Create repo on GitHub
echo -e "${BLUE}→ Creating GitHub repository...${NC}"
CREATE_RESP=$(curl -s -H "Authorization: token $TOKEN" \
     -H "Content-Type: application/json" \
     -X POST https://api.github.com/user/repos \
     -d "{\"name\":\"$REPO_NAME\",\"description\":\"Free unlimited AI image generator with multi-provider API server. No login required. Automatic fallback between HuggingFace, ModelScope, Replicate, Fal AI, and Together AI.\",\"private\":false,\"auto_init\":false}")

REPO_URL=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('clone_url',''))" 2>/dev/null)

if [ -z "$REPO_URL" ]; then
    ERROR_MSG=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','unknown error'))" 2>/dev/null)
    echo -e "${RED}Failed to create repo: $ERROR_MSG${NC}"
    echo "The repo '${REPO_NAME}' may already exist on your account."
    echo -e "${BLUE}Trying to push to existing repo instead...${NC}"
    REPO_URL="https://$TOKEN@github.com/$USERNAME/$REPO_NAME.git"
else
    REPO_URL="https://$TOKEN@github.com/$USERNAME/$REPO_NAME.git"
fi

# Push to GitHub
echo -e "${BLUE}→ Pushing to GitHub...${NC}"
git remote add origin "$REPO_URL"
git push -u origin main 2>&1 || git push -u origin master 2>&1 || {
    echo -e "${RED}Push failed. The repo might already have content.${NC}"
    echo "Trying force push..."
    git push -u origin main --force 2>&1 || {
        echo -e "${RED}Could not push. Try manually:${NC}"
        echo "  cd image-unity"
        echo "  git remote add origin https://github.com/$USERNAME/$REPO_NAME.git"
        echo "  git push -u origin main"
        exit 1
    }
}

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ SUCCESS! Repo created & pushed!       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Repo:  https://github.com/$USERNAME/$REPO_NAME"
echo "  Clone: git clone https://github.com/$USERNAME/$REPO_NAME.git"
echo ""
echo -e "${BLUE}→ Deploy to Render.com (free, 1-click):${NC}"
echo "  1. Go to https://render.com/new/web"
echo "  2. Connect your GitHub repo"
echo "  3. Build: npm install"
echo "  4. Start: node server/index.js"
echo "  5. Click 'Create Web Service'"
echo ""

# Clean up token from remote URL
git remote set-url origin "https://github.com/$USERNAME/$REPO_NAME.git"

echo -e "${GREEN}Token removed from git remote. You're all set!${NC}"
