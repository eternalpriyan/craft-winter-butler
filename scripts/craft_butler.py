import argparse
import json
import os
import sys
import datetime
import requests
import google.generativeai as genai

# --- 1. Path & Config Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")

# NOTE: Calendar integration planned for future release

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Error: Config file not found at {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # Validation
    if "PASTE" in config['api_urls']['daily_notes'] or "PASTE" in config['gemini_api_key']:
        print("\n⚠️  PLEASE CONFIGURE YOUR KEYS FIRST!")
        print(f"    Open this file: {CONFIG_PATH}")
        sys.exit(1)

    # Sanitize URLs
    for key in config['api_urls']:
        config['api_urls'][key] = config['api_urls'][key].rstrip('/')

    return config

# --- 2. API Clients ---

def get_ai_response(prompt, api_key, model_name="gemini-2.5-flash"):
    genai.configure(api_key=api_key)
    # Use configured model
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def fetch_blocks(base_url, params=None):
    """Generic fetch wrapper for multi-document API."""
    url = f"{base_url}/blocks"
    if not params:
        params = {}
    if 'maxDepth' not in params:
        params['maxDepth'] = 1  # Default depth
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        # Check if response has content
        if not response.text:
            print(f"⚠️  Empty response from {url}")
            return []

        data = response.json()
        # Multi-document API can return either a document with content or items list
        if "content" in data:
            return data.get("content", [])
        elif "items" in data:
            return data.get("items", [])
        else:
            return []
    except requests.exceptions.HTTPError as e:
        print(f"⚠️  HTTP Error: {e.response.status_code} - {e.response.text[:200]}")
        return []
    except requests.exceptions.JSONDecodeError as e:
        print(f"⚠️  JSON Error: {e}")
        print(f"    Response text: {response.text[:200]}")
        return []

def insert_blocks(base_url, blocks, target_location):
    """
    Inserts blocks to multi-document API.
    target_location format:
    - For daily notes: {"date": "today", "position_type": "start"}
    - For pages: {"page_id": "...", "position_type": "end"}
    """
    url = f"{base_url}/blocks"
    headers = {"Content-Type": "application/json"}

    payload = {"blocks": blocks}

    # Handle different target location formats
    if "date" in target_location:
        # Daily notes with date - need to get page ID first
        date_val = target_location["date"]
        position_type = target_location.get("position_type", "start")

        # Fetch the page ID for this date
        try:
            resp = requests.get(url, headers=headers, params={"date": date_val, "maxDepth": 0})
            if resp.ok:
                page_data = resp.json()
                page_id = page_data.get("id")
                if page_id:
                    payload["date"] = date_val
                    payload["position"] = {
                        "position": position_type,
                        "pageId": page_id
                    }
                else:
                    print("⚠️  Could not get page ID for date")
                    return None
            else:
                print(f"⚠️  Could not fetch daily note for {date_val}")
                return None
        except Exception as e:
            print(f"⚠️  Error fetching page ID: {e}")
            return None

    elif "page_id" in target_location:
        # Inserting into a specific page
        payload["id"] = target_location["page_id"]
        payload["position"] = {
            "position": target_location.get("position_type", "end"),
            "pageId": target_location["page_id"]
        }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        if not response.text:
            print(f"⚠️  Empty response after insert")
            return None

        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Craft API Write Error: {e.response.status_code}")
        print(f"    Response: {e.response.text[:300]}")
        return None
    except requests.exceptions.JSONDecodeError as e:
        print(f"⚠️  JSON decode error after insert: {e}")
        print(f"    Response text: {response.text[:300]}")
        return None

# --- 3. Monthly Logic ---

def get_monthly_doc_id(base_url):
    """Get the document ID for the monthly logs document."""
    try:
        # Try to get documents list (multi-document API)
        url = f"{base_url}/documents"
        response = requests.get(url, headers={"Content-Type": "application/json"})
        if response.ok:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                return data["items"][0]["id"]

        # Fallback: try to fetch blocks and extract ID from response
        url = f"{base_url}/blocks"
        response = requests.get(url, headers={"Content-Type": "application/json"}, params={"maxDepth": 0})
        if response.ok:
            data = response.json()
            if "id" in data:
                return data["id"]
    except:
        pass
    return None

def ensure_month_page(base_url):
    """
    Checks if a page for 'November 2025' exists in the Monthly Doc.
    If not, creates it. Returns the pageId.
    """
    current_month_name = datetime.datetime.now().strftime("%B %Y")

    # Get the monthly document ID first
    doc_id = get_monthly_doc_id(base_url)
    if not doc_id:
        print("❌ Could not find monthly document ID")
        return None

    # Read root blocks of the Monthly Document
    root_blocks = fetch_blocks(base_url, {"id": doc_id, "maxDepth": 1})

    # Search for existing month page
    for block in root_blocks:
        md = block.get("markdown", "")
        if md.strip() == current_month_name:
            print(f"   ✓ Found existing page for {current_month_name}")
            return block.get("id")

    # Create if missing
    print(f"   + Creating new page for {current_month_name}...")
    new_page_block = [{
        "type": "text",
        "textStyle": "page",
        "markdown": current_month_name
    }]

    # Insert at top of Monthly Log doc
    result = insert_blocks(base_url, new_page_block, {"page_id": doc_id, "position_type": "start"})
    if result and "items" in result:
        return result["items"][0]["id"]
    return None

# --- 4. Helpers ---

def extract_todos(blocks):
    """Recursively extract unfinished tasks from blocks."""
    todos = []
    for block in blocks:
        if block.get("listStyle") == "task":
            task_info = block.get("taskInfo", {})
            if task_info.get("state") == "todo":
                todos.append(block.get("markdown", ""))
        # Recursive check if deep fetching
        if "content" in block and isinstance(block["content"], list):
            todos.extend(extract_todos(block["content"]))
    return todos

def extract_completed_tasks(blocks):
    """Recursively extract completed tasks from blocks."""
    completed = []
    for block in blocks:
        if block.get("listStyle") == "task":
            task_info = block.get("taskInfo", {})
            if task_info.get("state") == "done":
                completed.append(block.get("markdown", ""))
        # Recursive check if deep fetching
        if "content" in block and isinstance(block["content"], list):
            completed.extend(extract_completed_tasks(block["content"]))
    return completed

def extract_content_with_state(blocks, max_blocks=50):
    """Extracts markdown from blocks, adding [x]/[ ] for tasks."""
    lines = []
    for block in blocks[:max_blocks]:
        md = block.get("markdown", "")
        
        # Add task state if applicable
        if block.get("listStyle") == "task":
            state = block.get("taskInfo", {}).get("state")
            if state == "done":
                md = f"[x] {md}"
            elif state == "todo":
                md = f"[ ] {md}"
            elif state == "canceled":
                md = f"[-] {md}"
        
        if md:
            lines.append(md)
            
    return "\n".join(lines)

def get_unfinished_tasks(days, daily_url):
    """Fetch unfinished tasks from the last N days."""
    context_lines = []
    today = datetime.date.today()

    for i in range(1, days + 1):
        past_date = today - datetime.timedelta(days=i)
        date_str = past_date.strftime("%Y-%m-%d")

        url = f"{daily_url}/blocks"
        try:
            resp = requests.get(url, headers={"Content-Type": "application/json"},
                              params={"date": date_str, "maxDepth": 5})
            if resp.ok:
                blocks = resp.json().get("content", [])
                todos = extract_todos(blocks)
                if todos:
                    context_lines.append(f"Unfinished from {date_str}:")
                    for t in todos:
                        context_lines.append(f"- {t}")
        except:
            continue

    if not context_lines:
        return "No unfinished tasks found."
    return "\n".join(context_lines)

def get_recent_daily_notes(days, daily_url):
    """Fetch actual content from recent daily notes (not just tasks)."""
    notes = []
    today = datetime.date.today()

    for i in range(1, days + 1):
        past_date = today - datetime.timedelta(days=i)
        date_str = past_date.strftime("%Y-%m-%d")
        readable_date = past_date.strftime("%A, %B %d")

        url = f"{daily_url}/blocks"
        try:
            resp = requests.get(url, headers={"Content-Type": "application/json"},
                              params={"date": date_str, "maxDepth": 2})
            if resp.ok:
                data = resp.json()
                blocks = data.get("content", [])

                # Extract meaningful content (skip empty, headers, tasks)
                content_pieces = []
                for block in blocks[:20]:  # Limit to first 20 blocks
                    md = block.get("markdown", "").strip()
                    if md and len(md) > 10:  # Skip very short blocks
                        # Skip common headers
                        if not md.startswith("##") and not md.startswith("---"):
                            content_pieces.append(md)

                if content_pieces:
                    note_summary = "\n".join(content_pieces[:5])  # Max 5 pieces
                    notes.append(f"**{readable_date}:**\n{note_summary}")
        except:
            continue

    if not notes:
        return "No recent daily notes found."
    return "\n\n".join(notes)

def get_monthly_context(monthly_url):
    """
    Read the current month's page from Monthly Doc to get progressive summaries.
    This provides the narrative arc that empowers morning briefings.
    """
    current_month_name = datetime.datetime.now().strftime("%B %Y")

    # Get the monthly document ID first
    doc_id = get_monthly_doc_id(monthly_url)
    if not doc_id:
        return f"Could not access monthly document."

    # Fetch root blocks to find month page
    root_blocks = fetch_blocks(monthly_url, {"id": doc_id, "maxDepth": 1})

    month_page_id = None
    for block in root_blocks:
        md = block.get("markdown", "")
        if md.strip() == current_month_name:
            month_page_id = block.get("id")
            break

    if not month_page_id:
        return f"No monthly summaries found for {current_month_name} yet."

    # Fetch content of the month page
    try:
        url = f"{monthly_url}/blocks"
        resp = requests.get(url, headers={"Content-Type": "application/json"},
                          params={"id": month_page_id, "maxDepth": 2})
        if resp.ok:
            data = resp.json()
            blocks = data.get("content", [])
            summaries = []
            for block in blocks:
                md = block.get("markdown", "").strip()
                if md and not md.startswith("#"):  # Skip headers
                    summaries.append(md)

            if summaries:
                return "\n".join(summaries)
            else:
                return f"Month page exists for {current_month_name}, but no summaries logged yet."
    except Exception as e:
        print(f"⚠️  Error reading month page: {e}")

    return f"Could not read monthly summaries for {current_month_name}."

# --- 5. Modes ---

def mode_morning(config):
    """
    Morning briefing powered by progressive summarization.
    Reads monthly summaries + recent daily notes + unfinished tasks.
    """
    print("☀️ Running Morning Routine...")
    daily_url = config['api_urls']['daily_notes']
    monthly_url = config['api_urls']['monthly_doc']

    # 1. Fetch Monthly Context (progressive summaries)
    print("📅 Reading monthly summaries...")
    monthly_context = get_monthly_context(monthly_url)

    # 2. Fetch Recent Daily Notes Content
    lookback_notes = config['settings']['morning'].get('lookback_days_notes', 2)
    print(f"📖 Reading last {lookback_notes} days' notes...")
    recent_notes = get_recent_daily_notes(lookback_notes, daily_url)

    # 3. Fetch Unfinished Tasks
    lookback_tasks = config['settings']['morning'].get('lookback_days_tasks', 3)
    print(f"📥 Checking last {lookback_tasks} days for unfinished tasks...")
    tasks_context = get_unfinished_tasks(lookback_tasks, daily_url)

    # 4. Generate Briefing
    today_str = datetime.datetime.now().strftime("%A, %B %d")
    prompt = config['prompts']['morning'].format(
        monthly_context=monthly_context,
        recent_notes=recent_notes,
        tasks_context=tasks_context,
        date=today_str
    )
    model_name = config.get('model_name', 'gemini-2.5-flash')
    briefing_md = get_ai_response(prompt, config['gemini_api_key'], model_name)

    if briefing_md:
        print("📝 Writing briefing to Daily Note as sub-page...")
        # Create a sub-page titled "Morning Briefing" with the content inside
        briefing_page = [{
            "type": "text",
            "textStyle": "page",
            "markdown": "☀️ Morning Briefing",
            "content": [
                {"type": "text", "markdown": briefing_md}
            ]
        }]
        insert_blocks(daily_url, briefing_page, {"date": "today", "position_type": "end"})
        print("✅ Morning briefing complete.")

def backfill_month(config, daily_url, monthly_url):
    """
    Backfill missing days of the current month with summaries.
    Called on first run or when monthly log has gaps.
    """
    print("\n📦 Checking for backfill needs...")

    # Get existing month entries
    doc_id = get_monthly_doc_id(monthly_url)
    if not doc_id:
        print("⚠️  Could not access monthly doc for backfill")
        return

    current_month_name = datetime.datetime.now().strftime("%B %Y")
    root_blocks = fetch_blocks(monthly_url, {"id": doc_id, "maxDepth": 2})

    # Find month page and existing entries
    month_page_id = None
    existing_days = set()

    for block in root_blocks:
        if block.get("markdown", "").strip() == current_month_name:
            month_page_id = block.get("id")
            # Check existing entries
            for entry in block.get("content", []):
                md = entry.get("markdown", "")
                # Extract day number from "**Friday 28:**" format
                if "**" in md and ":" in md:
                    try:
                        day_part = md.split("**")[1].split(":")[0].strip()
                        day_num = int(day_part.split()[-1])  # Get last word (the number)
                        existing_days.add(day_num)
                    except:
                        pass
            break

    if not month_page_id:
        month_page_id = ensure_month_page(monthly_url)

    # Determine days to backfill (1st of month to yesterday)
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    days_to_fill = []

    for day in range(1, yesterday.day + 1):
        if day not in existing_days:
            date_obj = datetime.date(today.year, today.month, day)
            days_to_fill.append(date_obj)

    if not days_to_fill:
        print("✅ No backfill needed - month is complete")
        return

    print(f"📝 Backfilling {len(days_to_fill)} days...")

    max_words = config['settings']['evening'].get('summary_max_words', 25)

    for date_obj in days_to_fill:
        date_str = date_obj.strftime("%Y-%m-%d")
        day_str = date_obj.strftime("%A %d")

        # Fetch that day's content
        try:
            url = f"{daily_url}/blocks"
            resp = requests.get(url, headers={"Content-Type": "application/json"},
                              params={"date": date_str, "maxDepth": 3})

            if resp.ok:
                blocks = resp.json().get("content", [])
                content_snippet = extract_content_with_state(blocks, max_blocks=50)

                if content_snippet.strip():
                    # Extract completed tasks for backfill
                    completed_tasks_list = extract_completed_tasks(blocks)
                    completed_tasks_str = "\n".join([f"- {t}" for t in completed_tasks_list]) if completed_tasks_list else "No tasks marked as completed."

                    # Generate summary
                    prompt = config['prompts']['evening_summary'].format(
                        context=content_snippet,
                        completed_tasks=completed_tasks_str,
                        max_words=max_words
                    )
                    model_name = config.get('model_name', 'gemini-2.5-flash')
                    summary = get_ai_response(prompt, config['gemini_api_key'], model_name)

                    if summary:
                        summary = summary.strip().strip('"').strip("'").strip()
                        entry_md = f"**{day_str}:** {summary}"

                        # Insert into monthly doc
                        insert_blocks(monthly_url,
                                    [{"type": "text", "markdown": entry_md}],
                                    {"page_id": month_page_id, "position_type": "end"})
                        print(f"   ✓ Backfilled {day_str}")
        except Exception as e:
            print(f"   ⚠️  Could not backfill {day_str}: {e}")
            continue

    print("✅ Backfill complete\n")

def mode_evening(config):
    """
    Evening progressive summarization.
    Reads today's full notes, generates ONE-LINE summary, logs to monthly doc only.
    Backfills missing days if configured.
    """
    print("🌙 Running Evening Progressive Summarization...")
    daily_url = config['api_urls']['daily_notes']
    monthly_url = config['api_urls']['monthly_doc']

    # Backfill check (if enabled and needed)
    if config['settings']['evening'].get('backfill_on_first_run', False):
        backfill_month(config, daily_url, monthly_url)

    # 1. Fetch Today's Content
    print("📥 Reading today's notes...")
    try:
        resp = requests.get(f"{daily_url}/blocks",
                          headers={"Content-Type": "application/json"},
                          params={"date": "today", "maxDepth": 3})
        today_blocks = resp.json().get("content", [])
    except:
        today_blocks = []

    content_snippet = extract_content_with_state(today_blocks, max_blocks=50)
    if not content_snippet:
        content_snippet = "No notes recorded today."

    # 2. Generate ONE-LINE Summary
    print("🧠 Compressing to one-line summary...")
    
    # Extract completed tasks for higher fidelity
    completed_tasks_list = extract_completed_tasks(today_blocks)
    completed_tasks_str = "\n".join([f"- {t}" for t in completed_tasks_list]) if completed_tasks_list else "No tasks marked as completed."
    
    max_words = config['settings']['evening'].get('summary_max_words', 15)
    prompt = config['prompts']['evening_summary'].format(
        context=content_snippet,
        completed_tasks=completed_tasks_str,
        max_words=max_words
    )
    model_name = config.get('model_name', 'gemini-2.5-flash')
    summary = get_ai_response(prompt, config['gemini_api_key'], model_name)

    if summary:
        # Clean up the summary (remove quotes, extra whitespace)
        summary = summary.strip().strip('"').strip("'").strip()

        # 3. Log ONLY to Monthly Doc (progressive summarization = compression)
        print("📅 Logging to Monthly Document...")

        # Find/Create Month Page
        month_page_id = ensure_month_page(monthly_url)

        if month_page_id:
            # Insert one-line entry with day of week and date prefix
            today_str = datetime.datetime.now().strftime("%A %d")  # e.g. "Friday 28"
            entry_md = f"**{today_str}:** {summary}"

            insert_blocks(monthly_url,
                         [{"type": "text", "markdown": entry_md}],
                         {"page_id": month_page_id, "position_type": "end"})
            print(f"✅ Summary logged to monthly doc: \"{summary}\"")
        else:
            print("❌ Error: Could not find or create month page.")

# --- 6. Entry ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['morning', 'evening'])
    args = parser.parse_args()

    if args.mode:
        cfg = load_config()
        if args.mode == 'morning': mode_morning(cfg)
        elif args.mode == 'evening': mode_evening(cfg)
    else:
        print("Use --mode morning or --mode evening")