# Bluesky API Setup Guide

## Step-by-step guide to get your Bluesky credentials for automated posting

### Step 1: Create a Bluesky Account

1. Go to **bsky.app** and sign up (or sign in if you already have an account)
2. Complete your profile setup (display name, avatar, bio)
3. Your handle will be something like `yourname.bsky.social`

### Step 2: Generate an App Password

App Passwords let your bot post without exposing your main password.

1. Go to **bsky.app/settings/app-passwords**
2. Click **"Add App Password"**
3. Give it a name (e.g., `BuenaVista Bot`)
4. Click **"Create App Password"**
5. Copy the generated password immediately — it is only shown once

> **Important:** App Passwords look like `xxxx-xxxx-xxxx-xxxx`. They are different from your login password. Never share your main password with any bot or script.

### Step 3: Verify Your Credentials

You should now have **2 values**:

| # | Key Name | Environment Variable | Example |
|---|----------|---------------------|---------|
| 1 | Bluesky Handle | `BLUESKY_HANDLE` | `buenavista101.bsky.social` |
| 2 | App Password | `BLUESKY_APP_PASSWORD` | `xxxx-xxxx-xxxx-xxxx` |

### Step 4: Add Keys to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings > Secrets and variables > Actions**
3. Click **"New repository secret"** for each key:
   - Name: `BLUESKY_HANDLE` / Value: your handle (e.g., `buenavista101.bsky.social`)
   - Name: `BLUESKY_APP_PASSWORD` / Value: your app password

### Step 5: Test Locally (Optional)

```bash
export BLUESKY_HANDLE="yourname.bsky.social"
export BLUESKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export OTM_API_KEY="your_otm_key"
export CLAUDE_API_KEY="your_claude_key"

python post_to_bluesky.py
```

---

## Troubleshooting

### "401 Unauthorized" when posting
- Your handle or app password is incorrect
- Fix: Double-check the handle includes `.bsky.social` and regenerate the app password

### "Invalid identifier or password"
- The app password may have been revoked or typed incorrectly
- Fix: Go to **bsky.app/settings/app-passwords**, delete the old one, and create a new one

### Image not showing in post
- The image file may be too large (Bluesky limit: 1 MB) or in an unsupported format
- Supported formats: JPEG, PNG, GIF, WebP
- The bot will post without an image if upload fails

### Post text too long
- Bluesky has a 300 grapheme limit (similar to characters)
- The bot automatically trims posts to fit

## How It Works

Unlike X/Twitter which requires OAuth and 4 API keys, Bluesky uses the **AT Protocol** with simple HTTP requests:

1. **Login** — `POST` to `bsky.social/xrpc/com.atproto.server.createSession` with handle + app password
2. **Upload image** — `POST` to `bsky.social/xrpc/com.atproto.repo.uploadBlob` with image binary
3. **Create post** — `POST` to `bsky.social/xrpc/com.atproto.repo.createRecord` with post text + image blob

No extra Python packages needed beyond `requests`.

## API Limits

- Completely free, no paid tiers
- No credit card required
- Rate limits are generous (enough for daily posting)
- Image uploads supported natively
- Works from GitHub Actions (no Cloudflare blocking)
