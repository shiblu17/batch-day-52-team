"""
Batch Day 52 Team Hub — RYUK (Gemini-backed) Assistant
Team members chat with a real LLM scoped ONLY to Batch Day 52 data.
Read + write (update sponsor status). Private workspace data excluded.
"""
import os, re, gradio as gr, time, subprocess
from google import genai
from collections import defaultdict

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SPONSORS = os.path.join(REPO_DIR, "Sponsors", "README.md")
LEARNINGS = os.path.join(REPO_DIR, "LEARNINGS.md")
KEY = os.environ.get("GEMINI_KEY", "")
client = genai.Client(api_key=KEY) if KEY else None

# simple in-memory cache + per-minute rate guard
_cache = {}
_last_call = [0.0]
MIN_INTERVAL = 2.0  # seconds between API calls to avoid quota burn

SYSTEM = """You are RYUK — the Batch Day 52 team assistant (AI teammate version).
You ONLY discuss Batch Day 52 data: sponsors, members, schedule, events, documents.
You do NOT have access to any personal/private workspace data (loans, personal tasks) — if asked, say you don't have that.
You can read and UPDATE sponsor status. When a user reports a sponsor update, update the file.
You also LEARN: when the team shares new insights, contact preferences, deal context, or anything useful, append it to the LEARNINGS file (via the tool) so it persists.
Respond in Bangla (English terms OK). Be concise, helpful, proactive.
When giving analysis, use the actual data. Suggest next steps for follow-ups."""

def read_learnings():
    if not os.path.exists(LEARNINGS):
        return ""
    with open(LEARNINGS, encoding="utf-8") as f:
        return f.read()

def append_learning(text):
    now = time.strftime("%Y-%m-%d %H:%M")
    with open(LEARNINGS, "a", encoding="utf-8") as f:
        f.write(f"\n- [{now}] {text}\n")
    # backup to git
    try:
        subprocess.run(["git", "-C", REPO_DIR, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", REPO_DIR, "commit", "-q", "-m", f"learning {now}"], capture_output=True)
        subprocess.run(["git", "-C", REPO_DIR, "push", "-q", "origin", "main"], capture_output=True)
    except Exception:
        pass

def backup_sponsors():
    try:
        subprocess.run(["git", "-C", REPO_DIR, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", REPO_DIR, "commit", "-q", "-m", "sponsor update"], capture_output=True)
        subprocess.run(["git", "-C", REPO_DIR, "push", "-q", "origin", "main"], capture_output=True)
    except Exception:
        pass

def read_sponsors():
    if not os.path.exists(SPONSORS):
        return "স্পন্সর ফাইল পাওয়া যায়নি।"
    with open(SPONSORS, encoding="utf-8") as f:
        return f.read()

def update_sponsor_status(name, status):
    txt = read_sponsors()
    pattern = re.compile(r"(##\s*" + re.escape(name) + r".*?)(?=## |\Z)", re.S)
    m = pattern.search(txt)
    if not m:
        return f"❌ '{name}' নামে কোনো স্পন্সর পাওয়া যায়নি।"
    block = m.group(1)
    new_block = re.sub(r"স্ট্যাটাস:.*", f"স্ট্যাটাস: {status}", block, count=1)
    txt = txt[:m.start()] + new_block + txt[m.end():]
    with open(SPONSORS, "w", encoding="utf-8") as f:
        f.write(txt)
    return f"✅ {name} স্ট্যাটাস '{status}' আপডেট হয়েছে।"

def parse_update(msg):
    """Detect: 'RAK Contacted' or 'Remark Negotiating' or 'update X status Y'."""
    m = re.search(r"(?:update\s+)?([A-Za-z][\w\s&.]*?)\s+(?:কে\s+)?(Contacted|Negotiating|Confirmed|Signed|Lead|Lost|Paid)", msg, re.I)
    if m:
        return m.group(1).strip(), m.group(2).capitalize()
    return None

def gemini(prompt):
    # rate guard: avoid hammering quota
    now = time.time()
    if now - _last_call[0] < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - (now - _last_call[0]))
    _last_call[0] = time.time()
    # cache identical prompts
    if prompt in _cache:
        return _cache[prompt]
    for i in range(3):
        try:
            r = client.models.generate_content(model="gemini-flash-latest", contents=prompt).text.strip()
            _cache[prompt] = r
            return r
        except Exception as e:
            if "503" in str(e) and i < 2:
                time.sleep(4)
                continue
            if "429" in str(e):
                return "⚠️ কোটা শেষ হয়ে গেছে (429)। কিছুক্ষণ পর আবার চেষ্টা করুন, বা নতুন API key দিন।"
            return "⚠️ Gemini এরর: " + str(e)[:120]
    return "⚠️ Gemini রিট্রাই ফেইল।"

def respond(message, history):
    if not client:
        return "⚠️ Gemini API key সেট নাই।"
    cmd = parse_update(message)
    if cmd:
        result = update_sponsor_status(*cmd)
        backup_sponsors()  # persist + git backup
        data = read_sponsors()
        learn = read_learnings()
        prompt = f"{SYSTEM}\n\n[Learnings so far]\n{learn}\n\n[Sponsor file]\n{data}\n\n[User] {message}\n[System action] {result}\nConfirm to user in Bangla + suggest next step."
        return gemini(prompt)
    data = read_sponsors()
    learn = read_learnings()
    # detect learning intent
    if any(k in message.lower() for k in ["জানলাম", "শিখলাম", "নোট", "মনে রাখবে", "learned", "note"]):
        append_learning(message)
    prompt = f"{SYSTEM}\n\n[Learnings so far]\n{learn}\n\n[Sponsor file]\n{data}\n\n[User] {message}"
    return gemini(prompt)

demo = gr.ChatInterface(
    respond,
    title="🎓 Batch Day 52 — RYUK Team Hub (AI)",
    description="টিম মেম্বারদের জন্য RYUK (AI স্পন্সর অ্যাসিস্টেন্ট)। শুধু Batch Day 52 ডাটা। উদাহরণ: 'কে কে স্পন্সর?', 'RAK Contacted', 'Remark deal final হয়েছে'",
    examples=["কে কে স্পন্সর এখনো Contacted না?", "RAK কল হয়ে গেছে", "Remark deal final করো", "পরবর্তী ফলোআপ কী?"],
)

if __name__ == "__main__":
    demo.launch(share=True)
