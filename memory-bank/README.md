# OCC IROPS Recovery Dashboard — Agent-Ready Markdown Pack

> Source document: `OCC_IROPS_Implementation_Plan(2).docx`  
> Version: 1.0 — MVP Implementation  
> Original date: 24/04/2026  
> Scope: Cascade Detection · Data Parsing · Pilot Rollout  
> Intended users: Developer · OCC Controller · Duty Manager · AIMS PIC

## 1. Purpose

This Markdown pack converts the original Word implementation plan into an Agent-ready project knowledge base.  
It is designed so a coding Agent such as Codex can understand the project context, rules, implementation priorities, acceptance criteria, and pilot rollout approach without reading the original Word file.

## 2. Recommended Import Order for Agent

Import the files in this order:

1. `00_PROJECT_CONTEXT.md`
2. `01_CASCADE_DETECTION_LOGIC.md`
3. `02_DATA_PARSING_STRATEGY.md`
4. `03_PILOT_ROLLOUT_PLAN.md`
5. `04_DEFINITION_OF_DONE.md`
6. `05_AGENT_IMPLEMENTATION_GUIDE.md`
7. `06_AGENT_PROMPT.md`
8. `07_TEST_CASES_AND_ACCEPTANCE.md`
9. `99_MASTER_AGENT_CONTEXT.md` — optional combined context for one-shot import

## 3. Core Project Principle

Do not pitch this as AI or optimization.  
Pitch it as an automated AIMS report reader:

> Read DayRepReport from AIMS → parse schedule data → detect airport-closure impact → show structured affected-flight list → export Excel for OCC/Duty Manager review.

The Duty Manager remains the final decision maker.

## 4. Non-Negotiable MVP Boundaries

- MVP scope is limited to Airport Closure scenario.
- Cascade detection is limited to flights within the loaded DayRepReport date range.
- Do not attempt overnight rotation recovery in MVP.
- Do not add optimization, auto-recovery, aircraft swapping, crew legality, or passenger reaccommodation in MVP.
- Build data parsing robustness before UI polish.
- Validate with real DayRepReport files before user pilot.

## 5. Output Expected from Agent

The Agent should be able to help produce or update:

- Parser module for AIMS DayRepReport.
- Cascade detection module.
- Streamlit dashboard.
- Excel export.
- Data quality warnings.
- Test cases for parser and cascade logic.
- Pilot execution checklist.
