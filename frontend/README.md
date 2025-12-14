# Belief Forge Bot Dashboard

A modern web interface for managing your Twitter engagement bot, built with responsive design and real-time functionality.

## Features

### 🎯 **Dashboard (Landing Page)**
- **Real-time Statistics**: Tweets scraped, pending replies, success rates
- **Live Activity Feed**: Monitor bot actions in real-time
- **Interactive Charts**: 7-day scraping activity visualization
- **Quick Actions**: Start/stop bot, emergency controls
- **Bot Status**: Active/inactive indicators with scheduling info

### ⚙️ **Settings Management**
- **Filter Controls**: Visual sliders for engagement thresholds
- **Authentication**: Twitter cookie management with validation
- **Target Management**: Hashtag and keyword configuration
- **Bot Control**: Start/stop/pause functionality
- **Real-time Validation**: Form validation with helpful error messages

### ✅ **Reply Review & Approval**
- **Queue Management**: Filter and sort pending replies
- **Visual Cards**: Tweet preview + generated reply display
- **Scoring System**: Commercial category and quality scoring
- **Bulk Actions**: Approve multiple replies at once
- **Inline Editing**: Edit replies before approval
- **Voice Validation**: British English compliance checking

### 📊 **Analytics & History**
- **Performance Metrics**: Success rates, engagement analytics
- **Category Breakdown**: Commercial category performance
- **Hashtag Analytics**: Target performance tracking
- **Voice Compliance**: Brand voice adherence metrics
- **Top Performers**: Best-performing replies identification
- **Learning Corpus**: Reply examples for LLM training

### 🔐 **Authentication & Security**
- **JWT Authentication**: Secure token-based authentication
- **Role-based Access**: Admin and user permission levels
- **Rate Limiting**: Login attempt protection
- **Session Management**: Secure session handling

## Quick Start

### 1. **Start the Services**

```bash
# Start all services including the dashboard
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. **Access the Dashboard**

- **Frontend**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 3. **Login**

Default credentials:
- **Email**: `admin@example.com`
- **Password**: `admin123`

## Architecture

### **Frontend Stack**
- **HTML5/CSS3/JavaScript**: Modern web standards
- **Tailwind CSS**: Utility-first styling
- **Chart.js**: Interactive data visualization
- **Material Icons**: Consistent iconography
- **Responsive Design**: Mobile-first approach

### **Backend Stack**
- **FastAPI**: High-performance Python API
- **PostgreSQL**: Robust data storage
- **Redis**: Caching and session management
- **JWT**: Secure authentication
- **SQLAlchemy**: Database ORM

### **Container Architecture**
- **Frontend**: Nginx serving static files
- **API**: FastAPI application server
- **Database**: PostgreSQL with health checks
- **Cache**: Redis for performance
- **Bot**: Main Twitter engagement application

## API Endpoints

### **Authentication**
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh JWT token

### **Dashboard**
- `GET /api/dashboard/` - Main dashboard statistics
- `GET /api/dashboard/pending-replies` - Pending replies count

### **Settings**
- `GET /api/settings/` - Get current settings
- `POST /api/settings/filters` - Update filter settings
- `POST /api/settings/validate-cookies` - Validate Twitter cookies
- `GET /api/settings/bot-status` - Get bot status

### **Replies**
- `GET /api/replies/pending` - Get pending replies for review
- `POST /api/replies/action` - Handle reply actions (approve/reject/edit)
- `POST /api/replies/bulk-action` - Bulk reply actions
- `GET /api/replies/history` - Reply history

### **Analytics**
- `GET /api/analytics/performance` - Performance metrics
- `GET /api/analytics/commercial-categories` - Category performance
- `GET /api/analytics/hashtags` - Hashtag performance
- `GET /api/analytics/voice-compliance` - Voice compliance metrics

## Configuration

### **Environment Variables**

Create a `.env` file with:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password
POSTGRES_USER=social_reply
POSTGRES_DB=social_reply

# Redis
REDIS_PASSWORD=your_redis_password

# Authentication
JWT_SECRET=your_jwt_secret_key_32_characters_long

# Twitter API
OPENROUTER_API_KEY=your_openrouter_api_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### **Docker Services**

The dashboard consists of multiple services:

- **frontend**: Web interface (port 3000)
- **dashboard**: API backend (port 8000)
- **bot**: Main Twitter engagement bot
- **postgres**: Database
- **redis**: Cache
- **nginx**: Reverse proxy (optional)

## User Workflows

### **Daily Workflow**
1. **Morning Check**: Review dashboard stats and overnight activity
2. **Reply Review**: Process pending approvals (5-10 minutes)
3. **Performance Check**: Monitor yesterday's reply performance
4. **Settings Adjustment**: Fine-tune filters based on results

### **Weekly Workflow**
1. **Analytics Review**: Deep dive into performance trends
2. **Strategy Update**: Adjust commercial priorities
3. **Cookie Maintenance**: Refresh Twitter authentication if needed
4. **Learning Review**: Mark good/bad examples for LLM training

## Security Features

- **JWT Authentication**: Secure token-based access
- **Rate Limiting**: Login attempt protection
- **Role-based Access**: Different permission levels
- **Input Validation**: Comprehensive form validation
- **CORS Protection**: Cross-origin request security
- **HTTPS Ready**: SSL/TLS support via nginx

## Development

### **Local Development**

```bash
# Start only the frontend for development
cd frontend
python -m http.server 3000

# Start the API backend
cd src/api
uvicorn app:app --reload --port 8000

# Start with Docker Compose
docker-compose up --build
```

### **API Testing**

The API includes interactive documentation at `http://localhost:8000/docs` with:
- **Swagger UI**: Interactive API exploration
- **Request Examples**: Sample requests for all endpoints
- **Authentication**: Built-in JWT testing

### **Frontend Customization**

- **Styling**: Modify Tailwind classes in HTML files
- **JavaScript**: Update `js/app.js` for new functionality
- **Charts**: Configure Chart.js options in the JavaScript
- **API Integration**: Update API endpoints in the JavaScript

## Troubleshooting

### **Common Issues**

1. **Frontend Not Loading**
   - Check if the frontend service is running: `docker-compose ps`
   - Verify port 3000 is not in use
   - Check nginx configuration in `frontend/nginx.conf`

2. **API Not Responding**
   - Verify dashboard service is healthy: `docker-compose logs dashboard`
   - Check database connectivity: `docker-compose logs postgres`
   - Validate environment variables

3. **Authentication Issues**
   - Verify JWT_SECRET is set in environment
   - Check token expiration (24 hours default)
   - Review user credentials in `src/api/auth.py`

4. **Real-time Updates Not Working**
   - Check WebSocket connections in browser console
   - Verify API polling intervals in JavaScript
   - Monitor bot logs for activity

### **Health Checks**

```bash
# Check service health
docker-compose ps

# View specific service logs
docker-compose logs frontend
docker-compose logs dashboard

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:3000
```

## Monitoring

The dashboard provides built-in monitoring:
- **Real-time Stats**: Live bot performance metrics
- **Activity Feed**: Recent bot actions and events
- **Health Indicators**: Service status and connectivity
- **Performance Charts**: Visual performance tracking
- **Error Logging**: Comprehensive error tracking

## Contributing

When adding new features:

1. **Frontend**: Update HTML/CSS/JS in `frontend/` directory
2. **Backend**: Add API endpoints in `src/api/` directory
3. **Database**: Update models in `src/db/models.py`
4. **Tests**: Add tests in `tests/` directory
5. **Documentation**: Update README and API docs

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Monitor service logs with `docker-compose logs`
4. Verify environment configuration
5. Check GitHub issues for known problems

---

**Built with ❤️ for Belief Forge** - Empowering entrepreneurs through intelligent Twitter engagement.