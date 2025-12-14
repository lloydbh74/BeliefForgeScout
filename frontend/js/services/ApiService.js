/**
 * Centralized API Service with error handling and caching
 * Provides consistent interface for all API calls
 */
class ApiService {
    constructor() {
        this.baseURL = '/api';
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.requestQueue = new Map();
        this.retryAttempts = 3;
        this.retryDelay = 1000;
    }

    // Generate cache key
    getCacheKey(endpoint, options = {}) {
        return `${endpoint}:${JSON.stringify(options)}`;
    }

    // Check if cached data is still valid
    isCacheValid(cachedData) {
        return cachedData && Date.now() - cachedData.timestamp < this.cacheTimeout;
    }

    // Get cached data
    getCachedData(key) {
        const cached = this.cache.get(key);
        return this.isCacheValid(cached) ? cached.data : null;
    }

    // Set cached data
    setCachedData(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    // Clear cache
    clearCache(pattern = null) {
        if (pattern) {
            const regex = new RegExp(pattern);
            for (const key of this.cache.keys()) {
                if (regex.test(key)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }

    // Get auth token
    getAuthToken() {
        return localStorage.getItem('auth_token');
    }

    // Set auth token
    setAuthToken(token) {
        if (token) {
            localStorage.setItem('auth_token', token);
        } else {
            localStorage.removeItem('auth_token');
        }
    }

    // Generic GET method
    async get(endpoint, options = {}) {
        return this.apiCall(endpoint, { ...options, method: 'GET' });
    }

    // Base API call method with retry logic
    async apiCall(endpoint, options = {}) {
        const cacheKey = this.getCacheKey(endpoint, options);
        const method = options.method || 'GET';
        const useCache = options.cache !== false && method === 'GET';

        // Return cached data if available
        if (useCache) {
            const cachedData = this.getCachedData(cacheKey);
            if (cachedData) {
                return cachedData;
            }
        }

        // Prevent duplicate requests
        if (this.requestQueue.has(cacheKey)) {
            return this.requestQueue.get(cacheKey);
        }

        const requestPromise = this.executeRequest(endpoint, options);
        this.requestQueue.set(cacheKey, requestPromise);

        try {
            const response = await requestPromise;

            // Cache successful GET requests
            if (useCache && response) {
                this.setCachedData(cacheKey, response);
            }

            return response;
        } finally {
            this.requestQueue.delete(cacheKey);
        }
    }

    // Execute actual HTTP request
    async executeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = this.getAuthToken();

        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
                ...options.headers
            },
            ...options
        };

        let lastError;

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, config);

                // Handle authentication errors
                if (response.status === 401 || response.status === 403) {
                    this.handleAuthError();
                    return null;
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                lastError = error;
                console.warn(`API request attempt ${attempt} failed:`, error.message);

                // Don't retry on authentication errors
                if (error.message.includes('401')) {
                    break;
                }

                // Wait before retry (exponential backoff)
                if (attempt < this.retryAttempts) {
                    await new Promise(resolve =>
                        setTimeout(resolve, this.retryDelay * Math.pow(2, attempt - 1))
                    );
                }
            }
        }

        throw new Error(`API request failed after ${this.retryAttempts} attempts: ${lastError.message}`);
    }

    // Handle authentication errors
    handleAuthError() {
        this.setAuthToken(null);
        localStorage.removeItem('userRole');

        // Clear all cached data
        this.clearCache();

        // Redirect to login if not already there
        if (!window.location.pathname.includes('/login')) {
            window.location.replace('/login');
        }
    }

    // Dashboard endpoints
    async getDashboardStats() {
        return this.apiCall('/dashboard/');
    }

    async getPendingReplies() {
        return this.apiCall('/replies/pending');
    }

    // Analytics endpoints
    async getAnalytics() {
        return this.apiCall('/analytics/');
    }

    async getPerformanceMetrics(days = 30) {
        return this.apiCall(`/analytics/performance?days=${days}`);
    }

    async getCommercialCategories() {
        return this.apiCall('/analytics/commercial-categories');
    }

    async getHashtagPerformance() {
        return this.apiCall('/analytics/hashtags');
    }

    // Bot control endpoints
    async startBot() {
        return this.apiCall('/bot/start', { method: 'POST' });
    }

    async stopBot() {
        return this.apiCall('/bot/stop', { method: 'POST' });
    }

    async pauseBot() {
        return this.apiCall('/bot/pause', { method: 'POST' });
    }

    async getBotStatus() {
        return this.apiCall('/bot/status');
    }

    // Reply management endpoints
    async approveReply(replyId) {
        const result = await this.apiCall(`/replies/${replyId}/approve`, {
            method: 'POST',
            cache: 'no-store'
        });
        this.clearCache('/replies'); // Clear reply-related cache
        return result;
    }

    async rejectReply(replyId) {
        const result = await this.apiCall(`/replies/${replyId}/reject`, {
            method: 'POST',
            cache: 'no-store'
        });
        this.clearCache('/replies');
        return result;
    }

    async editReply(replyId, replyText) {
        const result = await this.apiCall(`/replies/${replyId}/edit`, {
            method: 'POST',
            body: JSON.stringify({ reply_text: replyText }),
            cache: 'no-store'
        });
        this.clearCache('/replies');
        return result;
    }

    async getReplyHistory() {
        return this.apiCall('/replies/history');
    }

    // Settings endpoints
    async getSettings() {
        return this.apiCall('/config');
    }

    async updateSettings(settings) {
        const result = await this.apiCall('/config', {
            method: 'POST',
            body: JSON.stringify(settings),
            cache: 'no-store'
        });
        this.clearCache('config');
        return result;
    }

    async validateCookies(cookies) {
        return this.apiCall('/settings/validate-cookies', {
            method: 'POST',
            body: JSON.stringify({ cookies: JSON.stringify(cookies) }),
            cache: 'no-store'
        });
    }

    async getCookieStatus() {
        return this.apiCall('/settings/cookie-status');
    }

    // Authentication endpoints
    async login(email, password) {
        const result = await this.apiCall('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            cache: 'no-store'
        });

        if (result?.access_token) {
            this.setAuthToken(result.access_token);
            localStorage.setItem('userRole', result.role);
        }

        return result;
    }

    async validateToken() {
        const token = this.getAuthToken();
        if (!token) {
            return false;
        }

        try {
            const response = await fetch('/api/auth/validate', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                this.handleAuthError();
                return false;
            }

            return true;
        } catch (error) {
            console.error('Token validation failed:', error);
            this.handleAuthError();
            return false;
        }
    }

    async logout() {
        try {
            await this.apiCall('/auth/logout', { method: 'POST', cache: false });
        } catch (error) {
            console.error('Logout API call failed:', error);
        } finally {
            this.handleAuthError();
        }
    }

    // Health check for API connectivity
    async healthCheck() {
        try {
            const response = await this.apiCall('/health');
            return response !== null;
        } catch (error) {
            return false;
        }
    }
}

// Create singleton instance
const apiService = new ApiService();

// Export for use in modules
window.apiService = apiService;
export default apiService;