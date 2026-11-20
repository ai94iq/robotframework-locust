---
name: Locust Studio
description: Desktop workbench for building, running and reading Robot Framework load tests.
colors:
  graphite-window: "#151518"
  graphite-panel: "#1c1c20"
  graphite-raised: "#232328"
  graphite-line: "#2c2c32"
  graphite-ink: "#ececef"
  graphite-muted: "#8d8d96"
  signal-indigo: "#5865f2"
  signal-indigo-light: "#7c8cff"
  graphite-lilac: "#c4a1ff"
  graphite-pass: "#3ecf8e"
  graphite-fail: "#f2555a"
  paper-window: "#f7f5f0"
  paper-panel: "#fffdf9"
  paper-raised: "#efece5"
  paper-line: "#e2ddd2"
  paper-ink: "#1d1b18"
  paper-muted: "#6f6a61"
  ledger-teal: "#0b7476"
  paper-rust: "#c2551f"
  paper-pass: "#16804a"
  paper-fail: "#d23c3c"
typography:
  headline:
    fontFamily: "Inter, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.3
  title:
    fontFamily: "Inter, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Inter, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, Segoe UI, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.4
  numeric:
    fontFamily: "JetBrains Mono, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  metric:
    fontFamily: "JetBrains Mono, Consolas, monospace"
    fontSize: "20px"
    fontWeight: 500
    lineHeight: 1.2
    fontFeature: "tnum"
rounded:
  sm: "6px"
  md: "8px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.signal-indigo}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "6px 14px"
  button-primary-paper:
    backgroundColor: "{colors.ledger-teal}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "6px 14px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.graphite-ink}"
    rounded: "{rounded.sm}"
    padding: "6px 14px"
  input:
    backgroundColor: "{colors.graphite-window}"
    textColor: "{colors.graphite-ink}"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  tab-segment:
    backgroundColor: "{colors.graphite-raised}"
    textColor: "{colors.graphite-muted}"
    rounded: "{rounded.md}"
    padding: "2px"
  tab-segment-active:
    backgroundColor: "{colors.graphite-window}"
    textColor: "{colors.graphite-ink}"
    rounded: "{rounded.sm}"
    padding: "4px 12px"
  status-pill:
    backgroundColor: "{colors.graphite-raised}"
    textColor: "{colors.graphite-muted}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  card:
    backgroundColor: "{colors.graphite-panel}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
---

# Design System: Locust Studio

## Overview

**Creative North Star: "The Measured Workbench"**

Locust Studio is a desktop workbench for engineers who read numbers. Scenario on the left, the work in the middle, the console on the right. It is dense but calm: panels separate by tone, not by lines, and the only loud things on screen are the Run button, the live status and a failure count above zero.

Two themes share one structure. Graphite (dark) is the default for long runs on an engineer's desk. Paper (light) is a warm off-white for bright rooms and for screenshots that go into reports. Both use the same layout, type and component shapes; only the palette changes.

The look this replaces (hard 1px borders on every panel, a saturated blue tab block, centered numbers in the UI face) is the anti-reference.

**Key Characteristics:**
- Two themes, one structure: Graphite dark (default) and Paper light
- Inter for the chrome, JetBrains Mono with tabular figures for every measured number
- One accent per theme, used on the primary action, the selected state and focus
- Flat, tonal layering; no shadows at rest
- Numbers right-aligned; red appears only when a failure count is above zero

## Colors

Near-neutral greys (Graphite) or warm paper tones (Paper), each with a single accent and a pass/fail pair that means exactly that.

### Primary
- **Signal Indigo** (Graphite): fills the primary button (white text, 4.6:1). Its lighter partner **Signal Indigo Light** marks focus rings, the Users chart line and accent text on dark surfaces (6.1:1 on the window).
- **Ledger Teal** (Paper): fills the primary button (white text, 5.6:1), focus rings and the Users chart line in the light theme.

### Secondary
- **Graphite Lilac** / **Paper Rust**: the response-time (p95) chart line only. Never on controls.

### Neutral
- **Graphite Window / Paper Window**: the window background and input fields.
- **Graphite Panel / Paper Panel**: side panes, cards, the header bar.
- **Graphite Raised / Paper Raised**: selected list rows, task rows, the segmented tab track, the aggregated table row.
- **Graphite Line / Paper Line**: the one divider between panes and under table rows.
- **Graphite Ink / Paper Ink**: primary text.
- **Graphite Muted / Paper Muted**: labels, column headers, console text, secondary lines (at least 4.9:1 on their window).

### Status
- **Pass** (graphite-pass / paper-pass): PASS in the console, the RPS chart line, the live dot in the Running pill, the GET method chip.
- **Fail** (graphite-fail / paper-fail): a failure count above zero, failure share, the Failures/s line, the Stop state.

### Named Rules
**The One Accent Rule.** Each theme has one accent. It goes on the primary action, the active tab, focus and nothing decorative.

**The Earned Red Rule.** A zero is plain ink. Red appears only on a failure count above zero or a failure share, so red on screen always means something failed.

## Typography

**Body Font:** Inter (with Segoe UI, sans-serif), bundled with the app
**Label/Mono Font:** JetBrains Mono (with Consolas, monospace), bundled with the app

**Character:** Inter carries every word; JetBrains Mono carries every measured number, so columns line up and digits do not jump while a run updates.

### Hierarchy
- **Headline** (600, 18px, 1.3): dialog and empty-state headings.
- **Title** (500, 14px, 1.4): the suite name in the sidebar, section titles.
- **Body** (400, 13px, 1.5): labels, list rows, form text.
- **Label** (600, 11px, 1.4, sentence case): field labels, column headers, section labels such as "User classes".
- **Numeric** (400, 12px, tabular figures): stats table cells, task paths, the console.
- **Metric** (500, 20px, tabular figures): the run summary figures (requests, failures).

### Named Rules
**The Measured-Number Rule.** Every value that came from a run or a count uses the mono face with tabular figures and is right-aligned. Names and labels never use the mono face.

## Layout

A three-pane window: the suite sidebar (about 190px) on the left, the working pane in the middle, the console (about 230px) on the right. One header row runs across the top: app name, segmented tabs (Build, Run, Report, Settings), the status pill, and the Run or Stop button at the far right. The working pane uses 12px padding with 8-12px gaps; the stats table sits on top, with the three charts stacked under it at full width.

## Elevation & Depth

Flat. Depth comes from three tonal steps (window, panel, raised) and a single 1px line between panes. The only shadow is the active tab segment's lift.

### Shadow Vocabulary
- **Segment lift** (0 1px 2px rgba(0,0,0,0.25)): the active tab inside the segmented control.

### Named Rules
**The Tone-Not-Line Rule.** Separate areas with a tonal step first. A border appears only between the three panes, under table rows and around inputs.

## Shapes

Gently rounded controls (6px) and cards (8px), pill-shaped status badges. Tables and charts sit square inside their card; rows do not round.

## Components

Refined and restrained: controls look ready, not loud.

### Buttons
- **Shape:** gently rounded (6px).
- **Primary:** accent fill with white text, 6px 14px padding, weight 500. Run and Add task are primary.
- **Hover / Focus:** hover darkens the fill one step; focus draws a 2px accent ring offset by 2px.
- **Ghost:** transparent with a 1px line border; used for Open suite, Open Robot log and Open Locust report.

### Chips
- **Method chip:** GET on a pass tint with pass text, POST on an accent tint with accent text; mono, 9-10px, 4px radius.
- **Status pill:** a pill on the raised tone with muted text: Ready, Running 16 s (pass text with a live dot), Run complete.

### Cards / Containers
- **Corner Style:** 8px.
- **Background:** panel tone on the window tone.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px line.
- **Internal Padding:** 8-12px.

### Inputs / Fields
- **Style:** window tone, 1px line border, 6px radius, 6px 8px padding.
- **Focus:** a 2px accent border.

### Navigation
- **Segmented tabs:** a raised track holding Build, Run, Report and Settings. The active segment takes the window tone, ink text and the segment lift; inactive segments show muted text.

### Stats table
- Muted column headers in sentence case. Name left-aligned; every number right-aligned in mono. The Aggregated row sits on the raised tone in weight 600. A failure count above zero is red.

## Do's and Don'ts

### Do:
- **Do** right-align every number in JetBrains Mono with tabular figures.
- **Do** keep one accent per theme: Signal Indigo in Graphite, Ledger Teal in Paper.
- **Do** separate areas with tone (window, panel, raised) before reaching for a border.
- **Do** keep text at 4.5:1 or better: muted text uses the muted token, never a lighter grey.

### Don't:
- **Don't** colour a zero failure count red.
- **Don't** use decorative gradients, glassmorphism or glow.
- **Don't** put a 1px border around every panel; the old look did this.
- **Don't** add icons where a text label suffices.
- **Don't** animate metric values beyond a plain update each second.
