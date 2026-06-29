# config.py — Edit this before running the bot!

# ── Required ──────────────────────────────────────────────────────────────────
BOT_TOKEN = "8903300076:AAHGeLmRJ_LcXW3yioD7sdUXD4YkFusAeDI"       # From @BotFather

# ── Admin IDs (Telegram user IDs that can use /admin /grant /revoke) ─────────
ADMIN_IDS = [6696175051]                  # Replace with your Telegram user ID

# ── Plans ─────────────────────────────────────────────────────────────────────
FREE_DAILY_LIMIT   = 5      # Downloads per day on free plan
FREE_MAX_SIZE_MB   = 70     # Max file size for free users (MB)
PREMIUM_MAX_SIZE_MB = 10000  # Max file size for premium users (MB) = 2 GB

# ── Monetization ──────────────────────────────────────────────────────────────
AD_DURATION_SECONDS = 10    # How long to show ads to free users
PREMIUM_PRICE_USD  = 4.99   # Monthly price shown in /upgrade
PAYMENT_LINK       = "upi://pay?pa=8484028481-2@ybl&pn=ASHWINI%20SUNIL%20MALEWAR&mc=0000&mode=02&purpose=00"   # Your Stripe/PayPal link
ADMIN_USERNAME     = "@darshan0753m"                 # For upgrade support

# ── Storage ──────────────────────────────────────────────────────────────────
DB_FILE      = "data/users.json"
DOWNLOAD_DIR = "downloads"

# ── Queue ─────────────────────────────────────────────────────────────────────
MAX_CONCURRENT_DOWNLOADS = 10   # How many downloads run at once
QUEUE_TIMEOUT_SECONDS    = 300 # Max wait time in queue (5 min)
