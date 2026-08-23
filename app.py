"""
Batch Day 52 Team Hub — RYUK Assistant (Team Version)
Gradio chat app. Scoped ONLY to batch-day-52-team data.
Team members can read + update sponsor status. No access to private workspace.
"""
import os, re, gradio as gr

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SPONSORS = os.path.join(REPO_DIR, "Sponsors", "README.md")

SYSTEM = """আপনি RYUK — Batch Day 52 স্পন্সর টিমের অ্যাসিস্টেন্ট।
আপনি শুধু Batch Day 52 এর ডাটা নিয়ে কথা বলবেন: স্পন্সর, মেম্বার, শিডিউল, ইভেন্ট, ডক।
অন্য কোনো ব্যক্তিগত তথ্য নাই আপনার কাছে — সেটা বলে দেবেন।
টিম মেম্বারদের স্পন্সর স্ট্যাটাস আপডেট করতে সাহায্য করুন।
উত্তর সংক্ষিপ্ত ও বাংলায় দিন (ইংরেজি টার্ম ব্যবহার যায়)।"""

def read_sponsors():
    if not os.path.exists(SPONSORS):
        return "স্পন্সর ফাইল পাওয়া যায়নি।"
    with open(SPONSORS, encoding="utf-8") as f:
        return f.read()

def update_sponsor_status(name, status):
    """Update a sponsor's status in the README."""
    txt = read_sponsors()
    # find sponsor block
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

def parse_cmd(msg):
    """Detect update commands like 'RAK Contacted' or 'update Remark Negotiating'."""
    m = re.search(r"(?:update\s+)?([A-Za-z][\w\s]*?)\s+(Contacted|Negotiating|Confirmed|Signed|Lead|Lost|Paid)", msg, re.I)
    if m:
        return m.group(1).strip(), m.group(2).capitalize()
    return None

def respond(message, history):
    msg = message.strip()
    # command: update sponsor status
    cmd = parse_cmd(msg)
    if cmd:
        return update_sponsor_status(*cmd)
    # read query
    data = read_sponsors()
    # simple keyword summary
    if any(k in msg.lower() for k in ["কে কে", "list", "স্ট্যাটাস", "লিস্ট", "who"]):
        lines = [l for l in data.split("\n") if l.startswith("## ") and "স্পন্সর লিস্ট" not in l and "প্রপোজাল" not in l]
        return "📋 স্পন্সর লিস্ট:\n" + "\n".join(lines[:15])
    # default: echo context (lightweight, no LLM to keep free/HF-friendly)
    return (SYSTEM + "\n\n[কুয়েরি] " + msg + "\n\n"
            "বর্তমান স্পন্সর ডাটা:\n" + data[:1500] +
            "\n\n💡 আপডেট করতে লিখুন: 'RAK Contacted' বা 'Remark Negotiating'")

demo = gr.ChatInterface(
    respond,
    title="🎓 Batch Day 52 — RYUK Team Hub",
    description="টিম মেম্বারদের জন্য স্পন্সর/শিডিউল হাব। শুধু Batch Day 52 ডাটা। উদাহরণ: 'RAK Contacted' বা 'কে কে স্পন্সর?'",
    examples=["কে কে স্পন্সর?", "RAK Contacted", "Remark Negotiating", "Pran এর স্ট্যাটাস কী?"],
)

if __name__ == "__main__":
    demo.launch()
