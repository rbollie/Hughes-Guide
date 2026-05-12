"""
Hughes Guide — user guide PDF generator.
Produces a multi-page PDF document for the in-app Help page.
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, ListFlowable, ListItem,
)
from reportlab.pdfgen import canvas


# Brand colours
INK = HexColor("#1A1A1A")
RUST = HexColor("#A0432C")
MUTED = HexColor("#5A5A5A")
CREAM = HexColor("#FAF7F2")
RUST_SOFT = HexColor("#F2E5DE")
BORDER = HexColor("#E5DDC9")


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle(
            "CoverEyebrow", parent=base["Normal"],
            fontSize=9, leading=12, textColor=RUST,
            fontName="Helvetica-Bold", spaceAfter=12, alignment=TA_LEFT,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"],
            fontSize=54, leading=58, textColor=INK,
            fontName="Times-Roman", spaceAfter=10, alignment=TA_LEFT,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub", parent=base["Normal"],
            fontSize=15, leading=22, textColor=MUTED,
            spaceAfter=24, alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontSize=24, leading=28, textColor=INK,
            fontName="Times-Roman", spaceAfter=8, spaceBefore=4,
        ),
        "h1_num": ParagraphStyle(
            "H1Num", parent=base["Normal"],
            fontSize=10, leading=13, textColor=RUST,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontSize=13, leading=18, textColor=INK,
            fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=14,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10.5, leading=15.5, textColor=INK, spaceAfter=8,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["Normal"],
            fontSize=10, leading=14, textColor=MUTED, spaceAfter=6,
        ),
        "list_item": ParagraphStyle(
            "ListItem", parent=base["Normal"],
            fontSize=10.5, leading=15, textColor=INK, leftIndent=18,
            bulletIndent=4, spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"],
            fontSize=8, leading=10, textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "toc_item": ParagraphStyle(
            "TOC", parent=base["Normal"],
            fontSize=11, leading=18, textColor=INK, spaceAfter=2,
        ),
    }


def _page_decorator(canv: canvas.Canvas, doc):
    """Footer with page number on every page after the cover."""
    canv.saveState()
    if doc.page > 1:
        canv.setFont("Helvetica", 8)
        canv.setFillColor(MUTED)
        canv.drawString(0.9 * inch, 0.5 * inch, "Hughes Guide · User Guide")
        canv.drawRightString(letter[0] - 0.9 * inch, 0.5 * inch, f"Page {doc.page}")
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.5)
        canv.line(0.9 * inch, 0.65 * inch, letter[0] - 0.9 * inch, 0.65 * inch)
    canv.restoreState()


def _bullets(items, styles):
    """Build a bulleted list paragraph block."""
    return ListFlowable(
        [ListItem(Paragraph(t, styles["list_item"]),
                  leftIndent=14, value="bullet", bulletColor=RUST)
         for t in items],
        bulletType="bullet", start="•", leftIndent=14,
    )


def _section(num, title, blocks, styles):
    out = [
        Paragraph(f"§ {num}", styles["h1_num"]),
        Paragraph(title, styles["h1"]),
        Spacer(1, 6),
    ]
    out.extend(blocks)
    out.append(Spacer(1, 10))
    return out


def generate_user_guide_pdf() -> bytes:
    """Generate the full Hughes Guide user guide as PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.95 * inch, rightMargin=0.95 * inch,
        title="Hughes Guide — User Guide",
        author="Hughes Guide",
    )
    s = _build_styles()
    story = []

    # ===== COVER =====
    story.append(Spacer(1, 1.4 * inch))
    story.append(Paragraph("HUGHES GUIDE", s["cover_eyebrow"]))
    story.append(Paragraph("User Guide", s["cover_title"]))
    # Decorative rust accent line as a tiny table
    accent = Table([[" "]], colWidths=[0.7 * inch], rowHeights=[3])
    accent.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RUST)]))
    story.append(accent)
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "A PMO decision-support workbench for project teams.<br/>"
        "Decision-tree wizards. Reviewer routing. Document pre-screening.<br/>"
        "SLA breach alerts. Pipeline tracking. Final QA visibility.",
        s["cover_sub"]))
    story.append(Spacer(1, 2.6 * inch))
    story.append(Paragraph(
        f"Version 1.2 · {datetime.utcnow().strftime('%B %Y')}",
        s["muted"]))
    story.append(PageBreak())

    # ===== TABLE OF CONTENTS =====
    story.append(Paragraph("§ Contents", s["h1_num"]))
    story.append(Paragraph("In this guide", s["h1"]))
    story.append(Spacer(1, 8))
    toc = [
        "1. About Hughes Guide",
        "2. Getting access",
        "3. Your role and what you can do",
        "4. The tabs in your sidebar",
        "5. Submitting work (schedule or change request)",
        "6. Reviewing as a Team Lead",
        "7. Final QA approvals (administrators)",
        "8. The Timeline view",
        "9. Document pre-screening with Claude",
        "10. Understanding SLA tracking",
        "11. Administrators: managing users",
        "12. Administrators: customising templates and routing",
        "13. Troubleshooting and FAQ",
        "14. Glossary",
    ]
    for line in toc:
        story.append(Paragraph(line, s["toc_item"]))
    story.append(PageBreak())

    # ===== SECTION 1 =====
    story.extend(_section("1", "About Hughes Guide", [
        Paragraph(
            "Hughes Guide is a workbench that helps PMO supervisors get back their evenings. "
            "It guides two kinds of teams — scheduling teams who build project schedules, and "
            "change management teams who file change requests — through decision-tree wizards "
            "that pick the right template or classification. Submissions then route automatically "
            "to the appropriate reviewer, move through a defined approval pipeline, and only the "
            "items that need final sign-off land on the supervisor's desk.",
            s["body"]),
        Paragraph(
            "The point is to reduce time supervisors spend on routine routing and triage. "
            "Sixty-hour weeks become forty when the structure handles what the structure can handle.",
            s["body"]),
        Paragraph("What's in the app", s["h2"]),
        _bullets([
            "<b>Decision-tree wizards</b> for schedule templates and change request classifications",
            "<b>Risk scoring</b> — every submission gets a 0–10 score based on its wizard answers",
            "<b>Reviewer routing</b> — auto-assignment based on expertise tags and current load",
            "<b>Document pre-screening</b> — Claude reads uploaded PDFs against your criteria",
            "<b>SLA tracking</b> — every submission tracked against its template's deadline",
            "<b>Timeline view</b> — Gantt-style chart for spotting aged or bottlenecked work",
            "<b>Role-based access</b> — four roles (admin, lead, submitter, viewer)",
        ], s),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 2 =====
    story.extend(_section("2", "Getting access", [
        Paragraph(
            "Hughes Guide is invite-only. Your administrator creates your account with a username, "
            "an initial password, and a role.",
            s["body"]),
        Paragraph("When you receive your credentials", s["h2"]),
        _bullets([
            "Open the Hughes Guide URL your administrator gave you in a browser",
            "Click <b>Sign in →</b> on the landing page",
            "Enter your username and the initial password your administrator shared",
            "Once signed in, go to <b>Settings → Change password</b> to set your own password",
        ], s),
        Paragraph(
            "If you forget your password, your administrator can reset it for you. There is no "
            "automated email reset flow in this version.",
            s["muted"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 3 =====
    story.extend(_section("3", "Your role and what you can do", [
        Paragraph(
            "Hughes Guide has four roles. Your administrator assigned one when they created your "
            "account, and it shows next to your name in the sidebar.",
            s["body"]),
        Paragraph("Administrator", s["h2"]),
        Paragraph(
            "Full access. Manages user accounts and roles. Edits templates, change types, "
            "workflows, and reviewer rosters. Runs <b>Final QA</b> on every submission — items "
            "are not approved until an administrator signs off. Configures system settings.",
            s["body"]),
        Paragraph("Team Lead", s["h2"]),
        Paragraph(
            "Reviews submissions through the Peer Review and Team Lead Review stages. Can return "
            "items to the submitter with notes. Sees every submission in the workspace. Cannot "
            "perform Final QA — that is reserved for administrators.",
            s["body"]),
        Paragraph("Submitter", s["h2"]),
        Paragraph(
            "Runs the schedule or change request wizards. Sees only their own submissions in the "
            "Pipeline. Can use document pre-screening. Cannot review or act on other people's work.",
            s["body"]),
        Paragraph("Viewer", s["h2"]),
        Paragraph(
            "Read-only access to the Pipeline and Timeline. Useful for stakeholders, executives, "
            "and auditors who need to observe progress without acting on it.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 4 =====
    story.extend(_section("4", "The tabs in your sidebar", [
        Paragraph(
            "After signing in, your sidebar shows tabs based on your role.",
            s["body"]),
        Paragraph("Everyone sees", s["h2"]),
        _bullets([
            "<b>Home</b> — dashboard with stats, breach alerts, and quick links",
            "<b>Pipeline</b> — filterable list of submissions (filtered by your role's visibility)",
            "<b>Timeline</b> — Gantt-style aging view (if enabled)",
            "<b>Help</b> — this guide, downloadable as PDF",
            "<b>Settings</b> — your profile and password change",
        ], s),
        Paragraph("Submitters and above also see", s["h2"]),
        _bullets([
            "<b>Submit</b> — the decision-tree wizards for schedules and change requests",
            "<b>Documents</b> — Claude-powered document pre-screening",
        ], s),
        Paragraph("Administrators see the full Settings", s["h2"]),
        Paragraph(
            "Including user management, template editing, change type editing, reviewer rosters, "
            "feature toggles, workspace import/export, and a reset option.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 5 =====
    story.extend(_section("5", "Submitting work", [
        Paragraph("To submit a schedule template", s["h2"]),
        _bullets([
            "Click <b>Submit</b> in the sidebar",
            "Choose <b>Schedule template</b>",
            "Answer the 6 wizard questions — type, duration, team size, scope, compliance, dependencies",
            "Review the top-match template plus alternatives",
            "Optionally select a different template if you disagree with the recommendation",
            "Confirm details — title, your name, workflow type, optional notes",
            "Click <b>Submit to pipeline →</b>",
        ], s),
        Paragraph("To submit a change request", s["h2"]),
        _bullets([
            "Click <b>Submit</b> in the sidebar",
            "Choose <b>Change request</b>",
            "Answer the 5 wizard questions — urgency, risk, impact scope, reversibility, precedent",
            "Review the recommended classification (Standard / Normal / Major / Emergency)",
            "Confirm and submit",
        ], s),
        Paragraph(
            "Your submission appears immediately in the Pipeline. It is auto-assigned to the "
            "best-fit reviewer based on expertise tags and current load.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 6 =====
    story.extend(_section("6", "Reviewing as a Team Lead", [
        Paragraph(
            "When a submission is assigned to you, you can find it in the Pipeline at "
            "the Draft, Peer Review, or Team Lead Review stage.",
            s["body"]),
        Paragraph("To review a submission", s["h2"]),
        _bullets([
            "Open <b>Pipeline</b> and filter by stage if helpful",
            "Click <b>Open →</b> on the item you want to review",
            "Review submitter notes, selected criteria, risk score, and SLA status",
            "Take action: <b>Advance to next stage</b> if it looks good, or <b>Return to submitter</b> with a note explaining what's needed",
        ], s),
        Paragraph(
            "Tip: use the <b>Documents</b> tab to pre-screen any PDF documents associated with "
            "the submission before reviewing. Claude pre-screens against the relevant criteria.",
            s["muted"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 7 =====
    story.extend(_section("7", "Final QA approvals", [
        Paragraph(
            "Items at the Final QA / QC stage need administrator sign-off. Each has been vetted "
            "by a Team Lead already — your job is the final pass.",
            s["body"]),
        Paragraph("Process", s["h2"]),
        _bullets([
            "Open <b>Pipeline</b> and filter to the Final QA / QC stage",
            "Click <b>Open →</b> on each item",
            "Review the full activity log and history of the submission",
            "Take action: <b>Advance to Approved</b> for sign-off, or <b>Return to submitter</b> if rework is needed",
        ], s),
        Paragraph(
            "If you need to revisit an approved or returned item, open it and click <b>Reopen</b>. "
            "It returns to the first stage of its workflow for another pass.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 8 =====
    story.extend(_section("8", "The Timeline view", [
        Paragraph(
            "The Timeline tab is a Gantt-style horizontal chart. Every submission is a bar from "
            "its creation date to either now (in-flight) or its completion date (approved or returned). "
            "Bars are coloured by current stage. Items past their SLA show a ⚠ marker at the right edge.",
            s["body"]),
        Paragraph("Most useful for", s["h2"]),
        _bullets([
            "Spotting items stuck in the same stage longer than peers (likely bottleneck)",
            "Reviewing reviewer workload visually across the workspace",
            "Showing stakeholders what is moving and what is not",
            "Identifying which reviewers consistently take longer than the SLA",
        ], s),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 9 =====
    story.extend(_section("9", "Document pre-screening with Claude", [
        Paragraph(
            "The Documents tab is a pre-screening tool. It takes a PDF (or pasted text) and "
            "returns an analysis from Claude.",
            s["body"]),
        Paragraph("How to use it", s["h2"]),
        _bullets([
            "Pick an analysis lens — Schedule template review, Change request review, or Custom criteria",
            "Upload a PDF or paste document text",
            "Click <b>Run analysis</b>",
            "Claude returns a top-line verdict, strengths, issues (ordered by severity), and recommended next actions",
        ], s),
        Paragraph(
            "Use this BEFORE assigning to a team lead. Lead reviewers see a focused review "
            "instead of a blank document, which usually saves them 15-20 minutes per item.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 10 =====
    story.extend(_section("10", "Understanding SLA tracking", [
        Paragraph(
            "Every template and change type carries an SLA string like \"5 business days\" or "
            "\"Same business day\". The app parses these on the fly and tracks each submission's "
            "elapsed time against its SLA.",
            s["body"]),
        Paragraph("States", s["h2"]),
        _bullets([
            "<b>On track</b> (green) — under 80% of SLA elapsed",
            "<b>Due soon</b> (amber) — at 80% or more, still under 100%",
            "<b>Breached</b> (red) — past 100% of SLA; flagged on Home, Pipeline, Timeline, and the sidebar",
            "<b>Closed</b> — approved or returned; status frozen at completion time",
        ], s),
        Paragraph(
            "\"Business days\" SLAs count weekdays only (Monday–Friday). \"Days\" SLAs count "
            "calendar days. Edit any template or change type's SLA in Settings — formats accepted "
            "include \"N business days\", \"N days\", \"Same business day\", or blank for no SLA.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 11 =====
    story.extend(_section("11", "Administrators: managing users", [
        Paragraph("Open <b>Settings</b> and find <b>Users &amp; Access</b>.", s["body"]),
        Paragraph("To add a new user", s["h2"]),
        _bullets([
            "Click <b>+ Add new user</b>",
            "Fill in display name, username (3–30 chars, letters/digits/._-), initial password (8+ chars), and role",
            "Click <b>Create user</b>",
            "Share the credentials with the user via your secure channel — the app does not email them",
            "Tell them to change their password from their own Settings page on first login",
        ], s),
        Paragraph("To edit or remove a user", s["h2"]),
        _bullets([
            "Expand the user's row in the Users &amp; Access section",
            "Change display name, role, or active status",
            "Optionally reset their password (sets a new one — share it with them securely)",
            "Click <b>Delete user</b> to remove",
            "You cannot delete your own account or the last active administrator",
        ], s),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 12 =====
    story.extend(_section("12", "Customising templates and routing", [
        Paragraph(
            "The wizards are tag-driven, not hard-coded. Adjusting tags is the main way to "
            "change which template gets recommended for which kind of work.",
            s["body"]),
        Paragraph("Schedule templates", s["h2"]),
        Paragraph(
            "Each template has a name, description, tag list, default workflow, SLA, and risk base. "
            "Tags should match the wizard answer values your team will pick "
            "(e.g. <i>software, medium-duration, iterative</i>). Templates are ranked by how many "
            "of their tags overlap with the user's chosen answers.",
            s["body"]),
        Paragraph("Change request types", s["h2"]),
        Paragraph(
            "Same logic, but the field is called <i>conditions</i> instead of tags. Standard, "
            "Normal, Major, and Emergency are shipped as defaults — you can edit, add, or remove "
            "them in Settings.",
            s["body"]),
        Paragraph("Team Leads / Reviewers", s["h2"]),
        _bullets([
            "Each reviewer has a name, role, expertise tags, and capacity (max concurrent reviews)",
            "Auto-assignment picks the reviewer with most expertise overlap who has capacity headroom",
            "Default capacity is 4 — adjust per reviewer as needed",
            "Add reviewers in Settings → Team leads / reviewers",
        ], s),
        Paragraph(
            "If a recommendation looks wrong, the fix is almost always in the tags on the "
            "template or change type — not in the wizard questions themselves.",
            s["muted"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 13 =====
    story.extend(_section("13", "Troubleshooting and FAQ", [
        Paragraph("I forgot my password", s["h2"]),
        Paragraph(
            "Ask your administrator to reset it. They can do this from Settings → Users → "
            "expand your row → Reset password. They will share a new password with you, and "
            "you can change it again from your own Settings page once you sign in.",
            s["body"]),
        Paragraph("The wrong reviewer was auto-assigned", s["h2"]),
        Paragraph(
            "Open the item from Pipeline. Your administrator can manually reassign. The "
            "underlying fix is to adjust the expertise tags on the reviewers in Settings.",
            s["body"]),
        Paragraph("Can't see another user's submission", s["h2"]),
        Paragraph(
            "That is intentional. Submitters see only their own items. If you need to share "
            "work with someone, ask the submitter to add you in the notes field, or ask "
            "your administrator.",
            s["body"]),
        Paragraph("Item is stuck in the pipeline", s["h2"]),
        Paragraph(
            "Check the assigned reviewer and stage. If the reviewer is at capacity or "
            "unavailable, the admin can reassign by opening the item. SLA breach indicators "
            "will surface anything overdue.",
            s["body"]),
        Paragraph("Pipeline shows zero items but I submitted one", s["h2"]),
        Paragraph(
            "If you're a Submitter, you only see your own items. Confirm you're signed in "
            "as the user that submitted the item. Otherwise, check the stage filter at the "
            "top of the Pipeline — you may have filtered to a stage with no matches.",
            s["body"]),
        Paragraph("Document analysis isn't working", s["h2"]),
        Paragraph(
            "The Documents tab requires an Anthropic API key configured in Streamlit Cloud "
            "secrets as ANTHROPIC_API_KEY. Your administrator can verify this in the Streamlit "
            "Cloud dashboard. If the key is set but billing is not, requests will fail.",
            s["body"]),
    ], s))
    story.append(PageBreak())

    # ===== SECTION 14 =====
    story.extend(_section("14", "Glossary", [
        Paragraph("<b>Pipeline</b> — the list of all in-flight submissions in the workspace.", s["body"]),
        Paragraph("<b>Stage</b> — current step in the workflow. The defaults are Draft, Peer Review, Team Lead Review, Final QA / QC, Approved, and Returned.", s["body"]),
        Paragraph("<b>Workflow</b> — the sequence of stages a submission moves through. The defaults are Fast-Track (2 stages), Standard (3 stages), and Extended (4 stages).", s["body"]),
        Paragraph("<b>SLA</b> — Service Level Agreement. The time limit before a submission is considered overdue. Each template and change type has its own SLA string.", s["body"]),
        Paragraph("<b>Risk score</b> — automatic 0–10 score based on the submitter's wizard answers. High-risk submissions (7+) trigger a recommendation to use the Extended workflow.", s["body"]),
        Paragraph("<b>Auto-assignment</b> — the system picks the best-fit reviewer for a submission based on expertise tag overlap and current load.", s["body"]),
        Paragraph("<b>Tag</b> — a keyword on a template that matches the user's wizard answer values, used for ranking which template to recommend.", s["body"]),
        Paragraph("<b>Condition</b> — same as a tag, but on change request types instead of schedule templates.", s["body"]),
        Paragraph("<b>Capacity</b> — the maximum number of concurrent in-flight reviews a Team Lead can be auto-assigned. Default is 4.", s["body"]),
        Paragraph("<b>Reviewer load</b> — how many in-flight items are currently assigned to each reviewer. Visible on the Home page for administrators and team leads.", s["body"]),
    ], s))

    # ===== BUILD =====
    doc.build(story, onFirstPage=_page_decorator, onLaterPages=_page_decorator)
    buf.seek(0)
    return buf.getvalue()
