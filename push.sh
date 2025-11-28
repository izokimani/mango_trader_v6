#!/bin/bash
# Script to push to GitHub with authentication

echo "🚀 Pushing MangoTrades V6 to GitHub..."
echo ""
echo "You'll need to authenticate with GitHub."
echo "If you don't have a Personal Access Token, create one at:"
echo "https://github.com/settings/tokens"
echo ""
echo "When prompted:"
echo "  Username: izokimani"
echo "  Password: [Use your Personal Access Token, NOT your GitHub password]"
echo ""

cd "/Users/isaaccohen/Documents/ManyMangoes/MangoMagic/Apps/Trader Bots/MangoTrades V6"

# Try pushing
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo "Render will automatically deploy in a few minutes."
    echo ""
    echo "Next step: Add environment variables in Render:"
    echo "https://dashboard.render.com/web/srv-d4kde6odl3ps73dhvt70"
else
    echo ""
    echo "❌ Push failed. You may need to:"
    echo "1. Create a GitHub Personal Access Token"
    echo "2. Use it as the password when prompted"
    echo ""
    echo "Or use GitHub Desktop to push instead."
fi

