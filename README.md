# ❄️ Craft Winter Butler

**Progressive Summarization for Daily Notes**

Automatically compresses your daily notes into monthly summaries, then uses those summaries to generate context-aware morning briefings. Built with Craft's API + Google Gemini.

---

## 🎯 The Problem

Daily notes pile up. You lose track of what happened last week. You can't see patterns. Context vanishes.

**This solves it** by compressing daily notes → monthly summaries → morning context.

---

## 🧠 How It Works

### Evening (11 PM)
Reads today's full daily note → Generates specific 25-word summary → Logs to monthly document

**Example:** *"Friday 28: Attended Flow Basic & Essential classes, met Subba-ji for Calm in Chaos, decided on Cyber Weekend Gift Card promo, completed graduate survey."*

### Morning (5 AM)
Reads monthly summaries + recent 2 days' notes + unfinished tasks → Generates briefing as collapsible sub-page

**Plus:** Auto-backfills missing days if you start mid-month

---

## 🚀 Installation (5 Minutes)

### Before You Start

**IMPORTANT:** Move this entire folder to `Documents` (NOT Downloads - macOS blocks scripts there)

### Step 1: Get Your API Links

**For Monthly Logs:**
1. In Craft, create new document: **"Monthly Logs"**
2. Click **Share** → **Export** → **API**
3. Copy the URL (looks like: `https://connect.craft.do/links/XXXXX/api/v1`)

**For Daily Notes:**
1. Go to your Daily Notes space in Craft
2. Click **Share** → **Export** → **API**
3. Copy the URL

**Get Gemini Key:**
1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Create free account
3. Click **Get API Key** → Copy it

### Step 2: Configure

1. Right-click `config.json` → **Open With** → **TextEdit**
2. Replace `PASTE_MAGIC_LINK...` with your URLs:
   - `daily_notes`: Your daily notes API URL
   - `monthly_doc`: Your monthly logs API URL
   - `gemini_api_key`: Your Gemini API key
3. Save and close

### Step 3: Test It

1. Double-click `install_and_run.command`
2. **If you see security warning:**
   - Click **OK**
   - Right-click file → Hold **Option (⌥)** → Click **Open**
   - Click **Open** in popup
3. Choose **2** to test evening mode
4. Check Craft - you should see a new entry in Monthly Logs

### Step 4: Automate

1. Run `install_and_run.command` again
2. Type **3** and press Enter
3. Done! Runs automatically at 5 AM and 11 PM

---

## ✅ What You'll See

**In Daily Notes:**
- Morning sub-page with quote + what matters today
- Evening creates nothing (writes only to monthly doc)

**In Monthly Logs:**
- Auto-created "November 2025" sub-page
- One line per day: **"Thursday 27:** Met Nicole Laneng, taught Core..."

---

## 🔧 Troubleshooting

### "Permission denied" when running script
**Fix:** Make executable: `chmod +x install_and_run.command`

### "Config file not found"
**Fix:** Make sure you're in the correct directory. The script expects `config.json` in the same folder.

### "PASTE_YOUR_GEMINI_KEY_HERE" error
**Fix:** You forgot to edit config.json. Open it in TextEdit and paste your actual API keys.

### Script runs but nothing appears in Craft
**Check:**
1. Are your API URLs correct? They should start with `https://connect.craft.do/links/...`
2. Try running evening mode manually (option 2) and check the output
3. Look for error logs: `evening_error.txt` or `morning_error.txt` in the script folder

### Evening ran but didn't backfill the month
**Fix:** Set `"backfill_on_first_run": true` in config.json (under `settings.evening`)

### Automation not running
**Check:** `launchctl list | grep craftbot` - should show two agents
**Reload:**
```bash
launchctl unload ~/Library/LaunchAgents/com.craftbot.*.plist
launchctl load ~/Library/LaunchAgents/com.craftbot.*.plist
```

### Need to uninstall automation?
Run script → Choose option **4**

---

## ⚙️ Settings You Can Adjust

Edit `config.json`:

```json
"settings": {
  "morning": {
    "lookback_days_tasks": 3,     // How far back to check for unfinished tasks
    "lookback_days_notes": 2,     // How many recent days to read in detail
    "lookback_days_monthly": 30   // How much monthly context to include
  },
  "evening": {
    "summary_max_words": 25,      // Summary length
    "backfill_on_first_run": true // Auto-populate missing days
  }
}
```

---

## 📝 How to Submit Feedback

Found a bug? Email details to [your email] or post in Craft Slack #winter_challenge

---

## 🔮 Roadmap

- Figure out how to create backlinks (obsidian style wikilinks dont work when imported into Craft)
- Calendar integration (pull today's agenda into briefings)
- Weekly/yearly progressive summarization levels

