---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Read the pinned local guidelines at `references/web-interface-guidelines.md`
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Upstream origin (provenance only; do not fetch a moving branch during a review):

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Read `references/web-interface-guidelines.md` locally. Its source commit and checksum are recorded in `../../evaluation-frameworks.lock.json`. Do not upload project files. A guideline review is not user research, WCAG certification, or an automatic competition score.

## Usage

When a user provides a file or pattern argument:
1. Read the pinned local guidelines above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files are specified, use the active UI change and current frontend source tree; ask only if the scope remains ambiguous.

## MC-002 applicability

Project requirements take precedence. Apply Japanese writing conventions; do not impose English Title Case, quotation styles, or ampersands. Do not introduce external CDNs, Next.js/SSR features, native select elements, or expose private state/tokens in URLs. The app is a local Vite SPA. Keyboard support on native buttons must not add duplicate activation handlers. Form autocomplete should match field semantics; do not mechanically disable useful autocomplete. Verify browser capabilities before applying media recommendations, especially video inside picture. Flag suspected issues for evidence-based review, not automatic failures. Record issue, location, applicable rule, observed behavior, severity and evidence; record untested items explicitly.
