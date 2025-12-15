# 🛡️ Belief Forge Scout

**Your automated Reddit reconnaissance unit.**

The Scout is an intelligent agent designed to monitor Reddit for high-value engagement opportunities. It scans target subreddits, identifies posts indicating distress or specific strategic needs, and drafts empathetic, helpful responses using advanced AI models.

---

## ✨ Features

-   **📡 Watchtower**: Continuously monitors configurable subreddits for new keywords and trends.
-   **🧠 Intelligent Screening**: Uses Tier 1 AI (Google Gemini 2.0 Flash) to filter noise and identify posts with high intent (e.g., "Distress", "Venting", "Strategy").
-   **✍️ Auto-Drafting**: Generates draft responses using Tier 2 AI (Claude 3 Haiku / Gemini), tailored to the user's emotional state.
-   **🛡️ Safety First**: **No auto-posting.** All replies are saved as "Briefings" for human review and approval.
-   **🐳 Dockerized**: Easy to deploy and run anywhere.
-   **🔒 Secure**: Sensitive credentials (API keys, tokens) are managed via environment variables.

---

## 🚀 Quick Start

### Option A: Docker (Recommended)

The easiest way to get up and running.

1.  **Clone & Configure**
    ```bash
    git clone https://github.com/lloydbh74/BeliefForgeScout.git
    cd BeliefForgeScout
    cp scout/.env.example scout/.env
    cp scout/settings.json.example scout/settings.json
    ```

2.  **Add Your Keys**
    Edit `scout/.env` and add your keys:
    ```bash
    OPENROUTER_API_KEY=your_key_here  # Required for AI
    REDDIT_CLIENT_ID=your_id_here     # Required for scanning
    REDDIT_CLIENT_SECRET=your_secret  # Required for scanning
    TELEGRAM_BOT_TOKEN=optional       # Optional: For future alerts
    TELEGRAM_CHAT_ID=optional
    ```

3.  **Run**
    ```bash
    docker-compose up -d
    ```

4.  **Access**
    Open [http://localhost:8501](http://localhost:8501) in your browser.

    > **Note:** Data is persisted in the `scout_db_data/` directory on your host machine.

### Option B: Local Python

1.  **Install Dependencies**
    ```bash
    pip install -r scout/requirements.txt
    ```
2.  **Configure** (Same as Docker step 1 & 2)
3.  **Run**
    ```bash
    streamlit run scout/app.py
    ```

---

## ⚙️ Configuration

The Scout is highly configurable via two main files in the `scout/` directory.

### 1. Secrets (`.env`)
Stores sensitive credentials. **Never commit this file.**
-   `OPENROUTER_API_KEY`: API key for OpenRouter.ai (access to Gemini, Claude, etc.).
-   `REDDIT_CLIENT_ID` & `REDDIT_CLIENT_SECRET`: From your Reddit App preferences.
-   `REDDIT_USERNAME` & `REDDIT_PASSWORD`: (Optional) Only needed if you plan to automate posting privileges in the future.

### 2. Tuning (`settings.json`)
Refine the bot's behavior without restarting.
-   `target_subreddits`: List of subreddits to scan (e.g., `["entrepreneur", "startups"]`).
-   `pathfinder_keywords`: Keywords to look for (e.g., `["burnout", "help"]`).
-   `system_prompt`: The core instruction for the AI copywriter.

---

## 🖥️ Usage

1.  **Briefings Page**: This is your inbox.
    -   Review opportunities identifying by the Scout.
    -   See the user's "Intent" (Distress, Strategy, etc.).
    -   Edit the AI-drafted reply.
    -   Click **Approve** to save it (posting logic integration pending) or **Discard** to ignore.

2.  **Settings Page**:
    -   Update keys dynamically (saved to `.env`).
    -   Run manual missions to test configurations.

---

## 🛠️ Development

-   **Branching**: `master` is the stable release. `scout-release` is the staging branch.
-   **Database**: Uses SQLite (`scout_db_data/scout.db`).
-   **Stack**: Python 3.11, Streamlit, Pandas, PRAW (Reddit), OpenAI Client (for OpenRouter).

---

## 📄 License

[MIT License](LICENSE)
