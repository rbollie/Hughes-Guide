# Hughes Guide

A PMO decision-support workbench with role-based access for project teams. Public landing page, admin-managed user accounts, decision-tree wizards, reviewer routing, document pre-screening via Claude, SLA tracking, and a Gantt-style timeline.

## What's inside

- **Landing page** — public-facing front door explaining the product, with a sign-in CTA
- **Home** — pipeline counts, SLA breach count, reviewer load, workspace export (scope depends on role)
- **Submit** — decision-tree wizards for schedule templates and change requests
- **Pipeline** — searchable list with stage tracking + SLA pills, detail view with role-gated actions
- **Timeline** — Gantt-style horizontal chart of every item, coloured by stage, with ⚠ markers on breached items
- **Documents** — Claude pre-screens uploaded PDFs or pasted text against your criteria
- **Settings** — feature toggles, user management (admin only), editable templates / change types / reviewers, workspace import, backend status

---

## Roles & permissions

Four roles, each with a different default view. The admin creates accounts and assigns roles from Settings → Users.

| Role | Submit | See others' items | Review (peer/lead) | Final QA | Manage users / templates |
|------|:---:|:---:|:---:|:---:|:---:|
| **Admin** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Team Lead** | ✓ | ✓ | ✓ | – | – |
| **Submitter** | ✓ | only own | – | – | – |
| **Viewer** | – | ✓ (read-only) | – | – | – |

- **Admin** owns Final QA and manages users, templates, change types, reviewers, and features.
- **Team Lead** can advance items through Peer Review and Team Lead Review stages, return items, see all submissions, export, and use Document Analysis.
- **Submitter** runs wizards and sees only items they created. Useful for the team members building schedules or filing change requests.
- **Viewer** is read-only across pipeline and timeline. Useful for stakeholders, observers, or auditors.

Non-admins can change their own display name and password from the Settings page. Admins can reset any user's password, deactivate accounts, or delete users (except themselves and the last active admin).

### First-run setup

On the very first launch (no users yet), Hughes Guide shows a one-time **"Create the first administrator"** form. After you create that account, the app forces a sign-in and you're in.

If you ever lose all admins (deleted the last one somehow), there's no recovery built into the UI — you'd need to wipe the `users` key in your storage backend (drop the row in Supabase, or `DELETE FROM kv WHERE key='users'` in SQLite) to trigger first-run again. Be careful with that.

### Security notes

- Passwords are hashed with **bcrypt** (12 rounds) before storage. The plain password is never written to disk or the database.
- There's no email verification, password reset email, or "remember me" cookie in v1. Sessions live in `st.session_state` and reset on full page reload — users sign in again. That's a deliberate scope choice for an admin-invited internal tool; for public-facing multi-tenant use, layer in Supabase Auth or similar.
- If you migrate from local SQLite to Supabase, your user list (with password hashes) moves with the rest of the data via the workspace export/import flow.

---

## Run locally

Requires Python 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml — at minimum, ANTHROPIC_API_KEY for the Documents tab.
# Leave SUPABASE_URL / SUPABASE_KEY blank to use local SQLite.

streamlit run app.py
```

Opens at `http://localhost:8501`. First load is the landing page; click **Sign in** → first-run admin creation → back to login → in.

## Deploy to Streamlit Community Cloud

1. Push this folder to a **public GitHub repository**.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. **New app**, select the repo, set main file path to `app.py`.
4. Before deploying, open **Advanced settings → Secrets** and paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   SUPABASE_URL      = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_KEY      = "your-service-role-key"
   ```
5. Deploy. First launch takes ~2 minutes.

App lives at `https://<your-app-name>.streamlit.app`. Anyone with the URL sees the landing page; only people you've created accounts for can sign in.

---

## Durable storage with Supabase

Streamlit Community Cloud's container filesystem is **ephemeral** — anything written to disk (including the bundled SQLite file) is wiped on redeploys and idle restarts. For durable storage of users, submissions, templates, and reviewer config, wire up Supabase. Free tier is generous and setup takes about ten minutes.

### Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com).
2. **Run the table setup SQL.** In Supabase: **SQL Editor → New query**, paste the contents of `supabase_setup.sql`, run it.
3. **Grab the service role key.** In Supabase: **Project Settings → API → `service_role`** (the longer one, not `anon`).
4. **Add to Streamlit secrets:**
   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_KEY = "eyJhbGciOi..."
   ```
5. **Restart the app.** A green "● Supabase" badge appears in the sidebar and Settings page when connected.

If `SUPABASE_URL` and `SUPABASE_KEY` are both set, all reads/writes go to Supabase. If either is missing, falls back to local SQLite. No code changes needed to switch.

### Migrating existing data

From local SQLite to Supabase: log in as admin → **Home → Export workspace (JSON)** → configure Supabase secrets → restart → **Settings → Import workspace** and upload the JSON. Users, items, templates, and settings all move over.

---

## SLA breach tracking

Every template and change type has an SLA string (`"5 business days"`, `"10 days"`, `"Same business day"`, etc.). The app tracks elapsed time against each item's SLA and flags states:

- **On track** (green) — under 80% of SLA elapsed
- **Due soon** (amber) — at 80%+, still under 100%
- **Breached** (red) — past 100% of SLA, marked with ⚠ on Timeline
- **Closed** — approved or returned; status frozen at completion

Visible on: Home stat card, sidebar ⚠ counter on every page, pipeline row pills, pipeline SLA filter, item detail SLA card, and Timeline ⚠ markers.

"Business days" SLAs count Mon–Fri only. "Days" SLAs count calendar days. Disable the whole feature from Settings → Features if you want a quieter UI.

---

## Timeline (Gantt) view

Every item appears as a horizontal bar from creation time to either now or completion. Coloured by current stage, hover shows submitter, type, risk, SLA. Breached items get ⚠ at the right edge. Filter by type and toggle whether to include completed items.

Most useful for spotting reviewer bottlenecks (cluster of bars stuck at the same stage) and items that have been sitting much longer than peers.

---

## Customizing the decision logic

The wizards are tag-driven:

- **Templates** (Settings → Schedule templates): each template has a `tags` list. Tags should match wizard answer values (`software`, `medium-duration`, `iterative`). Recommendations rank by tag overlap.
- **Change types** (Settings → Change request types): same, field is called `conditions`.
- **Reviewers** (Settings → Team leads): each has an `expertise` list. Auto-assignment picks the reviewer with most overlap who still has capacity headroom.
- **SLA** on any template or change type: edit the string. Re-parsed on every render.

Wrong recommendation? Almost always a tag fix, not a wizard question fix.

---

## Files in this repo

```
hughes-guide/
├── app.py                          # Entire application
├── requirements.txt                # Python dependencies (incl. bcrypt)
├── supabase_setup.sql              # One-time SQL for Supabase
├── README.md                       # This file
├── .gitignore                      # Excludes secrets and local DB
└── .streamlit/
    ├── config.toml                 # Theme (cream / ink / rust)
    └── secrets.toml.example        # Template — copy, edit, never commit
```

## License

Internal use. Not for redistribution.
