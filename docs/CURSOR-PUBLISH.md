# Publish from Cursor (Cloud / Pages)

Use this when you want a **shareable URL** from Cursor (similar to what you did on another pcs-check app).

## Before you publish

This repository runs **Next.js (Node.js)** and calls **Python 3** (`python3`) for PDF/Word/Excel processing. Cursor’s hosted environment must allow **both** runtimes for every feature to work.

1. Open **Cursor → Docs** and find the current **publish / deploy / Cloud / Pages** flow (names change over time).
2. Confirm whether the host can:
   - run **Node** for `next build` / `next start`, and
   - run **Python** with dependencies from `requirements.txt` (or an equivalent install step).
3. If only Node is supported, PDF → Word and verify routes may fail until you add a **remote Python service** or use **Docker / GHCR** (`docs/INTERNAL-DEPLOYMENT.md`) instead.

## Typical publish steps (high level)

1. Open this project in **Cursor**.
2. Use the **Publish** (or Cloud deploy) entry point from the UI or Command Palette — follow the checks Cursor runs before going live.
3. Choose a **team URL** when prompted.
4. **Review** what data the app accepts (uploaded PCS documents) and who can open the URL — follow your company policy.

## Draft status

Hosting terms and capabilities are defined by **Cursor’s documentation**, not this file. Treat this note as internal guidance; have a qualified person confirm compliance before production use.
