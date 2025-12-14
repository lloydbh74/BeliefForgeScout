# Frontend/Dashboard System Architecture
# Twitter/X Engagement Bot - Belief Forge

**Document Version**: 1.0
**Last Updated**: 2025-11-07
**Author**: System Architecture Specialist
**Status**: Design Phase - Ready for Implementation

---

## Executive Summary

This document outlines a comprehensive frontend/dashboard system for the Belief Forge Twitter Engagement Bot. The design prioritizes **mobile-first approval workflows**, **ease of use for non-technical users**, and **rapid implementation**.

**Recommended Approach**: Hybrid Web Dashboard + Telegram Bot for mobile approvals

**Key Benefits**:
- Human-in-the-loop reply approval workflow
- Real-time notifications for generated replies
- Mobile-friendly approval (via Telegram)
- Comprehensive analytics and settings management (via web dashboard)
- Low hosting costs ($5-15/month)
- Fast implementation (2-3 weeks)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack Recommendation](#2-technology-stack-recommendation)
3. [Approval Workflow Design](#3-approval-workflow-design)
4. [Core Features Specification](#4-core-features-specification)
5. [User Interface Wireframes](#5-user-interface-wireframes)
6. [Data Model Updates](#6-data-model-updates)
7. [API Design](#7-api-design)
8. [Security & Authentication](#8-security--authentication)
9. [Implementation Phases](#9-implementation-phases)
10. [Alternative Approaches Comparison](#10-alternative-approaches-comparison)
11. [Deployment Strategy](#11-deployment-strategy)
12. [Cost Analysis](#12-cost-analysis)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                           │
├─────────────────────────┬───────────────────────────────────────┤
│   Web Dashboard         │   Telegram Bot                        │
│   (Desktop/Tablet)      │   (Mobile Notifications)              │
│                         │                                        │
│   - Analytics           │   - Instant reply approval            │
│   - Settings Management │   - Quick edits                       │
│   - Bulk Operations     │   - Status updates                    │
│   - Performance Metrics │   - Emergency controls                │
└─────────────────────────┴───────────────────────────────────────┘
                              ▲
                              │ HTTPS/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND API LAYER                            │
│                    (FastAPI + Python)                            │
│                                                                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Auth Service │  │ Reply Queue  │  │ Analytics    │         │
│   │              │  │ Manager      │  │ Service      │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Settings API │  │ Bot Control  │  │ WebSocket    │         │
│   │              │  │ Service      │  │ Handler      │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                   │
│                                                                   │
│   ┌──────────────────┐  ┌──────────────────┐                   │
│   │ PostgreSQL       │  │ Redis Cache      │                   │
│   │ (Main Database)  │  │ (Queue + Cache)  │                   │
│   │                  │  │                  │                   │
│   │ - Users          │  │ - Reply Queue    │                   │
│   │ - Pending Replies│  │ - Session Data   │                   │
│   │ - Reply History  │  │ - Real-time      │                   │
│   │ - Analytics      │  │   Events         │                   │
│   │ - Settings       │  │                  │                   │
│   └──────────────────┘  └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EXISTING BOT ENGINE                             │
│                  (Python Backend)                                │
│                                                                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Tweet Scraper│  │ LLM Reply    │  │ Twitter      │         │
│   │              │  │ Generator    │  │ Publisher    │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                   │
│   MODIFIED: Instead of auto-posting, queue replies for approval  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend Framework** | React + Vite | Fast development, rich ecosystem, mobile-responsive |
| **Backend Framework** | FastAPI | Python ecosystem compatibility, async support, auto-docs |
| **Database** | PostgreSQL | Robust, relational data, better than SQLite for multi-user |
| **Queue/Cache** | Redis | Fast, reliable, pub/sub for real-time updates |
| **Mobile Approvals** | Telegram Bot | Instant notifications, no app install, familiar UX |
| **Hosting** | Railway/Render | Easy Python deployment, affordable, auto-scaling |
| **Authentication** | JWT + HTTP-only cookies | Secure, stateless, mobile-friendly |

### 1.3 Data Flow: Reply Approval Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BOT GENERATES REPLY                                          │
│    - Scrapes tweet                                              │
│    - Scores & filters                                           │
│    - LLM generates reply                                        │
│    - Validates voice guidelines                                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. QUEUE FOR APPROVAL                                           │
│    - Insert into pending_replies table                          │
│    - Status: "pending"                                          │
│    - Priority: based on commercial score                        │
│    - Add to Redis queue                                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. NOTIFY USER                                                  │
│    ┌─────────────────┐         ┌─────────────────┐            │
│    │ Telegram Message│         │ Web Dashboard   │            │
│    │                 │   OR    │ Badge Counter   │            │
│    │ "New reply      │         │ (if user online)│            │
│    │  pending..."    │         │                 │            │
│    │                 │         │                 │            │
│    │ [Approve] [Edit]│         │ [View Queue]    │            │
│    └─────────────────┘         └─────────────────┘            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. USER DECISION                                                │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│    │   APPROVE    │  │     EDIT     │  │   REJECT     │       │
│    │              │  │              │  │              │       │
│    │ Post to X    │  │ Modify text  │  │ Discard      │       │
│    │ immediately  │  │ then approve │  │ (optional    │       │
│    │              │  │              │  │  feedback)   │       │
│    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│           │                  │                  │               │
└───────────┼──────────────────┼──────────────────┼───────────────┘
            │                  │                  │
            ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. EXECUTE ACTION                                               │
│    - Update status in database                                  │
│    - If approved: trigger Twitter posting                       │
│    - If edited: re-validate, then post                          │
│    - If rejected: log feedback for learning                     │
│    - Remove from Redis queue                                    │
│    - Log analytics event                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack Recommendation

### 2.1 Frontend Stack

```yaml
Core Framework:
  - React 18.x (with Hooks)
  - Vite (build tool - faster than Create React App)
  - TypeScript (optional but recommended for maintainability)

UI Library:
  - Tailwind CSS (rapid styling, mobile-first)
  - shadcn/ui (pre-built React components)
  - Recharts (analytics visualizations)
  - React Query (server state management)

State Management:
  - Zustand (lightweight, simple to learn)
  - React Query (for API data)

Real-time Updates:
  - Socket.io-client (WebSocket connections)
  - React Hot Toast (notifications)

Routing:
  - React Router v6

Forms:
  - React Hook Form (performance)
  - Zod (validation)
```

### 2.2 Backend Stack

```yaml
Web Framework:
  - FastAPI 0.104+ (async, auto-docs, WebSocket support)
  - Uvicorn (ASGI server)
  - Python 3.11+

Database:
  - PostgreSQL 15+ (main database)
  - Alembic (migrations)
  - SQLAlchemy 2.0 (ORM)

Caching & Queue:
  - Redis 7+ (queue + cache + pub/sub)
  - Redis Queue (RQ) or Celery (background tasks)

Authentication:
  - python-jose (JWT tokens)
  - passlib + bcrypt (password hashing)
  - python-multipart (form data)

Real-time:
  - Socket.io (WebSocket server)
  - FastAPI WebSocket support

Notifications:
  - python-telegram-bot (Telegram integration)
  - APScheduler (scheduled checks)

Existing Bot Integration:
  - Minimal changes to existing Python code
  - Add reply queue service
  - Add webhook endpoints
```

### 2.3 Development Tools

```yaml
Code Quality:
  - Black (Python formatting)
  - ESLint + Prettier (JS/React formatting)
  - Pre-commit hooks

Testing:
  - Pytest (backend)
  - Vitest (frontend)
  - Playwright (E2E)

Documentation:
  - FastAPI auto-docs (Swagger/OpenAPI)
  - Storybook (UI components - optional)

Version Control:
  - Git
  - GitHub/GitLab (with CI/CD)
```

### 2.4 Deployment Stack

```yaml
Hosting Options (Recommended):

  Option A - Railway.app (Easiest):
    - Backend: Railway (Python service)
    - Frontend: Railway (static site)
    - Database: Railway PostgreSQL
    - Redis: Railway Redis
    - Cost: ~$10-20/month
    - Pros: One-click deploy, automatic HTTPS, easy scaling
    - Cons: Slightly more expensive than alternatives

  Option B - Render.com (Good balance):
    - Backend: Render Web Service
    - Frontend: Render Static Site
    - Database: Render PostgreSQL (or Neon free tier)
    - Redis: Render Redis (or Upstash free tier)
    - Cost: ~$7-15/month
    - Pros: Good free tier, simple, reliable
    - Cons: Cold starts on free tier

  Option C - Fly.io (Most control):
    - Backend: Fly.io app
    - Frontend: Vercel (free)
    - Database: Neon Serverless Postgres (free tier)
    - Redis: Upstash Redis (free tier)
    - Cost: ~$5/month (just backend)
    - Pros: Most cost-effective, high performance
    - Cons: Slightly more complex setup

RECOMMENDED: Railway (easiest for solo founder)

Domain & SSL:
  - Custom domain (beliefforge.com/dashboard)
  - Automatic HTTPS (via Railway/Render/Vercel)

Monitoring:
  - Sentry (error tracking - free tier)
  - Uptimerobot (uptime monitoring - free)
  - Railway/Render built-in logs
```

---

## 3. Approval Workflow Design

### 3.1 Human-in-the-Loop Modes

Three operational modes to support different use cases:

```yaml
Mode 1: Full Manual Approval (Default)
  Description: Every reply requires explicit approval
  Use Case: Initial rollout, high-stakes accounts
  Process:
    1. Bot generates reply
    2. Queues for approval
    3. Notifies user via Telegram
    4. User approves/edits/rejects
    5. Bot posts if approved

  Pros:
    - Complete control
    - Quality assurance
    - Learning feedback

  Cons:
    - Requires attention every 30 min
    - Can't be fully hands-off

Mode 2: Auto-Approve Low Priority (Recommended)
  Description: Critical/high priority need approval, medium/low auto-post
  Use Case: After 2-4 weeks of successful operation
  Process:
    1. Bot generates reply
    2. Check priority level
    3. If critical/high: queue for approval
    4. If medium/low: auto-post after 5-min delay window
    5. User can review & recall in delay window

  Pros:
    - Balances automation & control
    - Focus attention on important replies
    - Still maintains quality

  Cons:
    - Requires trust in scoring system
    - Slightly higher risk

Mode 3: Batch Review (Alternative)
  Description: Queue all replies, review in batches 2-3x/day
  Use Case: Prefer scheduled review sessions
  Process:
    1. Bot generates replies throughout day
    2. Queues all for approval
    3. User reviews batch at set times (e.g., 9am, 2pm, 8pm)
    4. Bulk approve/reject
    5. Post approved replies in staggered manner

  Pros:
    - Fits into daily routine
    - More thoughtful review
    - Efficient bulk operations

  Cons:
    - Reduced real-time engagement
    - Replies may be less timely
```

**Recommendation**: Start with **Mode 1** for 2 weeks, then switch to **Mode 2** once confident.

### 3.2 Telegram Bot Approval Flow

```
┌────────────────────────────────────────────────────────┐
│ TELEGRAM MESSAGE                                        │
│                                                         │
│ 🤖 New Reply Generated                                 │
│                                                         │
│ Tweet: "Struggling with imposter syndrome as a         │
│         founder. Anyone else feel like they're          │
│         winging it every day?"                          │
│                                                         │
│ Author: @jane_founder (5.2K followers)                 │
│ Priority: 🔴 CRITICAL (Mental Block)                   │
│ Score: 78/100                                          │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ Suggested Reply:                                        │
│ "I've been embracing this too—quite liberating when    │
│  you realise perfection is a myth we create for        │
│  ourselves"                                             │
│                                                         │
│ ✅ 84 characters                                        │
│ ✅ Voice validation: 0.95                              │
│                                                         │
│ ─────────────────────────────────────────────────────  │
│                                                         │
│ [✅ Approve]  [✏️ Edit]  [❌ Reject]  [🔗 View Tweet] │
│                                                         │
│ ⏰ Generated 2 minutes ago                             │
│ 📊 3 replies pending                                   │
└────────────────────────────────────────────────────────┘
```

**Interaction Flow**:

1. **Approve Button**:
   - Posts immediately to Twitter
   - Sends confirmation: "✅ Reply posted successfully! +10 engagement score this hour"

2. **Edit Button**:
   - Opens text input: "Send edited reply text:"
   - User types correction
   - Bot validates edited version
   - If valid: posts immediately
   - If invalid: "⚠️ Voice validation failed (exclamation mark detected). Try again?"

3. **Reject Button**:
   - Prompts: "Reason for rejection? (optional)"
     - "Not relevant"
     - "Too similar to recent reply"
     - "Timing not right"
     - "Other (type reason)"
   - Logs feedback for future learning
   - Confirms: "❌ Reply discarded. Feedback saved."

4. **View Tweet Button**:
   - Opens Twitter link in-app browser
   - Allows full context review

**Telegram Commands**:

```
/start - Activate notifications
/status - Current bot status & queue length
/queue - Show all pending replies
/pause - Pause bot temporarily
/resume - Resume bot operation
/settings - Quick settings (open web dashboard)
/stats - Today's stats (replies sent, engagement)
```

### 3.3 Web Dashboard Approval Interface

**Queue Management View** (Primary interface for bulk review):

```
┌────────────────────────────────────────────────────────────────┐
│ Pending Replies (7)                          [Pause Bot] [▼]   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Filters: [🔴 Critical] [🟠 High] [🟡 Medium] [⚪ Low]         │
│          [Last Hour ▼] [All Sources ▼]                        │
│                                                                 │
│ Sort: [Priority ▼] [Time ▼] [Score ▼]                         │
│                                                                 │
│ [ ] Select All    [✅ Approve Selected] [❌ Reject Selected]  │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ [✓] 🔴 CRITICAL • 2m ago • Score: 78                     │  │
│ │                                                           │  │
│ │ Original Tweet:                                           │  │
│ │ "Struggling with imposter syndrome as a founder.         │  │
│ │  Anyone else feel like they're winging it every day?"    │  │
│ │                                                           │  │
│ │ 👤 @jane_founder • 5.2K followers • #BuildInPublic       │  │
│ │ 💗 45 likes • 💬 12 replies • 👁️ 9K views • 🕐 3h ago   │  │
│ │                                                           │  │
│ │ ─────────────────────────────────────────────────────────│  │
│ │                                                           │  │
│ │ Suggested Reply:                                          │  │
│ │ "I've been embracing this too—quite liberating when you  │  │
│ │  realise perfection is a myth we create for ourselves"   │  │
│ │                                                           │  │
│ │ ✅ 84 chars • ✅ Validation: 0.95 • 💰 $0.002           │  │
│ │                                                           │  │
│ │ Signals: imposter syndrome, self-doubt                    │  │
│ │                                                           │  │
│ │ [✅ Approve] [✏️ Edit] [❌ Reject] [🔗 View Tweet]      │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ [ ] 🟠 HIGH • 15m ago • Score: 71                        │  │
│ │                                                           │  │
│ │ Original Tweet:                                           │  │
│ │ "How do I find my brand positioning when everything      │  │
│ │  feels so generic?"                                       │  │
│ │                                                           │  │
│ │ ... (similar structure)                                   │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│ [Load More] • Showing 1-5 of 7                                 │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Edit Modal** (When clicking Edit button):

```
┌────────────────────────────────────────────────────────────┐
│ Edit Reply                                           [✕]    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ Original Tweet:                                             │
│ "Struggling with imposter syndrome as a founder..."        │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│                                                             │
│ Reply Text:                                                 │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ I've been embracing this too—quite liberating when  │   │
│ │ you realise perfection is a myth we create for      │   │
│ │ ourselves                                            │   │
│ │                                                      │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ 84 / 280 characters                                        │
│                                                             │
│ ✅ Voice validation: 0.95                                  │
│ ✅ No violations detected                                  │
│                                                             │
│ [Regenerate with AI] [Save & Approve] [Cancel]             │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 4. Core Features Specification

### 4.1 Dashboard Home (Overview)

**Purpose**: At-a-glance status of bot operations and performance

**Key Metrics**:
```
┌─────────────────────────────────────────────────────────────┐
│ Today                                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ 12 Replies   │ │ 7 Pending    │ │ 84% Approval │        │
│ │ Sent         │ │ Review       │ │ Rate         │        │
│ └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ 2.3% Avg     │ │ $1.24 API    │ │ 78/100 Avg   │        │
│ │ Engagement   │ │ Cost         │ │ Score        │        │
│ └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ Bot Status: 🟢 Running                                      │
│ Next Run: in 12 minutes                                     │
│ Active Hours: 07:00 - 24:00 GMT                            │
│                                                              │
│ [Pause Bot] [Run Now] [Settings]                           │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ Recent Activity                                              │
│                                                              │
│ ✅ 14:32 - Reply approved & posted (@jane_founder)          │
│ ⏸️  14:15 - Bot paused for manual review                    │
│ ✅ 14:02 - Reply approved & posted (@mike_startup)          │
│ ❌ 13:45 - Reply rejected (not relevant)                    │
│ 📊 13:30 - Session completed (3 replies generated)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Real-time Updates**:
- WebSocket connection shows live bot activity
- Badge counter for pending approvals
- Toast notifications for critical events

### 4.2 Reply Queue (Approval Interface)

**See Section 3.3** for detailed wireframe

**Key Features**:
- Real-time queue updates (WebSocket)
- Priority-based sorting
- Bulk approval/rejection
- In-line editing
- Quick filters (priority, source, time)
- Tweet preview with full metrics
- Approve/edit/reject actions
- Character counter & validation feedback

### 4.3 Analytics Dashboard

**Purpose**: Track bot performance, reply quality, and engagement trends

**Sections**:

**4.3.1 Performance Overview**
```
┌─────────────────────────────────────────────────────────────┐
│ Performance Analytics                [Last 7 Days ▼]        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Replies Sent Over Time                                      │
│ ┌────────────────────────────────────────────────────────┐ │
│ │     📊 Line Chart                                       │ │
│ │     X-axis: Days                                        │ │
│ │     Y-axis: Reply Count                                 │ │
│ │     Lines: Total, Critical, High, Medium, Low           │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ Engagement Rate by Priority                                 │
│ ┌────────────────────────────────────────────────────────┐ │
│ │     📊 Bar Chart                                        │ │
│ │     Critical: 3.2% avg engagement                       │ │
│ │     High:     2.1% avg engagement                       │ │
│ │     Medium:   1.4% avg engagement                       │ │
│ │     Low:      0.8% avg engagement                       │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.3.2 Voice Quality Metrics**
```
┌─────────────────────────────────────────────────────────────┐
│ Voice Quality                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Validation Pass Rate:  92% (target: 90%)  ✅               │
│ Avg Character Count:   86 chars (target: <100)  ✅         │
│ Violation Rate:        3% (target: <5%)  ✅                │
│                                                              │
│ Common Violations:                                           │
│ - Exclamation marks: 2 occurrences                          │
│ - American spelling: 1 occurrence                           │
│                                                              │
│ Top Performing Replies (Engagement):                        │
│ 1. "I've been embracing..." - 8 likes, 3 replies            │
│ 2. "As someone who naturally..." - 6 likes, 2 replies       │
│ 3. "In my experience..." - 5 likes, 1 reply                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.3.3 Commercial Performance**
```
┌─────────────────────────────────────────────────────────────┐
│ Commercial Performance                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Engagement by Signal Type:                                  │
│                                                              │
│ Mental Block:       15 replies  →  3.8% engagement  🔥      │
│ Brand Clarity:      10 replies  →  2.4% engagement          │
│ Growth Frustration:  8 replies  →  1.9% engagement          │
│ Values Alignment:    6 replies  →  1.2% engagement          │
│                                                              │
│ Target Audience Reach:                                       │
│ - Ideal followers (1K-50K): 72% of replies                  │
│ - Solo founders: 45%                                         │
│ - Early-stage startups: 38%                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.3.4 Cost Tracking**
```
┌─────────────────────────────────────────────────────────────┐
│ Cost Tracking                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ This Month: $12.45 / $50.00 budget  (25% used)             │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░                       │
│                                                              │
│ Daily Average: $0.58                                         │
│ Projected Month Total: $17.40  ✅ Under budget              │
│                                                              │
│ Cost Breakdown:                                              │
│ - LLM API (OpenRouter): $11.20                              │
│ - Twitter API: $0.00 (using scraping)                       │
│ - Hosting: $1.25                                            │
│                                                              │
│ Cost per Reply: $0.0024                                     │
│ Cost per Engagement: $0.12                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Settings Management

**4.4.1 Search & Discovery Settings**
```
┌─────────────────────────────────────────────────────────────┐
│ Search Settings                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Target Hashtags:                                             │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ #BuildInPublic          [✕]                             │ │
│ │ #Bootstrapped           [✕]                             │ │
│ │ #StartupLife            [✕]                             │ │
│ │ #SoloFounder            [✕]                             │ │
│ └────────────────────────────────────────────────────────┘ │
│ [+ Add Hashtag]                                             │
│                                                              │
│ Keywords:                                                    │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ imposter syndrome  • self-doubt • brand identity        │ │
│ │ positioning • founder struggles • belief-led            │ │
│ └────────────────────────────────────────────────────────┘ │
│ [Edit Keywords]                                             │
│                                                              │
│ Search Limits:                                               │
│ Max Results per Search: [50 ▼]                             │
│ Tweet Age Window: [2-12 hours ▼]                           │
│                                                              │
│ [Save Changes] [Reset to Defaults]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.4.2 Filtering Settings**
```
┌─────────────────────────────────────────────────────────────┐
│ Filtering & Scoring                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Base Filters:                                                │
│ Min Followers:        [500  ▼]                             │
│ Min Likes:            [10   ▼]                             │
│ Min Replies:          [3    ▼]                             │
│ Min Views:            [100  ▼]                             │
│ Account Age (days):   [90   ▼]                             │
│                                                              │
│ Scoring Threshold:    [65 / 100  ▼]                        │
│                                                              │
│ Commercial Priority:                                         │
│ [✓] Enable commercial filtering                            │
│ Minimum Priority: [Medium ▼]                                │
│                                                              │
│ Commercial Multipliers:                                      │
│ Mental Block:          [3.0x ▼]                            │
│ Brand Clarity:         [2.0x ▼]                            │
│ Growth Frustration:    [1.5x ▼]                            │
│                                                              │
│ [Save Changes] [View Advanced Settings]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.4.3 Voice & Reply Settings**
```
┌─────────────────────────────────────────────────────────────┐
│ Voice Guidelines                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Character Limit:      [100 ▼] (preferred)                  │
│ Hard Limit:           [280 ▼]                              │
│                                                              │
│ LLM Model:                                                   │
│ Primary:   [Claude Sonnet 3.5 ▼]                           │
│ Fallback:  [Claude Haiku ▼]                                │
│ Temperature: [0.7 ▼]                                        │
│                                                              │
│ Voice Profile:                                               │
│ [✓] Use British English                                     │
│ [✓] Gentle qualifiers (quite, rather, perhaps)             │
│ [✓] Avoid exclamation marks                                │
│ [✓] Max 1 emoji per reply                                  │
│                                                              │
│ Learning from Past Replies:                                  │
│ [✓] Enable learning mode                                    │
│ Examples per prompt: [5 ▼]                                  │
│ Min validation score: [0.9 ▼]                              │
│                                                              │
│ [Edit Full Voice Profile] [Test Reply Generation]          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.4.4 Schedule & Rate Limiting**
```
┌─────────────────────────────────────────────────────────────┐
│ Schedule & Rate Limits                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Active Hours (GMT):                                          │
│ Start: [07:00 ▼]    End: [24:00 ▼]                        │
│                                                              │
│ Run Interval:         [30 minutes ▼]                       │
│                                                              │
│ Rate Limits:                                                 │
│ Max Replies/Hour:     [5  ▼]                               │
│ Max Likes/Hour:       [15 ▼]                               │
│                                                              │
│ Approval Mode:                                               │
│ ( ) Full Manual - Approve every reply                       │
│ (•) Smart Auto - Critical/High need approval                │
│ ( ) Batch Review - Review 2-3x daily                        │
│                                                              │
│ Auto-Approve Delay: [5 minutes ▼]                          │
│ (Grace period to recall auto-approved replies)              │
│                                                              │
│ [Save Changes]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**4.4.5 Notifications**
```
┌─────────────────────────────────────────────────────────────┐
│ Notifications                                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Telegram Notifications:                                      │
│ [✓] New reply pending approval                              │
│ [✓] Critical priority replies only (when auto-approve on)   │
│ [✓] Bot errors & warnings                                   │
│ [ ] Daily summary                                           │
│ [ ] Weekly analytics report                                 │
│                                                              │
│ Telegram Bot: @BeliefForgeBot                               │
│ Status: ✅ Connected                                        │
│ [Reconnect] [Test Notification]                            │
│                                                              │
│ Email Notifications:                                         │
│ lloyd@beliefforge.com                                        │
│ [✓] Critical errors only                                    │
│ [ ] Daily summary                                           │
│ [ ] Weekly report                                           │
│                                                              │
│ [Save Changes]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 Bot Control Panel

**Emergency Controls & Manual Operations**

```
┌─────────────────────────────────────────────────────────────┐
│ Bot Control Panel                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Current Status: 🟢 Running                                  │
│ Last Run: 2 minutes ago                                      │
│ Next Scheduled: in 28 minutes                                │
│                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ [⏸️ Pause]   │ │ [▶️ Resume]  │ │ [🔄 Run Now] │        │
│ └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 🔴 EMERGENCY STOP                                    │   │
│ │ Immediately halt all bot operations                  │   │
│ │ [Stop Bot & Clear Queue]                             │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Manual Actions:                                              │
│ [Generate Replies Now] - Run scrape & generation            │
│ [Clear Pending Queue] - Remove all pending approvals        │
│ [Test Reply Generation] - Test with sample tweet            │
│ [Refresh Learning Corpus] - Update best examples            │
│                                                              │
│ Session Stats (Current Hour):                                │
│ - Replies sent: 2 / 5 max                                   │
│ - Likes given: 8 / 15 max                                   │
│ - API calls: 12 / 20 max per minute                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.6 Reply History & Performance

**Searchable archive of all sent replies**

```
┌─────────────────────────────────────────────────────────────┐
│ Reply History                        [Export CSV ▼]         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Search: [________________] [🔍]                             │
│                                                              │
│ Filters: [Last 7 Days ▼] [All Priorities ▼]                │
│          [Min 1 like ▼] [Sort: Recent ▼]                   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 🔴 CRITICAL • Nov 7, 14:32 • @jane_founder           │   │
│ │                                                       │   │
│ │ Reply: "I've been embracing this too—quite           │   │
│ │         liberating when you realise perfection..."   │   │
│ │                                                       │   │
│ │ Performance: 💗 8 likes • 💬 3 replies • 🔄 1 RT     │   │
│ │ Engagement: 3.2% (above avg 2.1%)                    │   │
│ │                                                       │   │
│ │ [⭐ Mark as Good Example] [🔗 View Thread] [📋]      │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ 🟠 HIGH • Nov 7, 14:02 • @mike_startup               │   │
│ │ ... (similar structure)                               │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ [Load More] • Showing 1-10 of 156                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Mark best replies as "good examples" for learning
- Export to CSV for external analysis
- Click through to view full Twitter thread
- Performance metrics update daily
- Filter by priority, engagement, date range

---

## 5. User Interface Wireframes

### 5.1 Navigation Structure

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Belief Forge Bot          lloyd@beliefforge.com    [👤] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🏠 Dashboard                                                │
│  ⏳ Reply Queue [7]  ← Badge shows pending count            │
│  📊 Analytics                                                │
│  ⚙️  Settings                                                │
│  🎛️  Bot Control                                             │
│  📜 History                                                  │
│  ❓ Help                                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Mobile Navigation** (hamburger menu):
- Collapsed sidebar
- Floating "+ New Approval" button
- Bottom nav bar for key actions

### 5.2 Color Scheme & Design System

```yaml
Brand Colors:
  Primary: #6366F1 (Indigo - action buttons)
  Success: #10B981 (Green - approvals, positive metrics)
  Warning: #F59E0B (Amber - edits, warnings)
  Error: #EF4444 (Red - rejections, critical alerts)
  Info: #3B82F6 (Blue - info, links)

Priority Colors:
  Critical: #DC2626 (Red)
  High: #EA580C (Orange)
  Medium: #EAB308 (Yellow)
  Low: #9CA3AF (Gray)

Background:
  Page: #F9FAFB (Light gray)
  Card: #FFFFFF (White)
  Border: #E5E7EB (Light gray)

Text:
  Primary: #111827 (Near black)
  Secondary: #6B7280 (Medium gray)
  Muted: #9CA3AF (Light gray)

Shadows:
  Card: 0 1px 3px rgba(0,0,0,0.1)
  Hover: 0 4px 6px rgba(0,0,0,0.1)

Fonts:
  Heading: Inter (sans-serif)
  Body: Inter (sans-serif)
  Mono: JetBrains Mono (for tweet text)
```

### 5.3 Responsive Design

```yaml
Breakpoints:
  Mobile: < 640px
  Tablet: 640px - 1024px
  Desktop: > 1024px

Mobile Optimizations:
  - Single column layout
  - Collapsible cards
  - Bottom navigation bar
  - Swipe gestures for approve/reject
  - Simplified metrics (3 key stats vs 6)
  - Telegram bot primary for approvals

Tablet Optimizations:
  - Two column layout
  - Sidebar navigation
  - Full feature access
  - Touch-optimized buttons

Desktop:
  - Multi-column layouts
  - Expanded metrics
  - Keyboard shortcuts
  - Batch operations
```

### 5.4 Accessibility

```yaml
WCAG AA Compliance:
  - Color contrast ratios: 4.5:1 minimum
  - Keyboard navigation support
  - ARIA labels on all interactive elements
  - Screen reader friendly
  - Focus indicators on all buttons
  - Skip navigation links
  - Alt text on all icons

Keyboard Shortcuts:
  - Ctrl+K: Quick search
  - Ctrl+A: Approve first pending reply
  - Ctrl+E: Edit first pending reply
  - Ctrl+R: Reject first pending reply
  - Ctrl+P: Pause/resume bot
  - Esc: Close modals
```

---

## 6. Data Model Updates

### 6.1 New Database Schema

**PostgreSQL Database: `belief_forge_bot`**

#### Table: `users`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    telegram_chat_id BIGINT UNIQUE,
    telegram_username VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_telegram ON users(telegram_chat_id);
```

#### Table: `pending_replies` (NEW - Core of approval system)
```sql
CREATE TABLE pending_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tweet info
    tweet_id VARCHAR(50) UNIQUE NOT NULL,
    tweet_text TEXT NOT NULL,
    tweet_author_username VARCHAR(255) NOT NULL,
    tweet_author_display_name VARCHAR(255),
    tweet_author_followers INT,
    tweet_url TEXT NOT NULL,
    tweet_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    tweet_metrics JSONB, -- likes, replies, retweets, views

    -- Generated reply
    suggested_reply_text TEXT NOT NULL,
    character_count INT NOT NULL,

    -- Scoring & priority
    tweet_score DECIMAL(5,2) NOT NULL,
    commercial_priority VARCHAR(20) NOT NULL, -- critical, high, medium, low
    priority_score DECIMAL(5,2),
    detected_signals JSONB, -- array of matched keywords

    -- Validation
    validation_score DECIMAL(3,2),
    had_violations BOOLEAN DEFAULT false,
    violation_details JSONB,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, edited, auto_approved, expired
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Edit history
    edited_text TEXT, -- if user edited before approving
    edit_count INT DEFAULT 0,

    -- LLM metadata
    llm_model VARCHAR(100),
    llm_temperature DECIMAL(2,1),
    generation_attempt INT DEFAULT 1,
    token_usage INT,
    cost_usd DECIMAL(10,6),

    -- Learning context
    learning_examples_used JSONB, -- IDs of past replies used for learning

    -- Timestamps
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- auto-expire old pending replies

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pending_status ON pending_replies(status);
CREATE INDEX idx_pending_priority ON pending_replies(commercial_priority, tweet_score DESC);
CREATE INDEX idx_pending_generated_at ON pending_replies(generated_at DESC);
CREATE INDEX idx_pending_expires_at ON pending_replies(expires_at);
```

#### Table: `sent_replies` (Enhanced version of existing reply log)
```sql
CREATE TABLE sent_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    pending_reply_id UUID REFERENCES pending_replies(id),
    tweet_id VARCHAR(50) NOT NULL,
    reply_id VARCHAR(50) UNIQUE, -- Twitter reply ID

    -- Content
    original_tweet_text TEXT NOT NULL,
    reply_text TEXT NOT NULL,
    was_edited BOOLEAN DEFAULT false,
    character_count INT NOT NULL,

    -- Original scoring
    tweet_score DECIMAL(5,2),
    commercial_priority VARCHAR(20),
    priority_score DECIMAL(5,2),
    detected_signals JSONB,

    -- Validation
    validation_score DECIMAL(3,2),
    had_violations BOOLEAN DEFAULT false,

    -- Performance tracking (updated via scheduled job)
    like_count INT DEFAULT 0,
    reply_count INT DEFAULT 0,
    retweet_count INT DEFAULT 0,
    quote_count INT DEFAULT 0,
    engagement_rate DECIMAL(5,2), -- calculated
    last_performance_check TIMESTAMP WITH TIME ZONE,

    -- Quality markers
    marked_as_good_example BOOLEAN DEFAULT false,
    marked_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    llm_model VARCHAR(100),
    token_usage INT,
    cost_usd DECIMAL(10,6),
    session_id VARCHAR(100),

    -- Timestamps
    posted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sent_tweet_id ON sent_replies(tweet_id);
CREATE INDEX idx_sent_posted_at ON sent_replies(posted_at DESC);
CREATE INDEX idx_sent_priority ON sent_replies(commercial_priority);
CREATE INDEX idx_sent_good_examples ON sent_replies(marked_as_good_example, engagement_rate DESC);
```

#### Table: `bot_sessions`
```sql
CREATE TABLE bot_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) UNIQUE NOT NULL,

    -- Session info
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed, interrupted

    -- Metrics
    tweets_scraped INT DEFAULT 0,
    tweets_scored INT DEFAULT 0,
    replies_generated INT DEFAULT 0,
    replies_approved INT DEFAULT 0,
    replies_rejected INT DEFAULT 0,
    replies_auto_approved INT DEFAULT 0,

    errors JSONB, -- array of error messages

    -- Performance
    avg_tweet_score DECIMAL(5,2),
    total_cost_usd DECIMAL(10,6),
    total_tokens INT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sessions_started_at ON bot_sessions(started_at DESC);
CREATE INDEX idx_sessions_status ON bot_sessions(status);
```

#### Table: `bot_settings` (Configuration stored in DB)
```sql
CREATE TABLE bot_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(100), -- search, filtering, voice, schedule, etc.
    description TEXT,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_settings_category ON bot_settings(category);
```

#### Table: `bot_events` (Audit log)
```sql
CREATE TABLE bot_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL, -- bot_started, bot_paused, reply_approved, settings_changed, etc.
    event_data JSONB,
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'info', -- info, warning, error, critical
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_events_type ON bot_events(event_type);
CREATE INDEX idx_events_created_at ON bot_events(created_at DESC);
CREATE INDEX idx_events_severity ON bot_events(severity);
```

#### Table: `notification_queue`
```sql
CREATE TABLE notification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    notification_type VARCHAR(50) NOT NULL, -- telegram, email, webhook
    priority VARCHAR(20) DEFAULT 'normal', -- urgent, high, normal, low
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB, -- additional notification data
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_status ON notification_queue(status, priority DESC);
CREATE INDEX idx_notifications_user ON notification_queue(user_id, created_at DESC);
```

### 6.2 Migration from SQLite

**Strategy**: Maintain both databases during transition

```python
# Migration script: migrate_sqlite_to_postgres.py

import sqlite3
import psycopg2
from datetime import datetime

def migrate_deduplication_db():
    """Migrate existing SQLite deduplication.db to PostgreSQL"""

    sqlite_conn = sqlite3.connect('data/deduplication.db')
    pg_conn = psycopg2.connect("postgresql://user:pass@localhost/belief_forge_bot")

    # Migrate replied tweets -> sent_replies
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM replied_tweets")

    for row in cursor.fetchall():
        # Map SQLite columns to PostgreSQL table
        # Insert into sent_replies
        pass

    sqlite_conn.close()
    pg_conn.close()

def migrate_analytics_db():
    """Migrate existing SQLite analytics.db to PostgreSQL"""
    # Similar approach
    pass
```

**Backward Compatibility**:
- Keep existing SQLite for 30 days
- Bot writes to both databases during transition
- Validate data consistency
- Switch entirely to PostgreSQL after validation

---

## 7. API Design

### 7.1 API Architecture

**Base URL**: `https://api.beliefforge.com` (or subdomain)

**Authentication**: JWT tokens via HTTP-only cookies

**API Versioning**: `/api/v1/...`

### 7.2 Core API Endpoints

#### Authentication

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
POST   /api/v1/auth/telegram/connect
```

#### Reply Queue Management

```
GET    /api/v1/replies/pending
       Query params: priority, limit, offset, sort
       Returns: Paginated list of pending replies

GET    /api/v1/replies/pending/:id
       Returns: Single pending reply with full details

POST   /api/v1/replies/:id/approve
       Body: { auto_post: boolean }
       Returns: Updated reply status

POST   /api/v1/replies/:id/edit
       Body: { edited_text: string }
       Returns: Validation result, updated reply

POST   /api/v1/replies/:id/reject
       Body: { reason: string }
       Returns: Updated status

POST   /api/v1/replies/bulk-approve
       Body: { reply_ids: string[] }
       Returns: Bulk operation result

DELETE /api/v1/replies/:id
       Permanently delete pending reply
```

#### Reply History

```
GET    /api/v1/replies/sent
       Query params: start_date, end_date, priority, min_engagement
       Returns: Paginated sent replies with performance

GET    /api/v1/replies/sent/:id
       Returns: Single reply with full thread context

POST   /api/v1/replies/sent/:id/mark-example
       Mark reply as good example for learning
       Body: { is_good_example: boolean }

GET    /api/v1/replies/sent/:id/performance
       Returns: Latest performance metrics
```

#### Analytics

```
GET    /api/v1/analytics/overview
       Query params: start_date, end_date
       Returns: Summary metrics

GET    /api/v1/analytics/performance
       Returns: Reply performance over time

GET    /api/v1/analytics/voice-quality
       Returns: Voice validation metrics

GET    /api/v1/analytics/commercial
       Returns: Commercial performance breakdown

GET    /api/v1/analytics/costs
       Returns: Cost tracking & projections
```

#### Settings

```
GET    /api/v1/settings
       Returns: All bot settings grouped by category

GET    /api/v1/settings/:category
       Returns: Settings for specific category

PUT    /api/v1/settings/:category
       Body: { settings object }
       Returns: Updated settings

POST   /api/v1/settings/reset
       Body: { category?: string }
       Reset to defaults
```

#### Bot Control

```
GET    /api/v1/bot/status
       Returns: Current bot status, next run, metrics

POST   /api/v1/bot/pause
       Pause bot operations

POST   /api/v1/bot/resume
       Resume bot operations

POST   /api/v1/bot/run-now
       Trigger immediate bot run

POST   /api/v1/bot/stop
       Emergency stop (clear queue)

GET    /api/v1/bot/sessions
       Returns: Recent bot sessions

GET    /api/v1/bot/sessions/:id
       Returns: Detailed session info
```

#### Events & Logs

```
GET    /api/v1/events
       Query params: event_type, severity, start_date, limit
       Returns: Bot events/audit log

GET    /api/v1/events/:id
       Returns: Single event details
```

### 7.3 WebSocket Events

**Connection**: `wss://api.beliefforge.com/ws`

**Events Emitted by Server**:

```javascript
// New reply pending approval
{
  event: 'reply.pending',
  data: {
    id: 'uuid',
    priority: 'critical',
    tweet_author: '@jane_founder',
    suggested_reply: '...',
    // ... full reply object
  }
}

// Reply approved/rejected
{
  event: 'reply.status_changed',
  data: {
    id: 'uuid',
    old_status: 'pending',
    new_status: 'approved',
    reviewed_by: 'user_id'
  }
}

// Bot status change
{
  event: 'bot.status_changed',
  data: {
    old_status: 'running',
    new_status: 'paused',
    reason: 'manual'
  }
}

// Performance update
{
  event: 'reply.performance_updated',
  data: {
    reply_id: 'uuid',
    like_count: 5,
    engagement_rate: 2.3
  }
}

// Error/warning
{
  event: 'bot.error',
  data: {
    severity: 'warning',
    message: 'Rate limit approaching',
    details: {...}
  }
}
```

**Events Sent by Client**:

```javascript
// Subscribe to specific reply updates
{
  event: 'subscribe',
  data: { channel: 'replies' }
}

// Ping/pong for connection health
{
  event: 'ping'
}
```

### 7.4 API Example Requests

**Approve a Reply** (Python):

```python
import httpx

async def approve_reply(reply_id: str, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.beliefforge.com/api/v1/replies/{reply_id}/approve",
            json={"auto_post": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

**Fetch Pending Replies** (React):

```typescript
import { useQuery } from '@tanstack/react-query';

function usePendingReplies(priority?: string) {
  return useQuery({
    queryKey: ['replies', 'pending', priority],
    queryFn: async () => {
      const params = priority ? `?priority=${priority}` : '';
      const response = await fetch(`/api/v1/replies/pending${params}`, {
        credentials: 'include' // Include auth cookie
      });
      return response.json();
    },
    refetchInterval: 30000 // Poll every 30 seconds
  });
}
```

---

## 8. Security & Authentication

### 8.1 Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER LOGIN                                                │
│    POST /api/v1/auth/login                                   │
│    Body: { email, password }                                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SERVER VALIDATES                                          │
│    - Check email exists                                      │
│    - Verify password hash (bcrypt)                           │
│    - Generate JWT access token (15 min expiry)              │
│    - Generate JWT refresh token (7 day expiry)              │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SET COOKIES                                               │
│    Set-Cookie: access_token=xxx; HttpOnly; Secure; SameSite │
│    Set-Cookie: refresh_token=yyy; HttpOnly; Secure; SameSite│
│    Response: { user: {...}, success: true }                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SUBSEQUENT REQUESTS                                       │
│    - Browser automatically sends cookies                     │
│    - Server validates access token                           │
│    - If expired: use refresh token to get new access token  │
│    - If refresh expired: redirect to login                   │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Security Measures

```yaml
Password Security:
  - Bcrypt hashing with salt rounds: 12
  - Minimum length: 12 characters
  - Require: uppercase, lowercase, number, symbol
  - Password reset via secure token (1-hour expiry)

JWT Tokens:
  - Access token: 15 minutes expiry
  - Refresh token: 7 days expiry
  - Signed with HS256 algorithm
  - Store in HTTP-only cookies (not localStorage)
  - SameSite=Strict to prevent CSRF

API Security:
  - Rate limiting: 100 requests/minute per IP
  - CORS: Whitelist dashboard domain only
  - HTTPS only (enforce SSL)
  - API key rotation for external services
  - Input validation on all endpoints
  - SQL injection prevention (parameterized queries)

Secrets Management:
  - Store in environment variables
  - Never commit to git (.env in .gitignore)
  - Use separate secrets for dev/staging/prod
  - Rotate credentials quarterly
  - OpenRouter API key: prefix sk-or-
  - Twitter cookies: encrypted at rest

Telegram Bot Security:
  - Webhook secret token validation
  - User ID verification
  - Rate limiting on bot commands
  - No sensitive data in messages
  - Commands require authentication link

Database Security:
  - PostgreSQL with SSL
  - Principle of least privilege (app user has limited perms)
  - Regular backups (daily)
  - Encrypted backups
  - No direct database access from public internet
```

### 8.3 Telegram Bot Authentication

```python
# Telegram authentication flow

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - initiate authentication"""

    chat_id = update.effective_chat.id
    telegram_username = update.effective_user.username

    # Generate one-time authentication token
    auth_token = generate_auth_token(chat_id)

    # Send authentication link
    auth_url = f"https://dashboard.beliefforge.com/auth/telegram?token={auth_token}"

    await update.message.reply_text(
        f"👋 Welcome to Belief Forge Bot!\n\n"
        f"To receive reply approvals, please link your account:\n"
        f"{auth_url}\n\n"
        f"This link expires in 5 minutes."
    )

async def approve_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button approval"""

    query = update.callback_query
    await query.answer()

    # Extract reply ID from callback data
    reply_id = query.data.split(':')[1]

    # Verify user is authenticated
    user = get_user_by_telegram_chat_id(query.from_user.id)
    if not user:
        await query.edit_message_text("⚠️ Please authenticate first: /start")
        return

    # Approve reply via API
    result = await api_approve_reply(reply_id, user.id)

    if result['success']:
        await query.edit_message_text(
            f"✅ Reply approved and posted!\n\n"
            f"View on Twitter: {result['tweet_url']}"
        )
    else:
        await query.edit_message_text(
            f"❌ Error: {result['error']}"
        )
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1)

**Backend Setup**
- [ ] Initialize FastAPI project structure
- [ ] Set up PostgreSQL database (Railway/Render)
- [ ] Set up Redis (Railway/Render or Upstash)
- [ ] Create database schema & migrations (Alembic)
- [ ] Implement authentication system (JWT + cookies)
- [ ] Build core API endpoints (auth, settings)
- [ ] Set up error handling & logging

**Frontend Setup**
- [ ] Initialize React + Vite project
- [ ] Set up Tailwind CSS + shadcn/ui
- [ ] Create basic layout & navigation
- [ ] Implement authentication flow (login page)
- [ ] Set up React Query for API calls
- [ ] Configure routing (React Router)

**Deliverables**:
- Working login system
- Empty dashboard shell
- Database ready for data
- Basic API docs (FastAPI auto-docs)

### Phase 2: Reply Queue System (Week 2)

**Backend**
- [ ] Create `pending_replies` table & models
- [ ] Build reply queue API endpoints
- [ ] Implement WebSocket server for real-time updates
- [ ] Create background job for reply expiration
- [ ] Add approval/edit/reject logic
- [ ] Integrate with existing bot (modify to queue instead of auto-post)

**Frontend**
- [ ] Build reply queue UI (list view)
- [ ] Implement approve/edit/reject actions
- [ ] Add real-time WebSocket updates
- [ ] Create edit modal with validation
- [ ] Add filtering & sorting
- [ ] Build bulk selection UI

**Bot Integration**
- [ ] Modify existing bot to queue replies
- [ ] Add API calls to create pending replies
- [ ] Add API calls to post approved replies
- [ ] Test end-to-end flow

**Deliverables**:
- Functional reply approval workflow
- Real-time queue updates
- Bot queuing replies (not auto-posting)

### Phase 3: Telegram Bot Integration (Week 3)

**Telegram Bot**
- [ ] Set up python-telegram-bot
- [ ] Implement authentication flow
- [ ] Build reply notification messages
- [ ] Add inline approve/edit/reject buttons
- [ ] Implement bot commands (/status, /queue, etc.)
- [ ] Add webhook integration (if not polling)

**Backend**
- [ ] Create notification queue system
- [ ] Build Telegram notification service
- [ ] Add user-telegram linking endpoints
- [ ] Implement notification preferences

**Testing**
- [ ] Test Telegram approval flow end-to-end
- [ ] Test authentication linking
- [ ] Test notification delivery
- [ ] Test concurrent web + Telegram approvals

**Deliverables**:
- Working Telegram bot for approvals
- Mobile-friendly approval workflow
- Notification system

### Phase 4: Analytics & Monitoring (Week 4)

**Backend**
- [ ] Create analytics aggregation queries
- [ ] Build analytics API endpoints
- [ ] Implement performance tracking job (daily)
- [ ] Create cost tracking calculations
- [ ] Build bot session tracking

**Frontend**
- [ ] Build dashboard home (overview metrics)
- [ ] Create analytics views (charts with Recharts)
- [ ] Build performance over time charts
- [ ] Create voice quality metrics view
- [ ] Build cost tracking dashboard

**Deliverables**:
- Complete analytics dashboard
- Performance tracking
- Cost monitoring

### Phase 5: Settings & Bot Control (Week 5)

**Backend**
- [ ] Create bot settings API
- [ ] Build bot control endpoints (pause/resume/run)
- [ ] Implement settings validation
- [ ] Add settings change audit logging

**Frontend**
- [ ] Build settings management UI (all categories)
- [ ] Create bot control panel
- [ ] Add settings validation & error handling
- [ ] Build emergency stop UI
- [ ] Add settings export/import

**Bot Integration**
- [ ] Make bot read settings from database (not just YAML)
- [ ] Add real-time settings reload
- [ ] Implement pause/resume controls
- [ ] Add manual trigger support

**Deliverables**:
- Complete settings management
- Bot control panel
- Database-driven configuration

### Phase 6: Reply History & Polish (Week 6)

**Backend**
- [ ] Create reply history API endpoints
- [ ] Build good example marking system
- [ ] Add CSV export functionality
- [ ] Implement search & filtering

**Frontend**
- [ ] Build reply history UI
- [ ] Add search & advanced filtering
- [ ] Create performance detail views
- [ ] Build good example management
- [ ] Add CSV export UI
- [ ] Polish all UI components
- [ ] Add loading states & error boundaries
- [ ] Implement keyboard shortcuts

**Documentation**
- [ ] Write user guide
- [ ] Create video tutorials (optional)
- [ ] Document API
- [ ] Write deployment guide

**Deliverables**:
- Complete reply history
- Polished UI/UX
- Full documentation

### Phase 7: Testing & Deployment (Week 7)

**Testing**
- [ ] Write backend unit tests (pytest)
- [ ] Write frontend unit tests (Vitest)
- [ ] End-to-end testing (Playwright)
- [ ] Security audit
- [ ] Performance testing
- [ ] Mobile testing

**Deployment**
- [ ] Set up production environment (Railway/Render)
- [ ] Configure production database
- [ ] Set up production Redis
- [ ] Configure domain & SSL
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Set up monitoring (Sentry, Uptimerobot)
- [ ] Configure backups

**Migration**
- [ ] Migrate SQLite data to PostgreSQL
- [ ] Validate data integrity
- [ ] Run parallel for 7 days
- [ ] Switch fully to new system

**Deliverables**:
- Production deployment
- Data migration complete
- Monitoring active
- System live

### Phase 8: Optimization & Iteration (Ongoing)

**Week 8+**
- [ ] Monitor user feedback
- [ ] Optimize slow queries
- [ ] Improve UI based on usage patterns
- [ ] Add requested features
- [ ] Refine scoring weights based on analytics
- [ ] Improve voice validation
- [ ] A/B test prompt variations

---

## 10. Alternative Approaches Comparison

### 10.1 Option A: Web Dashboard Only (No Telegram)

**Architecture**: Single-page React app + FastAPI backend

**Pros**:
- Simpler architecture (one less integration)
- Unified interface
- Easier to maintain
- Lower complexity

**Cons**:
- Not mobile-friendly for approvals
- Requires opening laptop for every approval
- Less real-time/immediate
- Doesn't fit Lloyd's on-the-go lifestyle

**Verdict**: ❌ Not recommended for solo founder

---

### 10.2 Option B: Telegram Bot Only (No Web Dashboard)

**Architecture**: Pure Telegram bot interface for all operations

**Pros**:
- Extremely mobile-friendly
- Instant notifications
- Familiar interface
- Very fast to build
- Lowest hosting costs

**Cons**:
- Limited UI capabilities (no rich charts)
- Poor for bulk operations
- Hard to view detailed analytics
- Difficult to manage complex settings
- Not suitable for desktop work

**Example Commands**:
```
/approve - Show next pending reply
/queue - List all pending (text-only)
/stats - Basic text stats
/settings - Text-based settings (limited)
/history - Text list of recent replies
```

**Verdict**: ⚠️ Good for MVP, but limiting long-term

---

### 10.3 Option C: Hybrid (Web Dashboard + Telegram) - RECOMMENDED

**Architecture**: Full web dashboard + Telegram bot for mobile approvals

**Pros**:
- Best of both worlds
- Mobile approvals via Telegram
- Detailed analytics via web
- Flexible settings management
- Scales with future needs
- Professional appearance

**Cons**:
- More complex to build
- Two UIs to maintain
- Slightly higher costs

**Verdict**: ✅ **RECOMMENDED** - Best balance for growing business

---

### 10.4 Option D: Desktop Application (Electron)

**Architecture**: Electron app (cross-platform desktop)

**Pros**:
- Native desktop experience
- Offline capabilities
- Full control over UI
- No hosting costs (besides API)

**Cons**:
- Still not mobile-friendly
- More complex deployment (installers)
- Updates require user action
- Electron bundle size large
- Doesn't solve mobile approval problem

**Verdict**: ❌ Over-engineered for this use case

---

### 10.5 Option E: No-Code Tools (Zapier, Make, Airtable)

**Architecture**: Airtable for database + Make/Zapier for approval workflow

**Pros**:
- Fastest to build (days vs weeks)
- No coding required
- Visual workflow builder
- Airtable has mobile app

**Cons**:
- Limited customization
- Expensive at scale (Airtable + Make/Zapier)
- Vendor lock-in
- Poor analytics capabilities
- Can't integrate deeply with existing Python bot
- Recurring costs increase over time

**Example Flow**:
1. Bot writes pending replies to Airtable
2. Airtable view triggers Make.com workflow
3. Make.com sends Telegram message
4. Airtable form for approval/rejection
5. Make.com watches Airtable, posts to Twitter

**Verdict**: ⚠️ Good for quick MVP, but doesn't scale

---

### 10.6 Option F: Minimal Web Dashboard (Streamlit/Gradio)

**Architecture**: Python-based simple dashboards (Streamlit/Gradio)

**Pros**:
- Very fast to build (hours)
- Pure Python (no JS needed)
- Good for prototyping
- Built-in widgets for metrics

**Cons**:
- Limited UI customization
- Poor mobile experience
- No real-time updates (requires page refresh)
- Not production-ready for public-facing app
- Doesn't look professional

**Verdict**: ⚠️ Good for internal testing, not production

---

## 11. Deployment Strategy

### 11.1 Recommended Deployment: Railway.app

**Why Railway**:
- Simplest deployment for Python + PostgreSQL + Redis
- Automatic HTTPS & domain management
- GitHub integration (auto-deploy on push)
- Built-in monitoring
- Fair pricing ($5 free credit/month, ~$10-20/month typical)

**Deployment Steps**:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Add PostgreSQL
railway add --database postgresql

# 5. Add Redis
railway add --database redis

# 6. Deploy backend
cd backend
railway up

# 7. Deploy frontend (static site)
cd frontend
npm run build
railway up --service frontend

# 8. Configure environment variables
railway variables set OPENROUTER_API_KEY=sk-or-...
railway variables set TELEGRAM_BOT_TOKEN=...
railway variables set DATABASE_URL=... (auto-set)
railway variables set REDIS_URL=... (auto-set)

# 9. Configure domain
railway domain
```

**Project Structure on Railway**:
```
belief-forge-bot/
├── Backend Service (FastAPI)
│   └── Port: 8000
│   └── Health check: /api/v1/health
├── Frontend Service (Static)
│   └── Served via Nginx
│   └── Custom domain: dashboard.beliefforge.com
├── PostgreSQL Database
│   └── Auto-provisioned
│   └── Automatic backups
└── Redis Database
    └── Auto-provisioned
    └── Used for queue + cache
```

### 11.2 Alternative: Render.com

**Deploy via Dashboard**:
1. Connect GitHub repo
2. Create Web Service (backend)
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Create Static Site (frontend)
   - Build: `npm run build`
   - Publish: `dist`
4. Add PostgreSQL database (free tier available)
5. Add Redis database (free tier via Upstash)

**Cost**: $0-7/month (free tier backend + paid database)

### 11.3 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest

      - name: Deploy to Railway
        run: |
          npm install -g @railway/cli
          railway login --token ${{ secrets.RAILWAY_TOKEN }}
          railway up --service backend

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build frontend
        run: |
          cd frontend
          npm install
          npm run build

      - name: Deploy to Railway
        run: |
          railway up --service frontend
```

### 11.4 Environment Variables

**Backend (.env)**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/belief_forge_bot
REDIS_URL=redis://default:pass@host:6379

# API Keys
OPENROUTER_API_KEY=sk-or-v1-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=https://dashboard.beliefforge.com,http://localhost:5173

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Twitter (existing bot)
TWITTER_COOKIES_FILE=./cookies.json
```

**Frontend (.env.production)**:
```bash
VITE_API_URL=https://api.beliefforge.com
VITE_WS_URL=wss://api.beliefforge.com/ws
VITE_ENVIRONMENT=production
```

### 11.5 Monitoring & Alerts

```yaml
Monitoring Stack:

Application Monitoring:
  - Sentry (error tracking)
    - Free tier: 5K errors/month
    - Set up: sentry.init() in FastAPI & React

Uptime Monitoring:
  - Uptimerobot (free tier: 50 monitors)
    - Monitor: https://api.beliefforge.com/health
    - Alert via email/Telegram if down

Logs:
  - Railway built-in logs
  - Structured JSON logging
  - Log retention: 7 days (Railway free)

Performance:
  - Railway metrics (CPU, memory, response time)
  - Database query monitoring (pg_stat_statements)

Alerts:
  Telegram Alerts for:
    - Bot errors (via existing notification system)
    - API downtime (via Uptimerobot)
    - High cost alerts (>80% monthly budget)
    - Database backup failures
    - Reply approval queue backlog (>20 pending)
```

---

## 12. Cost Analysis

### 12.1 Monthly Cost Breakdown

**Hosting (Railway - Recommended)**:
```
Backend Service (FastAPI):       $5-10/month
PostgreSQL Database:              $5/month (1GB)
Redis:                            $5/month (250MB)
Bandwidth:                        $0-2/month
─────────────────────────────────────────────
Total Hosting:                    $15-20/month
```

**Alternative (Render + Free Tiers)**:
```
Backend Service:                  $7/month (starter)
PostgreSQL (Neon free tier):      $0
Redis (Upstash free tier):        $0
─────────────────────────────────────────────
Total Hosting:                    $7/month
```

**API Costs**:
```
OpenRouter (Claude Sonnet 3.5):   $15-30/month (existing)
Telegram Bot API:                 $0 (free)
Twitter API:                      $0 (using scraping)
─────────────────────────────────────────────
Total API:                        $15-30/month
```

**Domain & SSL**:
```
Domain (if new subdomain):        $0 (already own beliefforge.com)
SSL Certificate:                  $0 (auto via Railway/Render)
```

**Monitoring**:
```
Sentry (free tier):               $0
Uptimerobot (free tier):          $0
```

**TOTAL MONTHLY COST**:
- **Option A (Railway)**: $30-50/month
- **Option B (Render + free tiers)**: $22-37/month

**One-Time Costs**:
- Development time: 6-7 weeks (if solo, ~80 hours)
- Freelance developer: $3,000-5,000 (if outsourcing)

### 12.2 Cost Optimization Strategies

1. **Start with Render free tiers** (Neon + Upstash)
   - Move to paid hosting when scaling

2. **Use Fly.io for backend** ($5/month)
   - More cost-effective for single service

3. **Optimize LLM usage**:
   - Use Haiku for lower-priority replies
   - Cache common responses
   - Batch API calls

4. **Database optimization**:
   - Archive old data (>90 days)
   - Use read replicas only if needed
   - Compress large JSON fields

5. **Free alternatives**:
   - Host on personal server (if have VPS)
   - Use Supabase free tier (PostgreSQL + API)
   - Self-host Redis on same VPS

---

## 13. Conclusion & Next Steps

### 13.1 Recommended Solution

**Hybrid Approach**: Web Dashboard + Telegram Bot

**Key Benefits for Lloyd**:
1. **Mobile approvals** via Telegram (instant, on-the-go)
2. **Detailed analytics** via web dashboard (desktop)
3. **Flexible settings** management (web)
4. **Real-time notifications** (Telegram)
5. **Professional appearance** (web dashboard for clients/investors)
6. **Scalable architecture** (can add features easily)

**Technology Stack**:
- Frontend: React + Vite + Tailwind CSS + shadcn/ui
- Backend: FastAPI + PostgreSQL + Redis
- Notifications: Telegram Bot (python-telegram-bot)
- Hosting: Railway (easiest) or Render (cheapest)
- Cost: ~$30-50/month all-in

### 13.2 Implementation Timeline

**7 weeks total** (part-time, ~10-15 hours/week):

- **Week 1**: Foundation (auth, database, basic UI)
- **Week 2**: Reply queue system (core approval workflow)
- **Week 3**: Telegram bot integration
- **Week 4**: Analytics dashboard
- **Week 5**: Settings & bot control
- **Week 6**: Reply history & polish
- **Week 7**: Testing & deployment

**Fast-track option** (3-4 weeks full-time):
- Focus on core features only (skip advanced analytics initially)
- Use Streamlit for quick MVP
- Deploy on free tiers
- Add polish later

### 13.3 Immediate Next Steps

1. **Decision Point**: Confirm hybrid approach (web + Telegram)

2. **Set up infrastructure**:
   - Create Railway/Render account
   - Provision PostgreSQL + Redis
   - Set up GitHub repo for dashboard

3. **Start with Phase 1** (Week 1):
   - Initialize FastAPI project
   - Create database schema
   - Build basic React shell
   - Implement authentication

4. **Parallel work**:
   - Modify existing bot to use reply queue API (instead of auto-posting)
   - Create Telegram bot (basic commands)

5. **Test early**:
   - Deploy to staging environment ASAP
   - Test approval workflow end-to-end
   - Iterate based on real usage

### 13.4 Success Metrics

**Technical**:
- 99.9% uptime
- <500ms API response time
- Real-time updates (<2s latency)
- Zero security incidents

**User Experience (Lloyd)**:
- Approve reply in <30 seconds (mobile)
- Review analytics in <2 minutes
- Adjust settings in <1 minute
- Understand bot performance at a glance

**Business**:
- Maintain 90%+ voice validation
- Achieve 2-3% engagement rate (critical replies)
- Stay within $50/month budget
- Save 80% of time vs manual replies

---

## 14. Appendix

### 14.1 Additional Resources

**Documentation Links**:
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Tailwind CSS: https://tailwindcss.com/
- shadcn/ui: https://ui.shadcn.com/
- python-telegram-bot: https://python-telegram-bot.org/
- Railway: https://docs.railway.app/
- Render: https://render.com/docs

**Tutorials**:
- FastAPI + PostgreSQL: https://testdriven.io/blog/fastapi-crud/
- React + Tailwind: https://www.youtube.com/watch?v=bxmDnn7lrnk
- Telegram Bot: https://github.com/python-telegram-bot/python-telegram-bot/wiki

**Example Projects**:
- FastAPI + React Template: https://github.com/tiangolo/full-stack-fastapi-postgresql
- Telegram Approval Bot: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples

### 14.2 Glossary

- **JWT**: JSON Web Token (authentication)
- **WebSocket**: Real-time bidirectional communication protocol
- **CORS**: Cross-Origin Resource Sharing (security)
- **CRUD**: Create, Read, Update, Delete (basic operations)
- **ORM**: Object-Relational Mapping (database abstraction)
- **SSR**: Server-Side Rendering
- **SPA**: Single-Page Application
- **API**: Application Programming Interface
- **REST**: Representational State Transfer (API architecture)
- **HTTPS**: HTTP Secure (encrypted)

### 14.3 Contact & Support

For questions about this architecture document:
- Email: lloyd@beliefforge.com
- Review existing bot code: `C:\Users\lloyd\Documents\Social Reply`
- API documentation: Will be auto-generated via FastAPI at `/docs`

---

**END OF DOCUMENT**

*This architecture is designed to grow with your business. Start with the core approval workflow, then expand analytics and automation as you gain confidence in the system.*

*Remember: The goal is to save you time while maintaining reply quality. The dashboard should make your life easier, not add complexity.*

Good luck with the build!
