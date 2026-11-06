# Hostinger SSH Cron Job Setup

This guide sets up daily automated product discovery and site rebuilding on Hostinger.

## What Gets Automated

Every day at 5:17 AM UTC, Hostinger will:

1. **Discover 5 new products** from Amazon matching your categories
2. **Fetch fresh product photos** from Amazon
3. **Rebuild the site** with all changes
4. **Add TikTok tracking pixel** to all pages

New products are added to a **staging section** for your review before going live.

---

## Prerequisites

✅ You need:
- SSH access to your Hostinger account
- The `.env` file with Amazon credentials on the server (see "Step 3" below)
- Scripts uploaded: `discover_products.py`, `daily-automation.sh` (already in repo)

---

## Step 1: Upload Files to Hostinger

The following files are already in your repository and need to be on Hostinger:

```
site/
  ├── discover_products.py          ← Product discovery script
  ├── daily-automation.sh           ← Main cron wrapper (must be executable)
  ├── fetch_amazon_images.py        ← Photo fetching
  ├── build.py                       ← Site rebuilder
  ├── add_tiktok_pixel.py           ← TikTok pixel
  ├── products.json                 ← Product database (will have staging added)
  └── public/
      └── admin/
          └── review-products.php   ← Admin panel to approve staged products
```

These are deployed via your normal GitHub Actions workflow to Hostinger. Just ensure they're in `site/` directory.

---

## Step 2: Make Scripts Executable

SSH into your Hostinger account and run:

```bash
# Connect via SSH (get your Hostinger SSH credentials from hPanel > Advanced > SSH)
ssh your-username@your-host.com

# Navigate to your site directory (Hostinger default)
cd ~/public_html

# Make automation script executable
chmod +x site/daily-automation.sh
chmod +x site/discover_products.py
```

---

## Step 3: Set Environment Variables

The automation needs your Amazon API credentials and other configuration.

**Create `.env` file on Hostinger:**

The script supports both naming conventions. Use whichever matches your setup:

**Option A: Using live sync variable names:**
```bash
cat > ~/public_html/site/.env << 'EOF'
AMAZON_CLIENT_ID=your-client-id
AMAZON_CLIENT_SECRET=your-client-secret
AMAZON_CREDENTIAL_VERSION=v1
AMAZON_PARTNER_TAG=your-associate-tag
AMAZON_MARKETPLACE=www.amazon.com
AMAZON_SEARCHES=kitchen drawer organizer|small kitchen gadgets|kitchen storage
GEMINI_API_KEY=your-gemini-key
REPLICATE_API_KEY=your-replicate-key
VIDEO_SERVICE=replicate
EOF
```

**Option B: Using Creators API names (compatible with existing scripts):**
```bash
cat > ~/public_html/site/.env << 'EOF'
AMAZON_CREATORS_CLIENT_ID=your-client-id
AMAZON_CREATORS_CLIENT_SECRET=your-client-secret
GEMINI_API_KEY=your-gemini-key
REPLICATE_API_KEY=your-replicate-key
VIDEO_SERVICE=replicate
EOF
```

**Secure it:**
```bash
chmod 600 ~/public_html/site/.env
```

**⚠️ SECURITY:** Never commit `.env` to GitHub. It's in `.gitignore` for a reason.

---

## Step 4: Set Up SSH Cron Job

SSH into Hostinger and edit your crontab:

```bash
crontab -e
```

Add this line (runs daily at 5:17 AM UTC):

```cron
17 5 * * * /home/your-username/public_html/site/daily-automation.sh >> /home/your-username/public_html/site/logs/cron.log 2>&1
```

**Adjust if needed:**
- Change `your-username` to your actual Hostinger username
- Change time: `17 5 * * *` means "5:17 AM UTC every day"
  - First number: minute (0-59)
  - Second number: hour (0-23, UTC)
  - Other numbers: day, month, day-of-week (leave as `*` for every day)

**Examples:**
- `0 9 * * *` = 9:00 AM UTC daily
- `0 5 * * 1` = 5:00 AM UTC every Monday

---

## Step 5: Verify Setup

Check if cron job is installed:

```bash
crontab -l
```

You should see your automation line listed.

---

## Step 6: Monitor Logs

After the first cron run, check the logs:

```bash
# View today's log
cat ~/public_html/site/logs/automation-*.log

# Follow live log
tail -f ~/public_html/site/logs/automation-*.log

# Check for errors
cat ~/public_html/site/logs/automation-error.log
```

---

## Step 7: Review Staged Products

New products discovered by automation are added to **staging** and won't appear on your site until you approve them.

**To review and approve:**

1. Go to: `https://kitchenfindsfavorites.com/admin/review-products.php`
2. Enter the admin password (set in `review-products.php` - change it from default!)
3. Edit product details if needed
4. Click **"✓ Approve"** to add to site, or **"✗ Reject"** to remove

Approved products go into your main site immediately after you save.

---

## What Happens Daily

**5:17 AM UTC (your cron time):**

1. ✓ Script runs `discover_products.py`
   - Searches Amazon for new kitchen products
   - Finds top 5 candidates
   - Adds to `products.json` staging section

2. ✓ Script runs `fetch_amazon_images.py`
   - Gets fresh product photos from Amazon
   - Updates product image URLs

3. ✓ Script runs `build.py`
   - Validates all product data
   - Generates all HTML pages
   - Creates sitemap, robots.txt, meta tags

4. ✓ Script runs `add_tiktok_pixel.py`
   - Ensures TikTok tracking pixel on every page

5. ✓ Logs everything to `site/logs/automation-*.log`

**Your staging section fills up with new product candidates.**

**You review and approve them at your convenience** via the admin panel.

---

## Troubleshooting

### Cron job not running?

```bash
# Check if cron service is running
pgrep cron

# Check system log (if available)
tail /var/log/syslog | grep CRON
```

### Script errors?

Check the log file:

```bash
tail -50 ~/public_html/site/logs/automation-error.log
```

### Amazon API failing?

Verify credentials in `.env`:
```bash
cat ~/public_html/site/.env
```

Make sure:
- `AMAZON_CREATORS_CLIENT_ID` and `AMAZON_CREATORS_CLIENT_SECRET` are set
- Keys haven't expired
- Your Associates account has 10+ qualifying sales (required by Amazon)

### Python not found?

Use full path in crontab. Update the cron line to:

```cron
17 5 * * * /usr/bin/python3 /home/your-username/public_html/site/daily-automation.sh >> /home/your-username/public_html/site/logs/cron.log 2>&1
```

Or find Python path:
```bash
which python3
```

---

## Disabling Automation

To temporarily stop the cron job:

```bash
crontab -e
# Comment out the line with #
# 17 5 * * * /home/...
```

To fully remove:

```bash
crontab -r
```

---

## Checking What's in Staging

View all staged products:

```bash
# Pretty-print staging section
cat ~/public_html/site/products.json | python3 -m json.tool | grep -A 100 '"staging"'
```

---

## Next Steps

1. ✅ Deploy the scripts via GitHub (they're already committed)
2. ✅ SSH into Hostinger
3. ✅ Make scripts executable
4. ✅ Create `.env` file with credentials
5. ✅ Set up cron job with `crontab -e`
6. ✅ Wait for first automated run (or manually trigger: `bash ~/public_html/site/daily-automation.sh`)
7. ✅ Check logs: `tail ~/public_html/site/logs/automation-*.log`
8. ✅ Review staged products at `/admin/review-products.php`
9. ✅ Approve products to add them to your site

---

## Security Notes

- **Keep `.env` out of Git** — it's in `.gitignore`
- **Admin password** — currently set to: `N7_bwzBK3a1mv99fBTar5Gg2rpKvxJEQDlIvByjMwKs`
  - Change it in `site/public/admin/review-products.php` if you want a different password
  - Access admin panel at: `https://kitchenfindsfavorites.com/admin/review-products.php`
- **SSH access should be key-based**, not password (set in hPanel)
- **Logs contain API details** — consider restricting log access: `chmod 600 logs/*`
- **Credentials in `.env`** — Only readable by your user: `chmod 600 site/.env`

---

Questions? Check the scripts themselves — they have detailed comments explaining each step.
