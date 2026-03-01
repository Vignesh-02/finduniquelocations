# X (Twitter) API Setup Guide

## Step-by-step guide to get your X API credentials on console.x.com

### Step 1: Create a Developer Account

1. Go to **console.x.com** and sign in with your X account
2. Accept the Developer Agreement and Policy
3. An app will be auto-created for you (e.g., `BuenaVista1`)

### Step 2: Set Up User Authentication

This is required before you can post tweets.

1. Click on your app name to open its settings
2. Find **"User authentication settings"** and click **"Set up"**
3. Fill in the following:

| Field | Value |
|-------|-------|
| **App permissions** | Read and write |
| **Type of App** | Web App, Automated App or Bot |
| **Callback URL** | `https://buenavista.in/callback` |
| **Website URL** | `https://buenavista.in` |

4. Leave all other fields blank/default
5. Click **Save**

### Step 3: Get Your Consumer Keys (API Key & Secret)

1. Go to your app's **"Keys and Tokens"** tab
2. Under **Consumer Keys**, you'll see:
   - **API Key** (also called Consumer Key)
   - **API Key Secret** (also called Consumer Secret)
3. If you need to regenerate them, click **"Regenerate"**
4. Copy both values immediately — they are only shown once

### Step 4: Generate Access Token & Secret

These allow your app to post on behalf of YOUR account.

1. On the same **"Keys and Tokens"** tab, scroll down to **"Authentication Tokens"**
2. Find **"Access Token and Secret"** and click **"Generate"**
3. Copy both values immediately:
   - **Access Token**
   - **Access Token Secret**

> **Important:** If you changed app permissions (e.g., from Read to Read+Write),
> you MUST regenerate the Access Token and Secret for the new permissions to work.
> Old tokens will still have Read-only access.

### Step 5: Verify Your Keys

You should now have **4 keys**:

| # | Key Name | Environment Variable |
|---|----------|---------------------|
| 1 | API Key (Consumer Key) | `X_API_KEY` |
| 2 | API Key Secret (Consumer Secret) | `X_API_SECRET` |
| 3 | Access Token | `X_ACCESS_TOKEN` |
| 4 | Access Token Secret | `X_ACCESS_TOKEN_SECRET` |

> **Note:** The Bearer Token is NOT needed. It's only for read-only app-level authentication.

### Step 6: Add Keys to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings > Secrets and variables > Actions**
3. Click **"New repository secret"** for each key:
   - Name: `X_API_KEY` / Value: your API Key
   - Name: `X_API_SECRET` / Value: your API Key Secret
   - Name: `X_ACCESS_TOKEN` / Value: your Access Token
   - Name: `X_ACCESS_TOKEN_SECRET` / Value: your Access Token Secret

### Step 7: Test Locally (Optional)

```bash
export X_API_KEY="your_api_key"
export X_API_SECRET="your_api_secret"
export X_ACCESS_TOKEN="your_access_token"
export X_ACCESS_TOKEN_SECRET="your_access_token_secret"
export OTM_API_KEY="your_otm_key"
export CLAUDE_API_KEY="your_claude_key"

python post_to_x.py
```

---

## Troubleshooting

### "403 Forbidden" when posting
- Your app permissions are set to Read-only
- Fix: Change to **Read and write** in User authentication settings, then **regenerate** Access Token and Secret

### "401 Unauthorized"
- Your keys are incorrect or expired
- Fix: Regenerate all keys from the Keys and Tokens tab

### Can't find "Keys and Tokens" tab
- Click directly on your app name first to open the app detail page
- The tab appears at the top of the app detail view

### "User authentication not set up"
- You skipped Step 2
- Fix: Go to your app settings and complete the User authentication setup

## Free Tier Limits

- 1,500 tweets per month (plenty for 1/day)
- 50 requests per 15 minutes
- Media upload supported
- No credit card required
