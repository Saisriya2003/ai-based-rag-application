"""Seed a small library so chat works on first boot."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import Document
from app.ingest import ingest_bytes

AETHER_SPEC = """# Aether Desk - Product Specification

Owner: Maya Krishnan, Product
Status: Approved for build
Target launch: 14 October 2026
Company: Helios Labs

## Summary

Aether Desk is a lightweight workspace for distributed product teams at Helios Labs.
It keeps living specifications, a dated decision log, and a weekly pulse in one place
so a team can move without a heavier project-management suite.

## Users

Primary users are product managers, designers, and engineers working across Hyderabad,
Berlin, and remote contracts. A secondary audience is design partners who need read-only
access to a single specification.

## Goals

1. Record 80 percent of product decisions in the decision log within 48 hours.
2. Cut specification drift: fewer than two conflicting versions of a spec in circulation.
3. Make the weekly pulse take under twelve minutes to assemble from existing notes.

## Core features

- Living specs with section-level ownership and a last-reviewed date.
- Decision log entries that require a context paragraph, options considered, and a named owner.
- Weekly pulse: shipped, slipped, and a single risk - generated from the log, not a blank form.
- Comment threads that expire after the related decision is marked resolved.

## Non-goals

Aether Desk is not a replacement for chat, issue trackers, or roadmapping tools.
It will not include Gantt charts, time tracking, or customer-facing portals in v1.

## Technical notes

The v1 stack is React on the client, FastAPI for the service layer, and PostgreSQL
for documents and decision records. Search is lexical in v1; semantic retrieval is
scheduled for the November 2026 maintenance window.

## Launch criteria

Launch on 14 October 2026 if at least two internal squads have run a four-week pilot
and the decision-log completion rate stays above 70 percent in the final pilot week.
"""

LEAVE_POLICY = """# Helios Labs - Time Away Policy

Effective: 1 April 2026
Audience: Full-time employees and eligible contractors
System of record: Workday

## Paid time off

Full-time employees receive 22 days of paid time off (PTO) per calendar year,
accrued monthly. Unused PTO may carry over by up to 5 days into the next year.
Contractors on six-month or longer agreements receive 10 days of unpaid flexible leave.

## Sick leave

Employees receive 10 days of sick leave each year. Sick leave does not pay out
at departure and does not carry over. A clinician note is required after three
consecutive working days.

## Parental leave

Birth, adoptive, and partner parents receive 16 weeks of paid parental leave.
Leave may be taken continuously or in two blocks within the first twelve months
after the child's arrival. Notify People Operations at least 30 days in advance
when the date is known.

## How to request time away

Submit requests in Workday at least 10 business days before the first day of leave,
except for sick leave or emergencies. Managers respond within 3 business days.
People Operations can override a denial when coverage is documented.

## Blackout windows

The last two weeks of Q4 are a blackout for Finance and Customer Support except
for already-approved parental leave and certified medical leave. Engineering
blackouts are announced per squad during a release freeze.

## Contact

Questions about balances or exceptions go to people@helioslabs.example.
This policy supersedes the 2024 handbook section on vacation.
"""

RIVERLINE_BRIEF = """# Riverline - Q3 Project Brief

Program: Warehouse visibility
Owner: Ananya Rao, Operations
Engineering lead: Kabir Menon
Budget: $186,000
Pilot date: 8 September 2026
Pilot site: Hyderabad warehouse

## Problem

Exception handling on inbound pallets currently takes 41 minutes on average.
Supervisors stitch scanner events, carrier ETAs, and a handwritten bay map.
The lag hides aging freight and creates evening overtime.

## Outcome

Riverline is an internal logistics visibility dashboard. The goal is to cut
exception-handling time from 41 minutes to under 12 minutes for the Hyderabad
warehouse during the four-week pilot that starts 8 September 2026.

## Scope

In scope: live inbound board, exception queue, bay heatmap, and a nightly
CSV export for Finance. Out of scope: carrier rate shopping, driver apps,
and any customer-facing tracking page.

## Risks

The primary risk is scanner firmware lag on the 2019 belt units. Kabir Menon's
team will ship a buffer that accepts late scans for up to nine minutes before
flagging a miss. A secondary risk is weekend staffing for the pilot desk.

## Governance

Ananya Rao is the single project owner and approves scope changes over one
engineering day. Weekly status is due each Thursday to the Ops leadership list.
A go / no-go for a Chennai rollout is scheduled for 6 October 2026.

## Success metrics

- Median exception handling time at or below 12 minutes by week four.
- Fewer than 4 unexplained missing-scan tickets per day.
- Nightly export used by Finance on at least 18 of 20 working days.
"""

SEEDS = (
    ("Aether Desk - Product Spec.md", "text/markdown", AETHER_SPEC),
    ("Helios Labs - Time Away Policy.md", "text/markdown", LEAVE_POLICY),
    ("Riverline - Q3 Project Brief.md", "text/markdown", RIVERLINE_BRIEF),
)


def seed_if_empty(db: Session) -> int:
    if db.query(Document).count() > 0:
        return 0
    created = 0
    for name, mime, body in SEEDS:
        ingest_bytes(db, name, mime, body.encode("utf-8"))
        created += 1
    return created
