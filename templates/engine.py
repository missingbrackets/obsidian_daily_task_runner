"""Template engine for creating daily and weekly notes.

Templates use Obsidian-style {{date:FORMAT}} placeholders plus
custom placeholders like {{title}}, {{Insured}}, etc.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from string import Template

# ── Built-in templates matching the user's Obsidian setup ──────────────

DAILY_TEMPLATE = """\
## 🔥 Top 3 Must-Do Today
- [ ]
- [ ]
- [ ]

---

## ✅ Daily Task List
- [ ]

---

## 📥 Carryover From Yesterday
- [ ]

---

### 🖥️ Landed On Desk List

---

## 🧠 Notes / Brain Dump
-

---

## 🌙 End of Day Review
**Wins today:**
-

**Move to tomorrow:**
- [ ]

## Case Pricings

## 📋 Tasks Still Open This Week
"""

WEEKLY_TEMPLATE = """\
# Week of {week_date}

## 🎯 Weekly Outcomes (Not tasks — results)
-
-
-

---

## 📋 Master Task List (This Week)

### 🧑‍💻 Work
- [ ]
- [ ]

### 🏠 Life Admin
- [ ]
- [ ]

### 💪 Health
- [ ]
- [ ]

### 🌱 Personal / Growth
- [ ]
- [ ]

---

## 🚫 Not This Week (Parking Lot)
-

---

## Project Tasks Due This Week

## Project Tasks Due Next Week
"""

PROJECT_TEMPLATE = """\
# {title}

## 🎯 Outcome / Definition of Done
What does "finished" look like?

---

## 🧠 Brain Dump
-

---

## 🪜 Next Actions (Only physical, doable steps)

- [ ]

---

## 📅 Waiting / Blocked
-

---

## ✅ Completed
- [ ]
"""

CASE_PRICING_TEMPLATE = """\
# Case Pricing – {Insured} – {Broker} – {LOB} – {InceptionDate}

---

TECHNICAL:
QUOTE:
WALK:
BIGGEST RISK:
WHY THIS PRICE IS RIGHT:

## 📌 1. Submission Snapshot

**Broker:** {Broker}
**Insured:** {Insured}

**Class / LOB:** {LOB}
**Layer:**
**Inception / Expiry:** {InceptionDate}
**Deadline:**
**Status:** ☐ Quoted ☐ NTU ☐ Bound ☐ Declined

### Risk Summary (3–5 lines)

> What is this risk, really?

---

## 🎯 2. Outcome / Definition of Done

- Technical price calculated and documented
- Key assumptions stated clearly
- Peer review complete (if required)
- Underwriter aligned on commercial range
- Files saved in correct location
- Learning captured (post-bind)

---

## 📂 3. Information Received

### Exposure
- SOV
- Exposure
- Limits & Deductibles
- Structure (attachments, reinstatements)
- Territories
- Historical exposure changes

### Claims
- Loss runs (valued as at?)
- Large loss details
- Cat losses separated?
- Attritional vs large split possible?

### Wordings / Coverage Notes
- Key extensions:
- Exclusions:
- Non-standard features:

---

## 🔎 4. Exposure & Data Assessment

**Data Quality:** ☐ Strong ☐ Adequate ☐ Weak

## Issues / adjustments needed:

## Exposure adjustments made:

## Loss adjustments made:

---

## 📊 5. Experience Analysis

### Loss Summary
- Latest ultimate loss ratio:
- Attritional LR:
- Large loss impact:
- Cat impact:

### Adjustments Made
- Trended to:
- Large loss cap:
- Burn adjustments:
- One-offs removed:

**Selected view of experience:**

> (Why this selection?)

---

## 🧮 6. Technical Pricing Build-Up

### A. Burning Cost View
- Adjusted expected losses:
- Expense load:
- Profit / risk load:
- Technical rate:

### B. Model View (if applicable)
- Model used:
- Key parameters:
- Output:
- Model adjustments:

### C. Exposure / Benchmark View
- Market rate level:
- Internal benchmark:
- Peer risks:

---

## 🧠 7. Actuarial Judgement

Where am I exercising judgement?
- Credibility weighting
- Large loss treatment
- Trend selection
- Exposure adequacy
- Model adjustment
- Cycle / market load

**Blended technical price:**

Rationale:

> Why is this the right number?

---

## 💼 8. Commercial Overlay

## Underwriter view:
## Broker expectation:

Market conditions:
- Soft / Flat / Hard ?

Strategic considerations:
- New business?
- Portfolio diversification?
- Capacity deployment?
- Relationship value?

**Recommended quoting range:**

Walk-away price:

---

## ⚠ 9. Risk & Sensitivity

Main sensitivities:
- Large loss frequency
- Severity tail
- Exposure misstatement
- Wordings creep

Simple stress tests:
- +10% loss →
- −10% exposure →
- 1 extra large loss →

---

## 🏛 10. Governance & Documentation

- Pricing file saved
- Assumptions documented
- Peer review complete
- Reviewer:
- Key challenge points:

## Model limitations noted:

---

## 📤 11. Final Output to UW

**Technical price:**

**Selected quote:**

**Rate change vs expiring:**

**Key messages to communicate:**

---

## 📅 12. Post-Bind Review (Complete After Outcome Known)

Outcome: ☐ Bound ☐ Lost ☐ Declined

If bound:
- Bound premium:
- Final structure changes:
- Deviation from technical (%):

If lost:
- Lost to:
- Approx competing level:

### What did I learn?

### Should anything change in future pricings?

---

## 🪜 Next Actions

(Only physical, doable steps)

- [ ]

---

## 📅 Waiting / Blocked

---

## ✅ Completed

- [ ]
"""


def create_daily_note(vault_path: str, daily_folder: str, target_date: date | None = None) -> Path:
    """Create a daily note from template. Returns the path to the new file."""
    target_date = target_date or date.today()
    vault = Path(vault_path)
    folder = vault / daily_folder
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{target_date.strftime('%Y-%m-%d')}.md"
    filepath = folder / filename

    if filepath.exists():
        return filepath  # Don't overwrite

    content = DAILY_TEMPLATE
    filepath.write_text(content, encoding="utf-8")
    return filepath


def create_weekly_note(vault_path: str, weekly_folder: str, target_date: date | None = None) -> Path:
    """Create a weekly note. target_date should be any day in the target week."""
    target_date = target_date or date.today()
    monday = target_date - timedelta(days=target_date.weekday())
    vault = Path(vault_path)
    folder = vault / weekly_folder
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"Week of {monday.strftime('%Y-%m-%d')}.md"
    filepath = folder / filename

    if filepath.exists():
        return filepath

    content = WEEKLY_TEMPLATE.format(week_date=monday.strftime("%Y-%m-%d"))
    filepath.write_text(content, encoding="utf-8")
    return filepath


def create_project_note(vault_path: str, projects_folder: str, title: str) -> Path:
    """Create a project note from template."""
    vault = Path(vault_path)
    folder = vault / projects_folder
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{title}.md"
    filepath = folder / filename

    if filepath.exists():
        return filepath

    content = PROJECT_TEMPLATE.format(title=title)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def create_case_pricing_note(
    vault_path: str,
    case_pricing_folder: str,
    insured: str,
    broker: str,
    lob: str,
    inception_date: str,
) -> Path:
    """Create a case pricing note from template."""
    vault = Path(vault_path)
    folder = vault / case_pricing_folder
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"Case Pricing – {insured} – {broker} – {lob} – {inception_date}.md"
    filepath = folder / filename

    if filepath.exists():
        return filepath

    content = CASE_PRICING_TEMPLATE.format(
        Insured=insured,
        Broker=broker,
        LOB=lob,
        InceptionDate=inception_date,
    )
    filepath.write_text(content, encoding="utf-8")
    return filepath
