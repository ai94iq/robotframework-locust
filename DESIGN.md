<!-- SEED: established with the user before implementation; re-run /impeccable document once there's code to capture the actual tokens and components. -->

# Design System: robotframework-locust

## Overview

**Creative North Star: "The Measured Workbench"**

A desktop studio for load testing. Dense but calm: data-forward, precise, built for engineers who read numbers. Dark-first with a light theme. The UI is a workbench - scenario on the left, live metrics in the center, log on the right. No decoration; every pixel earns its place.

**Key Characteristics:**
- Dark-first, light theme available
- Monospace for metrics, sans-serif for chrome
- Restrained accent color (single hue) used sparingly on primary actions and live indicators
- Flat surfaces with tonal layering; shadows only on hover/focus
- Dense information layout with generous internal spacing

## Colors

Palette to be resolved during implementation. Roles:

### Primary
- **Accent** (#to be resolved): primary actions, live indicators, selected state.

### Neutral
- **Surface** (#to be resolved): window background.
- **Surface Raised** (#to be resolved): panels, cards.
- **Text** (#to be resolved): primary text.
- **Text Muted** (#to be resolved): secondary text.
- **Border** (#to be resolved): dividers, input borders.

## Typography

**Display Font:** [to be resolved during implementation]
**Body Font:** [to be resolved during implementation]
**Label/Mono Font:** [to be resolved during implementation]

**Character:** Workhorse faces; monospace for all numeric output.

### Hierarchy
- **Display** (bold, 24px, 1.2): window titles.
- **Headline** (semibold, 18px, 1.3): section headers.
- **Title** (medium, 14px, 1.4): panel titles.
- **Body** (regular, 13px, 1.5): labels, descriptions.
- **Label** (medium, 12px, 1.4, uppercase tracking): metric labels.

## Layout

Three-pane: left sidebar (scenario tree), center (builder/dashboard), right (live metrics + log). Tabs: Build / Run / Report. Responsive: sidebar collapses below 900px width.

## Elevation & Depth

Flat by default. Tonal layering for panels. Shadows appear only on hover/focus and modal dialogs.

## Shapes

Subtle rounding (6-8px) on panels and inputs. Sharp corners on data tables and charts. 1px borders on inputs.

## Components

Omitted; no components exist yet. Re-run `/impeccable document` after implementation.

## Do's and Don'ts

### Do:
- **Do** use monospace for all numeric metrics.
- **Do** keep the accent color rare (primary actions and live indicators only).
- **Do** prefer flat surfaces with tonal layering.

### Don't:
- **Don't** use decorative gradients or glassmorphism.
- **Don't** animate metric values beyond subtle transitions.
- **Don't** add icons where text labels suffice.
