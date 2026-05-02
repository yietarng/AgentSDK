# Customer Support ReAct Agent — Quick Start Tutorial

## Prerequisites

- Python 3.11+
- A running MySQL server
- An OpenAI API key
- A Tavily API key (free tier at https://tavily.com)

---

## 1. Install dependencies

```bash
cd AgentSDK
pip install -r requirements.txt
```

---

## 2. Configure environment

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...          # your OpenAI key
TAVILY_API_KEY=tvly-...        # your Tavily key

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_DATABASE=support_db
```

---

## 3. Set up the database

Create the database, then run the schema:

```bash
mysql -u your_db_user -p -e "CREATE DATABASE IF NOT EXISTS support_db;"
mysql -u your_db_user -p support_db < database/schema.sql
```

This creates three tables and seeds 5 sample support articles (shipping, returns,
billing, account, security).

---

## 4. Run the agent

```bash
python main.py
```

You'll be prompted for a user ID. Use a consistent ID across sessions to preserve
memory:

```
Enter your user ID (or press Enter for 'anonymous'): alice
```

Or pass it directly:

```bash
python main.py --user-id alice
python main.py --user-id alice --session-id sess_001  # resume a specific session
```

---

## 5. Example conversation

```
[Customer Support Agent]
User ID : alice
Session : f3a1bc2d-...

You: How do I return an item?

Agent: You can return any unused item within 30 days of delivery.
       To start a return, go to "My Orders" in your account,
       select the item, and click "Return Item". You'll receive
       a prepaid shipping label within 24 hours.
       [Return and Refund Policy]

You: I'm a premium member by the way.

Agent: Noted! As a premium member you get free returns with no
       questions asked. I've saved that to your profile.

You: What's the latest news on OpenAI?

Agent: [searches the web via Tavily]
       Here's what's current on OpenAI: ...
```

---

## 6. How memory works

| Type | Scope | Storage |
|---|---|---|
| **Short-term** | Current session only | `conversations` table |
| **Long-term** | Persists across sessions | `user_memory` table |

When you reveal a durable fact ("I'm on the pro plan"), the agent calls
`save_user_memory` and stores it. Next time you start a new session with the
same user ID, those facts are automatically injected into the system prompt.

To inspect what the agent remembers about a user:

```sql
SELECT memory_key, memory_value FROM user_memory WHERE user_id = 'alice';
```

---

## 7. Add your own knowledge base articles

```sql
INSERT INTO knowledge_base (title, content, category) VALUES (
  'Subscription Cancellation',
  'To cancel your subscription, go to Account Settings > Billing
   and click Cancel Plan. Your access continues until the end of
   the current billing period. No refunds are issued for partial months.',
  'billing'
);
```

The agent will find and cite new articles immediately — no restart needed.

---

## 8. Run the tests

```bash
python -m pytest tests/ -v
```

All 108 tests pass in under a second (no real DB or API calls required).

---

## Key tuning knobs (in `.env`)

| Variable | Default | Effect |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o` | Swap to `gpt-4o-mini` to reduce cost |
| `AGENT_MAX_TURNS` | `15` | Max ReAct loop iterations before giving up |
| `MAX_HISTORY_ITEMS` | `40` | Conversation history window per turn (~10 ReAct cycles) |
