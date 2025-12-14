# Belief Forge Scout: Quick Start

## 1. Setup

**Install Dependencies:**
```powershell
pip install -r scout/requirements.txt
```

**Configure API Keys:**
1.  Copy `.env.example` to `.env`:
    ```powershell
    copy scout/.env.example scout/.env
    ```
2.  Open `scout/.env` and paste your:
    -   **Reddit Credentials** (Context: Watchtower)
    -   **OpenRouter Key** (Context: Screener/Copywriter)

## 2. Running the Mission (The Engine)

To run a manual scan (Discovery -> Screening -> Drafting):

```powershell
$env:PYTHONPATH="."; python scout/main.py
```
*   *Note: On first run, it will scan r/python & r/learnprogramming (test mode).*
*   *You can change targets in `scout/main.py`.*

## 3. Running the Dashboard (The UI)

To review your briefings:

```powershell
$env:PYTHONPATH="."; streamlit run scout/app.py
```

## 4. Key Files
*   `scout/core/models.py`: Data structures.
*   `scout/core/screener.py`: The Tier 1 AI logic.
*   `scout/core/copywriter.py`: The Tier 2 AI logic.
*   `scout/main.py`: The orchestrator script.
