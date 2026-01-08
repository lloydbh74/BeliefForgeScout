# Comprehensive Code Audit Report: BeliefForgeScout

**Date**: 2026-01-08  
**Auditors**: Code Reviewer, Refactoring Expert, Security Auditor  
**Status**: 🔴 **Action Required** (Major improvements recommended)

---

## 🏗️ Structural Audit (Code Reviewer)

### 1. Logic Leakage in `app.py`
The `app.py` file is currently serving as both the UI layer (Streamlit) and the backend orchestrator (scheduler management, `.env` file writing).  
> [!WARNING]
> UI files should be thin wrappers. Business logic like "writing to .env" or "managing cron jobs" should be moved to a `core/system.py` or similar service layer.

### 2. Sync/Async Fragmentation
`notifier.py` utilizes `asyncio` to send Telegram messages, but it's called within a synchronous loop in `main.py`.  
*   **Issue**: Creating a new event loop on every notification is inefficient and prone to runtime errors in complex environments.
*   **Recommendation**: Move the entire `ScoutEngine` to an `async` architecture to natively support modern API clients (PRAW, OpenAI, Telegram).

### 3. Dependency Management
The `RedditScout` class uses "Lazy Loading" for the PRAW client. While clever, this makes testing difficult as the dependencies are instantiated deep within the class rather than injected.

---

## 🛠️ Refactoring Audit (Refactoring Expert)

### 1. Database Patterns
In `app.py`, raw SQL is executed directly using `sqlite3.connect`.  
*   **Current State**: Lines 196-197 in `app.py` duplicate connection logic already present in `ScoutDB`.
*   **Fix**: Consolidate all data access through the `ScoutDB` class. Implement a `get_recent_engagements()` method there.

### 2. Prompt Management
System prompts are currently managed as long strings in code or stored in `settings.json`.
*   **Improvement**: Migrate prompts to separate `.md` or `.txt` files in a `scout/prompts/` directory for better versioning and "prompt engineering" visibility.

### 3. Exception Handling
Critical mission steps in `main.py` wrap large blocks in `try/except Exception`.
*   **Risk**: This masks specific errors (e.g., `ValidationError` vs. `AuthError`).
*   **Reform**: Implement custom exception types and more granular error reporting.

---

## 🔒 Security Audit (Security Auditor)

### 1. Sensitive Data Persistence
The `Settings` form in `app.py` writes plain-text secrets directly to `scout/.env`.
> [!CAUTION]
> Writing to `.env` from a web UI is extremely dangerous. If the Streamlit app is compromised, internal file access could leak all keys. 
*   **Requirement**: Use an OS-level secret manager or at the very least, ensure `.env` file permissions are strictly locked (600).

### 2. Input Validation (SQL Injection)
While `sqlite3` uses parameterized queries in most places, the `update_briefing_status` in `db.py` uses multiple arguments.  
*   **Safe**: `cursor.execute("UPDATE ... WHERE post_id = ?", (post_id,))`
*   **Audit**: Ensure all `st.text_input` data is sanitized before arriving at the DB layer.

### 3. Rate Limit Management
The cooldown logic in `app.py` is stored in `st.session_state`.
*   **Vulnerability**: A user can bypass the cooldown by simply refreshing the page or opening a new tab.
*   **Hardening**: Move the "last post timestamp" to the `ScoutDB` to enforce global rate limits.

---

## 📋 Executive Summary Table

| Category | Risk Level | Priority | Key Recommendation |
| :--- | :--- | :--- | :--- |
| **Structure** | Medium | High | Decouple UI from System Logic |
| **Refactoring** | Low | Medium | Standardize Data Access Patterns |
| **Security** | **High** | **Immediate** | Secure Secret Persistence |

---

> [!TIP]
> **Next Recommended Task**: Perform a "Hardening Sprint" to address the high-priority security and structural issues before scaling the mission frequency.
