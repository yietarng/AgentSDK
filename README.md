# Customer Support ReAct Agent

A customer support agent built with the **OpenAI Agents SDK** that reasons and acts in a ReAct loop (Reason → Act → Observe → Respond). It searches an internal knowledge base, queries the live web, and maintains both short-term conversation history and long-term persistent user memory across sessions — all backed by MySQL.

---

## Features

- **ReAct reasoning loop** — the agent thinks before acting, observes tool results, retries on poor results, and only responds when it has grounded information
- **Internal knowledge base** — MySQL FULLTEXT search over support articles; returns ranked excerpts
- **Live web search** — Tavily API for current information not covered by the knowledge base
- **Short-term memory** — full conversation history persisted to MySQL and restored each turn via the SDK `Session` protocol
- **Long-term memory** — durable user facts (name, account tier, preferences) saved across sessions and auto-injected into the system prompt
- **Tool output verifier** — tags empty or error results with `[NO RESULTS]` / `[LOW QUALITY RESULT]` so the agent retries instead of hallucinating
- **108 unit tests** — all modules tested with mocks; no real DB or API calls required

---

## Use Case

This agent is designed for **businesses that want to automate first-line customer support**. It handles routine queries around the clock — freeing human agents for complex escalations — while delivering a personalised experience through persistent memory.

### Who it is for

| Audience | How they use it |
|---|---|
| **E-commerce stores** | Answer questions about orders, returns, shipping, and payments |
| **SaaS companies** | Help users with account issues, plan upgrades, and feature questions |
| **Any subscription business** | Handle billing queries, cancellations, and policy explanations |

### What the agent handles

| User asks about | Agent action |
|---|---|
| Return / refund policy | Searches knowledge base → cites the relevant article |
| Order tracking | Searches KB; escalates if order number is needed |
| Account tier or plan benefits | Retrieves KB article; recalls saved account facts from memory |
| Current news or third-party info | Falls back to live web search via Tavily |
| A fact the user already stated | Reads it from long-term memory — does not ask again |

### Memory behaviour across sessions

```
Session 1 — user says: "I'm on the premium plan"
  → Agent saves  account_tier: premium  to user_memory table

Session 2 (next day, new session ID, same user ID)
  → Agent loads  account_tier: premium  from DB before the first message
  → System prompt already contains "Known User Facts: account_tier: premium"
  → Agent greets the user with context intact, no re-introduction needed
```

---

## Example Dataset

The schema seeds five knowledge base articles automatically. You can extend the
dataset by inserting additional rows into the `knowledge_base` table.

### Seeded articles (from `database/schema.sql`)

| Title | Category | Key content |
|---|---|---|
| Order Tracking and Delivery Status | shipping | How to track orders; standard vs express delivery times; what to do if marked delivered but not received |
| Return and Refund Policy | returns | 30-day return window; how to initiate a return; refund processing time; premium member free returns |
| Account Tiers and Benefits | billing | Standard / Plus / Premium plan features and pricing |
| Password Reset and Account Security | account | Reset steps; 2FA setup; what to do if account is compromised |
| Payment Methods and Billing Issues | billing | Accepted payment methods; how to fix a failed payment; invoice schedule |

### Adding your own articles

```sql
INSERT INTO knowledge_base (title, content, category) VALUES
(
  'Subscription Cancellation Policy',
  'To cancel your subscription go to Account Settings > Billing and click
   Cancel Plan. Your access continues until the end of the current billing
   period. We do not issue refunds for partial months. To pause instead of
   cancel, use the Pause Subscription option on the same page.',
  'billing'
),
(
  'Two-Factor Authentication Setup',
  'Enable 2FA from Account Settings > Security > Two-Factor Authentication.
   We support authenticator apps (Google Authenticator, Authy) and SMS.
   Backup codes are shown once during setup — store them securely.
   If you lose access, contact support with your account email and a
   government-issued ID for verification.',
  'account'
),
(
  'Bulk Order Discounts',
  'Orders of 10 or more units qualify for a 10% discount applied at checkout.
   Orders of 50 or more units qualify for 20%. For orders above 200 units
   contact our sales team at sales@example.com for a custom quote.
   Bulk discounts cannot be combined with promotional codes.',
  'pricing'
);
```

### Sample user memory rows

The agent writes these automatically during conversation. You can also seed them
manually to simulate a returning user:

```sql
INSERT INTO user_memory (user_id, memory_key, memory_value) VALUES
('alice', 'account_tier',       'premium'),
('alice', 'preferred_contact',  'email'),
('alice', 'preferred_language', 'English'),
('alice', 'recurring_issue',    'delayed shipments'),
('bob',   'account_tier',       'standard'),
('bob',   'preferred_name',     'Bobby');
```

---

## Example Prompts

The following prompts demonstrate the agent's behaviour across different
scenarios. Run them with `python main.py --user-id alice` after seeding the
database.

### Scenario 1 — Knowledge base retrieval

```
You: How do I return a product?

Agent: You can return any unused item in its original packaging within
       30 days of delivery. To start a return:
       1. Log into your account and go to "My Orders"
       2. Select the item and click "Return Item"
       3. A prepaid shipping label will be emailed within 24 hours
       Refunds are processed within 5–7 business days after we receive
       the item. [Return and Refund Policy]
```

### Scenario 2 — Long-term memory recall

```
-- Session 1 --
You: By the way, I prefer to be contacted by email.

Agent: Got it — I've noted that you prefer email contact. I'll make
       sure that's on file for future sessions.

-- Session 2 (new session, same user ID) --
You: How do I get support for a billing issue?

Agent: For billing issues you can reach our team directly. Since you
       prefer email, I'd recommend emailing billing@example.com with
       your account details and order number.
```

### Scenario 3 — Follow-up within a session (short-term memory)

```
You: What plans do you offer?

Agent: We offer three tiers:
       - Standard: free shipping on orders over $50
       - Plus ($9.99/mo): free shipping on all orders + priority support
       - Premium ($19.99/mo): free shipping, free returns, early sale
         access, and a dedicated account manager

You: What's the price difference between Plus and Premium?

Agent: Plus is $9.99/month and Premium is $19.99/month — a $10/month
       difference. Premium adds free returns, early sale access, and a
       dedicated account manager on top of everything in Plus.
```

### Scenario 4 — Web search fallback

```
You: What are the latest OpenAI model pricing changes?

Agent: [searching the web...]
       Based on current web results: OpenAI updated its pricing in ...
       [Source: openai.com/pricing]
```

### Scenario 5 — Retry on poor results

```
You: Tell me about the xyz123 feature

Agent: [searches KB — no results]
       [retries with broader query — still no results]
       I wasn't able to find information about "xyz123" in our knowledge
       base or on the web. This may be an internal feature not yet
       documented. Would you like me to escalate this to a specialist?
```

---

## Architecture

```
main.py
  └── agent/react_agent.py      ← run_turn(): orchestrates one conversation turn
        ├── agent/prompts.py    ← ReAct system prompt + memory injection
        ├── agent/context.py    ← AppContext (user_id, session_id, memories)
        ├── memory/
        │   ├── long_term.py    ← recall_memories / save_memory  →  user_memory table
        │   └── short_term.py   ← MySQLSession (SDK Session protocol)  →  conversations table
        └── tools/
            ├── retrieval.py    ← search_knowledge_base  →  knowledge_base table
            ├── web_search.py   ← web_search  →  Tavily API
            ├── memory_tools.py ← save_user_memory / recall_user_memory
            └── verifier.py     ← verify_tool_output (quality gate)
```

---

## Requirements

- Python 3.11+
- MySQL 8.0+
- OpenAI API key
- Tavily API key — free tier at https://tavily.com

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd AgentSDK
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

TAVILY_API_KEY=tvly-...

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_DATABASE=support_db
```

### 4. Create the database and run the schema

```bash
mysql -u your_db_user -p -e "CREATE DATABASE IF NOT EXISTS support_db;"
mysql -u your_db_user -p support_db < database/schema.sql
```

This creates three tables (`knowledge_base`, `user_memory`, `conversations`) and
seeds five sample support articles.

---

## Usage

### Start the agent

```bash
python main.py
```

Enter a user ID when prompted. Using the same ID across sessions preserves long-term memory.

### Pass arguments directly

```bash
# Specify user ID
python main.py --user-id alice

# Resume a specific session
python main.py --user-id alice --session-id sess_001
```

### End a session

Type `exit` or `quit`, or press `Ctrl+C`.

---

## Configuration

All settings are read from `.env`. Optional settings have defaults shown below.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | Model to use (`gpt-4o-mini` reduces cost) |
| `TAVILY_API_KEY` | — | Required. Tavily search API key |
| `MYSQL_HOST` | `localhost` | MySQL host |
| `MYSQL_PORT` | `3306` | MySQL port |
| `MYSQL_USER` | — | Required. MySQL username |
| `MYSQL_PASSWORD` | — | Required. MySQL password |
| `MYSQL_DATABASE` | — | Required. Database name |
| `MYSQL_POOL_SIZE` | `5` | Connection pool size |
| `AGENT_MAX_TURNS` | `15` | Max ReAct iterations per turn before giving up |
| `MAX_HISTORY_ITEMS` | `40` | Conversation history window sent to the model per turn |

---

## Project Structure

```
AgentSDK/
├── main.py                   # CLI entry point
├── config.py                 # Centralised settings from .env
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── context.py            # AppContext dataclass
│   ├── prompts.py            # ReAct system prompt and memory injection
│   └── react_agent.py        # Agent definition and run_turn()
│
├── database/
│   ├── connection.py         # MySQL connection pool
│   └── schema.sql            # Table definitions and seed data
│
├── memory/
│   ├── long_term.py          # Persistent user facts (user_memory table)
│   └── short_term.py         # Session history (conversations table)
│
├── tools/
│   ├── retrieval.py          # Knowledge base search tool
│   ├── web_search.py         # Tavily web search tool
│   ├── memory_tools.py       # save/recall memory tools
│   └── verifier.py           # Tool output quality gate
│
├── tests/
│   ├── conftest.py           # Fixtures and external package stubs
│   ├── test_verifier.py
│   ├── test_prompts.py
│   ├── test_long_term.py
│   ├── test_short_term.py
│   ├── test_retrieval.py
│   ├── test_web_search.py
│   ├── test_memory_tools.py
│   └── test_react_agent.py
│
└── doc/
    ├── tutorial.md           # Step-by-step usage guide
    └── code_walkthrough.md   # Main steps of every source file
```

---

## Running Tests

No real database or API keys are needed — all external dependencies are mocked.

```bash
python -m pytest tests/ -v
```

Expected output: **108 passed**.

---

## Documentation

| File | Contents |
|---|---|
| `doc/tutorial.md` | Full usage guide with examples |
| `doc/code_walkthrough.md` | Step-by-step breakdown of every source file |
