# Hughes Guide

A PMO decision-support workbench. Guides project scheduling and change management teams to the right templates and request classifications, routes submissions through reviewer + QA workflows, pre-screens documents with Claude, tracks SLA breaches, and visualises pipeline aging on a Gantt-style timeline.

## What's inside

- **Home** — pipeline counts, SLA breach count, reviewer load, workspace export
- **Submit** — decision-tree wizards for schedule templates and change requests
- **Pipeline** — searchable list with stage tracking + SLA pills; detail view with advance / return / reopen actions and per-item SLA bar
- **Timeline** — Gantt-style horizontal chart of every item, coloured by stage, with ⚠ markers on breached items
- **Documents** — Claude pre-screens uploaded PDFs or pasted text against your criteria
- **Settings** — feature toggles, editable templates / change types / reviewers, workspace import, reset, backend status

## Run locally

Requires Python 3.9+.

```bash
# In the project directory:
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure secrets (optional for local dev)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml — at minimum, ANTHROPIC_API_KEY for the Documents tab.
# Leave SUPABASE_URL / SUPABASE_KEY blank to use local SQLite.

streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Deploy to Streamlit Community Cloud

1. Push this folder to a **public GitHub repository** (free tier requires public).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app**, select the repo, set main file path to `app.py`.
4. Before deploying, open **Advanced settings → Secrets** and paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   SUPABASE_URL      = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_KEY      = "your-service-role-key"
   ```
5. Deploy. Initial build takes ~2 minutes.

App lives at `https://<your-app-name>.streamlit.app`.

---

## Durable storage with Supabase

Streamlit Community Cloud's container filesystem is **ephemeral** — anything written to disk (including the bundled SQLite file) is wiped on redeploys and idle restarts. To keep submissions, templates, and reviewer config alive across restarts, wire up Supabase. The free tier is generous; setup takes about ten minutes.

### Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com). Note the project URL (`https://abcdefgh.supabase.co`).
2. **Run the table setup SQL.** In Supabase: **SQL Editor → New query**, paste the contents of `supabase_setup.sql`, run it. This creates a single `hughes_guide_kv` table with a JSONB value column.
3. **Grab the service role key.** In Supabase: **Project Settings → API → Project API keys → `service_role`** (the longer one, not the `anon` key). This bypasses Row Level Security so the app has full read/write access.
4. **Add the credentials to Streamlit secrets** — either in your Cloud app's Secrets section, or locally in `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_KEY = "eyJhbGciOi..."   # the service role key
   ```
5. **Restart the app.** Settings shows a green "● Supabase" badge when connected. The sidebar shows the same indicator on every page.

### How the backend switch works

At startup the app checks for `SUPABASE_URL` and `SUPABASE_KEY`. If both are present, all reads and writes go to Supabase. If either is missing, the app falls back to the local SQLite file (`hughes_guide.db`). Flip between the two by adjusting secrets and rerunning.

### Migrating existing data

Moving from local SQLite to Supabase:

1. On the **Home** tab, click **"Export full workspace (JSON)"**. Save the file.
2. Configure `SUPABASE_URL` and `SUPABASE_KEY` (see steps 1–4 above).
3. Restart the app. The backend is now Supabase but empty.
4. Go to **Settings → Import workspace** and upload the JSON you exported.

That moves every submission, template, reviewer, and feature toggle into Supabase.

### Security note

The setup above uses the **service role key**, which bypasses Row Level Security entirely. Fine for a single-tenant app where only the admin (you) configures the secrets and your team accesses the deployed Streamlit app. If you ever expose the app to anonymous users or need multi-tenant auth, switch to the `anon` key, enable RLS on the table, and add Supabase Auth. The commented-out policy block in `supabase_setup.sql` is a starting point.

---

## SLA breach tracking

Every template and change type has an SLA string like `"5 business days"`, `"10 days"`, or `"Same business day"`. The app parses these on the fly and tracks each submission's elapsed time against its SLA.

- **On track** — under 80% of SLA elapsed (green pill)
- **Due soon** — at 80% or more, still under 100% (amber pill)
- **Breached** — past 100% of SLA (red pill, marked with ⚠ on the Timeline)
- **Closed** — item was approved or returned; status frozen at completion time

Where you'll see it:

- **Home** — "SLA breaches" stat card and a banner alert when any are breached
- **Sidebar** — persistent ⚠ counter on every page when breaches exist
- **Pipeline** — coloured pill on every row, plus an "SLA" filter dropdown
- **Item detail** — full SLA tracking card with elapsed/total bar
- **Timeline** — breached items flagged with ⚠ next to their bar

"Business days" SLAs count weekdays only (Mon–Fri). "Days" SLAs count calendar days. Edit any template or change type's SLA in Settings — formats accepted: `"N business days"`, `"N days"`, `"Same business day"`, or leave it blank for no SLA.

Disable SLA tracking entirely from Settings → Features if you want a quieter UI.

---

## Timeline (Gantt) view

Every item appears as a horizontal bar from its creation time to either now (if in-flight) or its completion time (if approved/returned). Bars are coloured by current stage, sorted newest-first, and hover reveals submitter, type, risk, and SLA status. Breached items get a ⚠ marker at the right edge.

Filters: by type (schedule / change / all), and "Include completed" to hide approved/returned items.

Most useful for spotting:
- Items sitting in `lead_review` for much longer than peers
- Reviewer bottlenecks (cluster of bars stuck at the same stage)
- Throughput shape week-over-week

Hide the Timeline tab from Settings → Features if you don't want it.

---

## Customizing the decision logic

The wizards are tag-driven, not hard-coded. To change how recommendations route:

- **Templates** (Settings → Schedule templates): each template has a `tags` list. Tags should match the answer values your team selects in the wizard (e.g. `software`, `medium-duration`, `iterative`). When someone runs the wizard, templates are ranked by how many of their tags match the chosen answers. To re-route projects, edit the tags.
- **Change types** (Settings → Change request types): same logic, field is called `conditions`.
- **Reviewers** (Settings → Team leads): each reviewer has an `expertise` list. Auto-assignment picks the reviewer with the most overlap who still has capacity headroom (default cap is 4 concurrent items).
- **SLA** on any template or change type: just edit the SLA string. The app re-parses on every render.

If a recommendation looks wrong, the fix is almost always in the tags — not in the wizard questions.

---

## Files in this repo

```
hughes-guide/
├── app.py                          # Entire application
├── requirements.txt                # Python dependencies
├── supabase_setup.sql              # One-time SQL to run in Supabase
├── README.md                       # This file
├── .gitignore                      # Excludes secrets and local DB
└── .streamlit/
    ├── config.toml                 # Theme (cream / ink / rust)
    └── secrets.toml.example        # Template — copy and edit, never commit secrets.toml
```

## License

Internal use. Not for redistribution.
