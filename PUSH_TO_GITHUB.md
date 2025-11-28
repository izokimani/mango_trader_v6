# Push to GitHub - Quick Guide

Your code is committed locally and ready to push! Here's how:

## Option 1: Using GitHub Desktop (Easiest)
1. Open GitHub Desktop
2. File → Add Local Repository
3. Select: `/Users/isaaccohen/Documents/ManyMangoes/MangoMagic/Apps/Trader Bots/MangoTrades V6`
4. Click "Publish repository" or "Push origin"

## Option 2: Using Terminal
```bash
cd "/Users/isaaccohen/Documents/ManyMangoes/MangoMagic/Apps/Trader Bots/MangoTrades V6"
git push -u origin main
```
(You'll be prompted for GitHub username/password or token)

## Option 3: Using GitHub CLI (if installed)
```bash
gh auth login
cd "/Users/isaaccohen/Documents/ManyMangoes/MangoMagic/Apps/Trader Bots/MangoTrades V6"
git push -u origin main
```

## After Pushing
Once pushed, Render will automatically:
1. Detect the new commit
2. Build the service (`pip install -r requirements.txt`)
3. Start the scheduler (`python scheduler.py`)

**Don't forget**: Add environment variables in Render dashboard first!
Go to: https://dashboard.render.com/web/srv-d4kde6odl3ps73dhvt70 → Environment

