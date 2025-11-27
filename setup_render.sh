#!/bin/bash
# Setup script for Render deployment

echo "🚀 Setting up MangoTrades V6 for Render deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git branch -M main
fi

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo "🔗 Adding GitHub remote..."
    git remote add origin https://github.com/izokimani/mango_trader_v6.git
fi

# Add all files
echo "📝 Staging files..."
git add .

# Check if there are changes
if git diff --staged --quiet; then
    echo "✅ No changes to commit"
else
    echo "💾 Committing changes..."
    git commit -m "Configure for Render deployment - V6"
fi

# Push to GitHub
echo "⬆️  Pushing to GitHub..."
git push -u origin main || echo "⚠️  Push failed. Make sure the GitHub repo exists and you have access."

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Go to https://dashboard.render.com"
echo "2. Find or create 'MangoTrader' service"
echo "3. Connect it to: https://github.com/izokimani/mango_trader_v6"
echo "4. Set environment variables (see DEPLOY.md)"
echo "5. Deploy!"
echo ""
echo "Or run: python scheduler.py locally to test first"

