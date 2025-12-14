# Quick Start Guide: Building the Dashboard

**Goal**: Get a working approval workflow in 2 weeks

---

## Week 1: MVP Core (Human-in-the-Loop)

### Day 1-2: Backend Foundation

```bash
# Create project structure
mkdir belief-forge-dashboard
cd belief-forge-dashboard
mkdir backend frontend

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install FastAPI
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic python-jose passlib bcrypt python-multipart redis

# Create basic structure
mkdir app
cd app
touch main.py models.py database.py auth.py
```

**app/main.py** (Minimal FastAPI):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Belief Forge Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "running"}

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}
```

Run: `uvicorn app.main:app --reload`

### Day 3-4: Database Setup

**Create PostgreSQL tables** (use Alembic or raw SQL):

```sql
-- Minimum viable schema

CREATE TABLE pending_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tweet_id VARCHAR(50) UNIQUE NOT NULL,
    tweet_text TEXT NOT NULL,
    tweet_author_username VARCHAR(255) NOT NULL,
    tweet_url TEXT NOT NULL,
    suggested_reply_text TEXT NOT NULL,
    character_count INT NOT NULL,
    commercial_priority VARCHAR(20) NOT NULL,
    tweet_score DECIMAL(5,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE sent_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pending_reply_id UUID REFERENCES pending_replies(id),
    tweet_id VARCHAR(50) NOT NULL,
    reply_id VARCHAR(50),
    reply_text TEXT NOT NULL,
    commercial_priority VARCHAR(20),
    posted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Add API endpoints** (app/main.py):
```python
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends

class PendingReply(BaseModel):
    id: str
    tweet_text: str
    tweet_author_username: str
    suggested_reply_text: str
    commercial_priority: str
    tweet_score: float
    status: str

@app.get("/api/v1/replies/pending", response_model=List[PendingReply])
def get_pending_replies(db: Session = Depends(get_db)):
    """Get all pending replies"""
    replies = db.query(PendingReplies).filter_by(status='pending').all()
    return replies

@app.post("/api/v1/replies/{reply_id}/approve")
def approve_reply(reply_id: str, db: Session = Depends(get_db)):
    """Approve a reply and post to Twitter"""
    reply = db.query(PendingReplies).filter_by(id=reply_id).first()
    if not reply:
        return {"error": "Reply not found"}

    # Update status
    reply.status = 'approved'
    db.commit()

    # TODO: Call existing bot's Twitter posting function
    # post_to_twitter(reply.tweet_id, reply.suggested_reply_text)

    return {"success": True, "reply_id": reply_id}

@app.post("/api/v1/replies/{reply_id}/reject")
def reject_reply(reply_id: str, db: Session = Depends(get_db)):
    """Reject a reply"""
    reply = db.query(PendingReplies).filter_by(id=reply_id).first()
    reply.status = 'rejected'
    db.commit()
    return {"success": True}
```

### Day 5-6: Frontend Setup

```bash
cd frontend
npm create vite@latest . -- --template react
npm install

# Install dependencies
npm install @tanstack/react-query axios tailwindcss postcss autoprefixer
npm install -D @tailwindcss/forms

# Initialize Tailwind
npx tailwindcss init -p
```

**src/App.jsx** (Minimal approval UI):
```jsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

function App() {
  const queryClient = useQueryClient();

  // Fetch pending replies
  const { data: replies, isLoading } = useQuery({
    queryKey: ['replies', 'pending'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/replies/pending`);
      return res.data;
    },
    refetchInterval: 10000 // Refresh every 10 seconds
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (replyId) => axios.post(`${API_URL}/replies/${replyId}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries(['replies', 'pending']);
    }
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (replyId) => axios.post(`${API_URL}/replies/${replyId}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries(['replies', 'pending']);
    }
  });

  if (isLoading) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-3xl font-bold mb-8">Reply Queue ({replies?.length || 0})</h1>

      <div className="space-y-4">
        {replies?.map((reply) => (
          <div key={reply.id} className="bg-white p-6 rounded-lg shadow">
            <div className="mb-4">
              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                reply.commercial_priority === 'critical' ? 'bg-red-100 text-red-800' :
                reply.commercial_priority === 'high' ? 'bg-orange-100 text-orange-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {reply.commercial_priority.toUpperCase()}
              </span>
              <span className="ml-2 text-sm text-gray-600">
                Score: {reply.tweet_score}/100
              </span>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">Original Tweet:</p>
              <p className="text-gray-800 bg-gray-50 p-3 rounded">
                {reply.tweet_text}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                @{reply.tweet_author_username}
              </p>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">Suggested Reply:</p>
              <p className="text-gray-800 font-medium bg-blue-50 p-3 rounded">
                {reply.suggested_reply_text}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {reply.character_count} characters
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => approveMutation.mutate(reply.id)}
                disabled={approveMutation.isLoading}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                ✓ Approve
              </button>

              <button
                onClick={() => rejectMutation.mutate(reply.id)}
                disabled={rejectMutation.isLoading}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                ✗ Reject
              </button>

              <button
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                ✎ Edit
              </button>
            </div>
          </div>
        ))}
      </div>

      {(!replies || replies.length === 0) && (
        <div className="text-center text-gray-500 mt-12">
          <p>No pending replies</p>
        </div>
      )}
    </div>
  );
}

export default App;
```

### Day 7: Connect Bot to Queue

**Modify your existing bot** (add to your bot.py):

```python
import httpx
import asyncio

async def queue_reply_for_approval(tweet_data: dict, generated_reply: str, score: float, priority: str):
    """Queue generated reply for approval instead of auto-posting"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/replies/queue",
            json={
                "tweet_id": tweet_data["id"],
                "tweet_text": tweet_data["text"],
                "tweet_author_username": tweet_data["author"]["username"],
                "tweet_url": f"https://twitter.com/{tweet_data['author']['username']}/status/{tweet_data['id']}",
                "suggested_reply_text": generated_reply,
                "character_count": len(generated_reply),
                "commercial_priority": priority,
                "tweet_score": score,
            }
        )

    return response.json()

# In your main bot loop, replace:
# post_reply_to_twitter(tweet, reply)

# With:
# await queue_reply_for_approval(tweet, reply, score, priority)
```

**Test the full flow**:
1. Run backend: `uvicorn app.main:app --reload`
2. Run frontend: `npm run dev`
3. Run bot (modified to queue instead of post)
4. Open http://localhost:5173
5. See generated replies appear
6. Click approve/reject
7. Verify status updates

---

## Week 2: Telegram Bot

### Day 8-9: Basic Telegram Bot

```bash
pip install python-telegram-bot
```

**telegram_bot.py**:
```python
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import httpx

TELEGRAM_TOKEN = "your-bot-token-here"
API_URL = "http://localhost:8000/api/v1"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "👋 Welcome to Belief Forge Bot!\n\n"
        "Commands:\n"
        "/queue - Show pending replies\n"
        "/status - Bot status"
    )

async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending replies"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/replies/pending")
        replies = response.json()

    if not replies:
        await update.message.reply_text("No pending replies")
        return

    # Show first pending reply
    reply = replies[0]

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{reply['id']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{reply['id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""
🤖 New Reply

Tweet: {reply['tweet_text'][:100]}...
Author: @{reply['tweet_author_username']}
Priority: {reply['commercial_priority'].upper()}

Suggested Reply:
{reply['suggested_reply_text']}

✅ {reply['character_count']} chars
📊 Score: {reply['tweet_score']}/100
"""

    await update.message.reply_text(message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()

    action, reply_id = query.data.split(":")

    async with httpx.AsyncClient() as client:
        if action == "approve":
            await client.post(f"{API_URL}/replies/{reply_id}/approve")
            await query.edit_message_text("✅ Reply approved and posted!")
        elif action == "reject":
            await client.post(f"{API_URL}/replies/{reply_id}/reject")
            await query.edit_message_text("❌ Reply rejected")

def main():
    """Start the bot"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("queue", show_queue))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
```

Run: `python telegram_bot.py`

### Day 10: Auto-Notifications

**Add notification service** (backend):

```python
# app/notifications.py
from telegram import Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

async def notify_new_reply(reply_data: dict):
    """Send notification when new reply is pending"""

    keyboard = [
        [
            {"text": "✅ Approve", "callback_data": f"approve:{reply_data['id']}"},
            {"text": "❌ Reject", "callback_data": f"reject:{reply_data['id']}"}
        ]
    ]

    message = f"""
🤖 New Reply Pending

Priority: {reply_data['commercial_priority'].upper()}
Score: {reply_data['tweet_score']}/100

Tweet: {reply_data['tweet_text'][:100]}...
Author: @{reply_data['tweet_author_username']}

Suggested Reply:
{reply_data['suggested_reply_text']}
"""

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        reply_markup={"inline_keyboard": keyboard}
    )
```

**Trigger notification when reply is queued**:
```python
# In app/main.py
from app.notifications import notify_new_reply

@app.post("/api/v1/replies/queue")
async def queue_reply(reply: ReplyCreate, db: Session = Depends(get_db)):
    # Save to database
    new_reply = PendingReplies(**reply.dict())
    db.add(new_reply)
    db.commit()

    # Send Telegram notification
    await notify_new_reply(reply.dict())

    return {"success": True, "id": new_reply.id}
```

### Day 11-14: Polish & Testing

- Add edit functionality
- Add reply history view
- Add basic analytics (count of sent/pending)
- Test end-to-end flow multiple times
- Fix bugs
- Deploy to Railway/Render

---

## Deployment Checklist

### Railway Deployment (Fastest)

1. **Create Railway account**: https://railway.app
2. **Create new project**: "New Project" → "Empty Project"
3. **Add PostgreSQL**: "+ New" → "Database" → "Add PostgreSQL"
4. **Add Redis**: "+ New" → "Database" → "Add Redis"
5. **Deploy backend**:
   - "+ New" → "GitHub Repo" → Select your backend repo
   - Add environment variables (see below)
   - Deploy
6. **Deploy frontend**:
   - "+ New" → "GitHub Repo" → Select your frontend repo
   - Build command: `npm run build`
   - Static outdir: `dist`

### Environment Variables (Railway)

```bash
# Backend service
DATABASE_URL=${PGDATABASE_URL}  # Auto-filled by Railway
REDIS_URL=${REDIS_URL}          # Auto-filled by Railway
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
SECRET_KEY=your-secret-key
CORS_ORIGINS=https://your-frontend-url.railway.app
```

### Get Telegram Chat ID

1. Message your bot: `/start`
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in response
4. Copy that number

---

## Testing Checklist

- [ ] Bot generates reply and queues it
- [ ] Reply appears in web dashboard
- [ ] Telegram notification sent
- [ ] Approve via web dashboard → posts to Twitter
- [ ] Approve via Telegram → posts to Twitter
- [ ] Reject via web → reply removed
- [ ] Edit reply → validates and posts
- [ ] Multiple pending replies show correctly
- [ ] Real-time updates work (refresh shows new status)

---

## Next Steps After MVP

Once you have the basic approval workflow working:

1. **Add authentication** (if allowing others to use dashboard)
2. **Add analytics dashboard** (charts, metrics)
3. **Add settings management** (edit filters, scoring)
4. **Add reply history** (searchable archive)
5. **Add bot control panel** (pause/resume)
6. **Optimize UI** (better mobile, keyboard shortcuts)

---

## Quick Reference: Key Files

```
belief-forge-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── database.py          # DB connection
│   │   ├── notifications.py     # Telegram notifier
│   │   └── auth.py              # Authentication (later)
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main approval UI
│   │   ├── main.jsx             # Entry point
│   │   └── index.css            # Tailwind styles
│   ├── package.json
│   └── .env
│
├── telegram_bot.py              # Telegram bot handler
└── existing-bot/                # Your current Twitter bot
    └── bot.py (modified)        # Queue replies instead of auto-post
```

---

## Troubleshooting

**Bot not queuing replies**:
- Check API URL in bot.py
- Verify backend is running: `curl http://localhost:8000/api/v1/health`
- Check bot logs for errors

**Telegram notifications not working**:
- Verify TELEGRAM_BOT_TOKEN is correct
- Verify TELEGRAM_CHAT_ID is correct (see "Get Telegram Chat ID" above)
- Check bot can send messages: `/start` command should work

**Frontend not showing replies**:
- Check browser console for errors
- Verify API_URL in App.jsx
- Check CORS settings in backend
- Verify database has pending replies: `SELECT * FROM pending_replies WHERE status='pending'`

**Database connection errors**:
- Check DATABASE_URL is set correctly
- Verify PostgreSQL is running
- Check database exists and tables are created

---

## Support

Questions? Review the full architecture document:
`C:\Users\lloyd\Documents\Social Reply\DASHBOARD_ARCHITECTURE.md`

Good luck building! Start small, test often, deploy early.
