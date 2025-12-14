# Belief Forge Scout 🛡️

**The Night Watch for Reddit Community Building.**

The Scout is a standalone AI agent designed to help "Cozy Entrepreneurs" discover high-value conversations on Reddit. It emphasizes genuine connection and helpfulness over sales, using a two-tier AI architecture to screen for opportunities and draft empathetic responses.

## Features
*   **Discovery Engine:** Monitors subreddits (Watchtower) for key distress signals (Burnout, Strategy, Venting).
*   **Tier 1 Screener:** Low-cost AI (Gemini Flash) filters noise and classifies intent.
*   **Tier 2 Copywriter:** Intelligent AI (Claude Haiku) drafts responses in the "Cozy Entrepreneur" brand voice.
*   **Mission Control:** A local Streamlit dashboard to approve, edit, or discard drafts.
*   **Safe Mode:** Runs purely in Read-Only mode for discovery; credentials specifically safeguarded.

## Quick Start

### Prerequisites
*   Docker & Docker Compose
*   OpenRouter API Key
*   Reddit App Credentials (Script type)

### Usage

1.  **Configure:**
    Renames `.env.example` to `.env` (or configure via UI).

2.  **Launch:**
    ```bash
    docker-compose up --build
    ```

3.  **Scout:**
    Access the dashboard at `http://localhost:8501`.
    Go to **Settings** to enter your keys.
    Click **Run Mission Now** to start a scan.
