/**
 * Dashboard Component
 * Handles dashboard data loading and UI updates
 */
import stateManager from '../core/StateManager.js';
import apiService from '../services/ApiService.js';
import notificationManager from '../utils/NotificationManager.js';
import Security from '../utils/Security.js';

class Dashboard {
    constructor() {
        this.refreshInterval = null;
        this.debounceTimeout = null;
        this.isLoading = false;
        this.chartData = null;

        this.initializeEventListeners();
        this.setupStateSubscriptions();
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        // Bot control buttons
        const toggleBotBtn = document.getElementById('toggle-bot-btn');
        const emergencyStopBtn = document.getElementById('emergency-stop-btn');

        if (toggleBotBtn) {
            toggleBotBtn.addEventListener('click', () => this.toggleBot());
        }

        if (emergencyStopBtn) {
            emergencyStopBtn.addEventListener('click', () => this.emergencyStop());
        }

        this.initializePlatformToggles();
    }

    /**
     * Initialize platform toggle listeners
     */
    initializePlatformToggles() {
        const twitterBtn = document.getElementById('toggle-twitter-btn');
        const redditBtn = document.getElementById('toggle-reddit-btn');

        if (twitterBtn) {
            twitterBtn.addEventListener('click', () => this.togglePlatform('twitter'));
        }

        if (redditBtn) {
            redditBtn.addEventListener('click', () => this.togglePlatform('reddit'));
        }
    }

    /**
     * Toggle platform enabled state
     */
    async togglePlatform(platform) {
        const btnId = `toggle-${platform}-btn`;
        const btn = document.getElementById(btnId);
        if (!btn) return;

        // Determine current state from aria-checked
        const isChecked = btn.getAttribute('aria-checked') === 'true';
        const newState = !isChecked;

        // Optimistic UI update
        this.updatePlatformToggleUI(platform, newState);

        try {
            // Update config via API
            const updates = {
                platforms: {
                    [platform]: { enabled: newState }
                }
            };

            const result = await apiService.updateSettings(updates);

            if (result) {
                notificationManager.success(`${platform.charAt(0).toUpperCase() + platform.slice(1)} scraping ${newState ? 'enabled' : 'disabled'}`);
            } else {
                // Revert on failure
                this.updatePlatformToggleUI(platform, isChecked);
                notificationManager.error(`Failed to update ${platform} settings`);
            }
        } catch (error) {
            console.error(`Error toggling ${platform}:`, error);
            // Revert on error
            this.updatePlatformToggleUI(platform, isChecked);
            notificationManager.error('Failed to update settings');
        }
    }

    /**
     * Update platform toggle UI visual state
     */
    updatePlatformToggleUI(platform, isEnabled) {
        const btn = document.getElementById(`toggle-${platform}-btn`);
        if (!btn) return;

        const dot = btn.querySelector('span[aria-hidden="true"]');
        const activeColor = platform === 'twitter' ? 'bg-blue-600' : 'bg-orange-600';

        btn.setAttribute('aria-checked', isEnabled.toString());

        if (isEnabled) {
            btn.classList.remove('bg-gray-200');
            btn.classList.add(activeColor);
            dot.classList.remove('translate-x-0');
            dot.classList.add('translate-x-4'); // Adjust for width
        } else {
            btn.classList.add('bg-gray-200');
            btn.classList.remove('bg-blue-600', 'bg-orange-600');
            dot.classList.add('translate-x-0');
            dot.classList.remove('translate-x-4');
        }
    }

    /**
     * Setup state management subscriptions
     */
    setupStateSubscriptions() {
        // Subscribe to page changes
        stateManager.subscribe('currentPage', (newPage) => {
            if (newPage === 'dashboard') {
                this.startAutoRefresh();
                this.loadDashboardData();
            } else {
                this.stopAutoRefresh();
            }
        });

        // Subscribe to bot status changes
        stateManager.subscribe('bot.isActive', (isActive) => {
            this.updateBotStatusUI({ is_active: isActive });
        });
    }

    /**
     * Start auto-refresh interval
     */
    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear existing interval
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000); // Refresh every 30 seconds
    }

    /**
     * Stop auto-refresh interval
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Load dashboard data with debouncing
     */
    async loadDashboardData() {
        // Prevent multiple simultaneous loads
        if (this.isLoading) {
            console.log('Dashboard already loading, skipping...');
            return;
        }

        // Clear existing timeout
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }

        // Debounce the call to prevent multiple rapid executions
        this.debounceTimeout = setTimeout(async () => {
            if (this.isLoading) {
                return;
            }

            this.isLoading = true;
            stateManager.setState('ui.loading', true);

            try {
                console.log('Loading dashboard data...');

                // Load dashboard data
                const dashboardData = await this.loadDashboardStats();

                if (dashboardData) {
                    this.updateDashboardStats(dashboardData);

                    if (dashboardData.activity_chart) {
                        this.updateActivityChart(dashboardData.activity_chart);
                    }

                    if (dashboardData.activity_feed) {
                        this.updateActivityFeedUI(dashboardData.activity_feed);
                    }
                }

            } catch (error) {
                console.error('Error loading dashboard data:', error);
                notificationManager.error('Failed to load dashboard data');
            } finally {
                this.isLoading = false;
                stateManager.setState('ui.loading', false);
            }
        }, 200); // 200ms debounce delay
    }

    /**
     * Load dashboard statistics
     */
    async loadDashboardStats() {
        try {
            const dashboardData = await apiService.getDashboardStats();
            if (dashboardData) {
                stateManager.setState('data.dashboardStats', dashboardData);

                // Update bot status
                this.updateBotStatusUI({
                    is_active: dashboardData.stats?.bot_status === 'active'
                });

                return dashboardData;
            }
        } catch (error) {
            console.error('Error loading dashboard stats:', error);
            notificationManager.error('Failed to load dashboard statistics');
        }
        return null;
    }



    /**
     * Update dashboard statistics UI
     */
    updateDashboardStats(data) {
        // Require real data - no fallbacks
        if (!data || !data.stats) {
            console.error('No real data available for dashboard stats');
            notificationManager.error('Unable to load dashboard statistics');
            return;
        }

        // Update stats cards with real API data
        const statsElements = {
            'tweets-scraped': data.stats.tweets_scraped,
            'replies-pending': data.stats.pending_replies,
            'success-rate': data.stats.success_rate,
            'active-hours': data.stats.active_hours
        };

        Object.entries(statsElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined && value !== null) {
                if (id === 'success-rate') {
                    element.textContent = `${value}%`;
                } else {
                    element.textContent = typeof value === 'number' ?
                        value.toLocaleString() : value;
                }
                element.classList.remove('text-gray-400');
            } else if (element) {
                console.error(`Missing or invalid data for ${id}:`, value);
                element.textContent = 'N/A';
                element.classList.add('text-gray-400');
            }
        });

        // Update Platform Breakdown
        if (data.stats.platform_breakdown) {
            const breakdownEl = document.getElementById('scraped-breakdown');
            if (breakdownEl) {
                const { twitter, reddit } = data.stats.platform_breakdown;
                breakdownEl.innerHTML = `
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-gray-500">Twitter:</span>
                        <span class="text-sm font-medium text-blue-600">${twitter}</span>
                    </div>
                    <div class="h-4 w-px bg-gray-300 mx-2"></div>
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-gray-500">Reddit:</span>
                        <span class="text-sm font-medium text-orange-600">${reddit}</span>
                    </div>
                `;
            }
        }

        // Update Platform Toggles
        if (data.stats.platform_config) {
            const { twitter, reddit } = data.stats.platform_config;
            this.updatePlatformToggleUI('twitter', twitter);
            this.updatePlatformToggleUI('reddit', reddit);
        }
    }

    /**
     * Update bot status UI
     */
    updateBotStatusUI(status) {
        stateManager.setState('bot.isActive', status.is_active);

        const statusIndicator = document.querySelector('.bot-status');
        const statusText = document.querySelector('.bot-status-text');
        const statusDot = document.querySelector('.bot-status-dot');
        const toggleBtn = document.getElementById('toggle-bot-btn');

        if (!statusIndicator || !statusText || !statusDot) {
            console.log('Bot status elements not found in DOM, skipping update');
            return;
        }

        if (status.is_active) {
            // Active state
            statusDot.classList.remove('bg-red-500');
            statusDot.classList.add('bg-green-500');
            statusText.textContent = 'Bot Active';
            statusIndicator.classList.remove('bg-red-50');
            statusIndicator.classList.add('bg-green-50');

            if (toggleBtn) {
                toggleBtn.textContent = 'Pause Bot';
                toggleBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
                toggleBtn.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            }
        } else {
            // Inactive state
            statusDot.classList.remove('bg-green-500');
            statusDot.classList.add('bg-red-500');
            statusText.textContent = 'Bot Inactive';
            statusIndicator.classList.remove('bg-green-50');
            statusIndicator.classList.add('bg-red-50');

            if (toggleBtn) {
                toggleBtn.textContent = 'Start Bot';
                toggleBtn.classList.remove('bg-yellow-600', 'hover:bg-yellow-700');
                toggleBtn.classList.add('bg-green-600', 'hover:bg-green-700');
            }
        }

        // Update last session info if available
        if (status.current_session) {
            const sessionInfo = document.getElementById('session-info');
            if (sessionInfo) {
                sessionInfo.innerHTML = `
                    Current Session: ${status.current_session.tweets_scraped || 0} tweets scraped,
                    ${status.current_session.replies_generated || 0} replies generated
                `;
            }
        }
    }

    /**
     * Update activity feed UI
     */
    updateActivityFeedUI(activities) {
        const feed = document.getElementById('activity-feed');
        if (!feed) return;

        if (!activities || activities.length === 0) {
            feed.innerHTML = `
                <div class="text-center py-8">
                    <span class="material-symbols-outlined text-4xl text-gray-300">history</span>
                    <p class="mt-2 text-sm text-gray-500">No recent activity</p>
                </div>
            `;
            return;
        }

        const activitiesHtml = activities.map(activity => `
            <div class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                <div class="flex-shrink-0">
                    <span class="material-symbols-outlined ${this.getActivityColor(activity.type)}">
                        ${this.getActivityIcon(activity.type)}
                    </span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900">${Security.sanitizeText(activity.description)}</p>
                    <p class="text-sm text-gray-500">${this.formatTimeAgo(activity.timestamp)}</p>
                </div>
            </div>
        `).join('');

        Security.safeSetHTML(feed, activitiesHtml);
    }

    /**
     * Update activity chart
     */
    updateActivityChart(activityChartData) {
        const container = document.getElementById('activityChart');
        if (!container || !activityChartData) {
            console.error('Activity chart: Missing container or data');
            return;
        }

        // Check if data has changed to prevent unnecessary updates
        if (this.chartData &&
            JSON.stringify(this.chartData.labels) === JSON.stringify(activityChartData.labels) &&
            JSON.stringify(this.chartData.data) === JSON.stringify(activityChartData.data)) {
            console.log('Chart data unchanged, skipping update');
            return;
        }

        // Store current data for comparison
        this.chartData = activityChartData;

        console.log('Creating CSS activity chart with data:', activityChartData);

        const labels = activityChartData.labels || [];
        const data = activityChartData.data || [];

        // Find max value for scaling
        const maxValue = Math.max(...data, 1);

        // Create simple bar chart HTML
        const chartHTML = `
            <div class="css-bar-chart" style="display: flex; align-items: end; height: 200px; gap: 8px; padding: 10px;">
                ${labels.map((label, index) => {
            const value = data[index] || 0;
            const height = (value / maxValue) * 180; // Max height 180px
            return `
                        <div class="bar-wrapper" style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                            <div class="bar-value" style="font-size: 10px; color: #6b7280; font-weight: 500;">${value}</div>
                            <div class="bar" style="
                                width: 100%;
                                height: ${height}px;
                                background: linear-gradient(to top, rgba(139, 92, 246, 0.7), rgba(139, 92, 246, 0.4));
                                border-radius: 4px 4px 0 0;
                                min-height: 2px;
                                transition: height 0.3s ease;
                            " title="${label}: ${value} tweets"></div>
                            <div class="bar-label" style="font-size: 10px; color: #6b7280; text-align: center; margin-top: 4px;">${label}</div>
                        </div>
                    `;
        }).join('')}
            </div>
        `;

        container.innerHTML = chartHTML;
        container.style.background = 'white';
        container.style.borderRadius = '8px';
        container.style.padding = '0';
        container.style.height = '220px';

        console.log('CSS activity chart created successfully with', labels.length, 'data points');
    }

    /**
     * Toggle bot status
     */
    async toggleBot() {
        const isActive = stateManager.getState('bot.isActive');

        try {
            const endpoint = isActive ? '/bot/pause' : '/bot/start';
            const result = await apiService.apiCall(endpoint, { method: 'POST' });

            if (result) {
                const newStatus = !isActive;
                stateManager.setState('bot.isActive', newStatus);

                notificationManager.success(
                    newStatus ? 'Bot started successfully' : 'Bot paused',
                    { duration: 3000 }
                );

                this.loadDashboardData(); // Refresh status
            }
        } catch (error) {
            console.error('Failed to toggle bot status:', error);
            notificationManager.error('Failed to toggle bot status');
        }
    }

    /**
     * Emergency stop bot
     */
    async emergencyStop() {
        notificationManager.confirm(
            'Are you sure you want to emergency stop the bot? This will immediately halt all operations.',
            async () => {
                try {
                    const result = await apiService.stopBot();
                    if (result) {
                        stateManager.setState('bot.isActive', false);
                        notificationManager.error('Bot emergency stopped', { duration: 5000 });
                        this.loadDashboardData();
                    }
                } catch (error) {
                    console.error('Failed to emergency stop bot:', error);
                    notificationManager.error('Failed to stop bot');
                }
            }
        );
    }

    /**
     * Get activity icon for type
     */
    getActivityIcon(type) {
        const icons = {
            'reply': 'reply',
            'scrape': 'search',
            'generate': 'analytics',
            'post': 'send',
            'error': 'error',
            'warning': 'warning'
        };
        return icons[type] || 'info';
    }

    /**
     * Get activity color for type
     */
    getActivityColor(type) {
        const colors = {
            'reply': 'text-blue-600',
            'scrape': 'text-green-600',
            'generate': 'text-purple-600',
            'post': 'text-green-500',
            'error': 'text-red-600',
            'warning': 'text-yellow-600'
        };
        return colors[type] || 'text-gray-600';
    }

    /**
     * Format timestamp as time ago
     */
    formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'Just now';
    }

    /**
     * Cleanup resources
     */
    destroy() {
        this.stopAutoRefresh();
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
    }
}

// Create and export singleton instance
const dashboard = new Dashboard();
window.dashboard = dashboard;

export default dashboard;