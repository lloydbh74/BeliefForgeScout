/**
 * Main Application Orchestrator
 * Coordinates all components and manages application lifecycle
 */

// Import modules
import stateManager from './core/StateManager.js';
import apiService from './services/ApiService.js';
import Security from './utils/Security.js';
import notificationManager from './utils/NotificationManager.js';

// Import components
import dashboard from './components/Dashboard.js';
import reviewQueue from './components/ReviewQueue.js';
import settings from './components/Settings.js';
import './components/Analytics.js'; // Import to register window.Analytics

// Create global instances before the App class
window.stateManager = stateManager;
window.apiService = apiService;
window.security = new Security();
window.notificationManager = notificationManager;
window.dashboard = dashboard;
window.reviewQueue = reviewQueue;
window.settings = settings;

/**
 * Main Application Class
 */
class App {
    constructor() {
        this.components = {};
        this.isInitialized = false;
        this.initializationPromise = null;

        // Make utils globally available
        window.Security = Security;
        window.showNotification = (message, type, options) => {
            return window.notificationManager?.show(message, type, options);
        };
    }

    /**
     * Initialize the application
     */
    async initialize() {
        if (this.isInitialized) {
            return this.initializationPromise;
        }

        if (this.initializationPromise) {
            return this.initializationPromise;
        }

        this.initializationPromise = this._doInitialize();
        return this.initializationPromise;
    }

    /**
     * Perform actual initialization
     */
    async _doInitialize() {
        try {
            console.log('🚀 Initializing Social Reply Dashboard...');

            // Check authentication first
            const isAuthenticated = await this.checkAuthentication();
            if (!isAuthenticated) {
                console.log('🔐 Authentication required, redirecting to login');
                return;
            }

            // Initialize core systems
            this.initializeCore();

            // Initialize components
            this.initializeComponents();

            // Setup routing
            this.setupRouting();

            // Setup global error handling
            this.setupErrorHandling();

            // Setup performance monitoring
            this.setupPerformanceMonitoring();

            // Mark as initialized
            this.isInitialized = true;

            console.log('✅ Application initialized successfully');

            // Show initial page
            this.showInitialPage();

        } catch (error) {
            console.error('❌ Application initialization failed:', error);
            this.handleInitializationError(error);
        }
    }

    /**
     * Check authentication status
     */
    async checkAuthentication() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                if (window.location.pathname !== '/login') {
                    window.location.replace('/login');
                }
                return false;
            }

            // Validate token with server
            const isValid = await apiService.validateToken();
            if (!isValid) {
                console.log('🔐 Token validation failed, redirecting to login');
                if (window.location.pathname !== '/login') {
                    window.location.replace('/login');
                }
                return false;
            }

            return true;
        } catch (error) {
            console.error('Authentication check failed:', error);
            if (window.location.pathname !== '/login') {
                window.location.replace('/login');
            }
            return false;
        }
    }

    /**
     * Initialize core systems
     */
    initializeCore() {
        console.log('🔧 Initializing core systems...');

        // Initialize notification manager
        if (!window.notificationManager) {
            console.error('NotificationManager not available');
        }

        // Setup global state subscriptions
        this.setupGlobalStateSubscriptions();

        console.log('✅ Core systems initialized');
    }

    /**
     * Initialize components
     */
    initializeComponents() {
        console.log('🧩 Initializing components...');

        // Initialize components
        this.components = {
            dashboard: dashboard,
            settings: settings,
            review: reviewQueue,
            analytics: new window.Analytics()
        };

        // Expose analytics globally for onclick handlers
        window.analytics = this.components.analytics;

        // Add other components as they're created

        // Initialize each component if it has an init method
        Object.entries(this.components).forEach(([name, component]) => {
            if (component && typeof component.initialize === 'function') {
                try {
                    component.initialize();
                    console.log(`✅ ${name} component initialized`);
                } catch (error) {
                    console.error(`❌ Failed to initialize ${name} component:`, error);
                }
            } else if (component) {
                console.log(`✅ ${name} component ready`);
            }
        });

        console.log('✅ All components initialized');
    }

    /**
     * Setup routing
     */
    setupRouting() {
        console.log('🛣️ Setting up routing...');

        // Handle navigation links
        document.addEventListener('click', (event) => {
            const link = event.target.closest('[data-page]');
            if (link) {
                event.preventDefault();
                const page = link.dataset.page;
                this.showPage(page);
            }
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (event) => {
            const page = event.state?.page || 'dashboard';
            this.showPage(page, false); // Don't push state
        });

        console.log('✅ Routing setup complete');
    }

    /**
     * Setup global state subscriptions
     */
    setupGlobalStateSubscriptions() {
        // Subscribe to loading state changes
        window.stateManager.subscribe('ui.loading', (isLoading) => {
            this.updateLoadingUI(isLoading);
        });

        // Subscribe to page changes for cleanup
        window.stateManager.subscribe('currentPage', (newPage, oldPage) => {
            this.handlePageChange(newPage, oldPage);
        });
    }

    /**
     * Setup global error handling
     */
    setupErrorHandling() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            notificationManager.error('An unexpected error occurred');
            event.preventDefault();
        });

        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('JavaScript error:', event.error);
            // Don't show notifications for every error to avoid spam
            // notificationManager.error('An error occurred in the application');
        });
    }

    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        // Monitor page load performance
        if (window.performance && window.performance.timing) {
            window.addEventListener('load', () => {
                setTimeout(() => {
                    const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
                    console.log(`📊 Page load time: ${loadTime}ms`);
                }, 0);
            });
        }
    }

    /**
     * Show initial page
     */
    showInitialPage() {
        // Get page from URL hash or default to dashboard
        const hash = window.location.hash.slice(1);
        const page = hash || 'dashboard';
        this.showPage(page, false);
    }

    /**
     * Show a specific page
     */
    showPage(pageId, pushState = true) {
        if (!pageId || typeof pageId !== 'string') {
            console.warn('Invalid page ID:', pageId);
            pageId = 'dashboard';
        }

        console.log(`📄 Showing page: ${pageId}`);

        try {
            // Hide all pages
            document.querySelectorAll('[id$="-page"]').forEach(page => {
                page.classList.add('hidden');
            });

            // Show selected page
            const selectedPage = document.getElementById(`${pageId}-page`);
            if (selectedPage) {
                selectedPage.classList.remove('hidden');
            } else {
                console.warn(`Page not found: ${pageId}`);
                // Fallback to dashboard
                const dashboardPage = document.getElementById('dashboard-page');
                if (dashboardPage) {
                    dashboardPage.classList.remove('hidden');
                    pageId = 'dashboard';
                }
            }

            // Update navigation
            this.updateNavigation(pageId);

            // Update state
            window.stateManager.setState('currentPage', pageId);

            // Update URL
            if (pushState) {
                const url = `#${pageId}`;
                window.history.pushState({ page: pageId }, '', url);
            }

        } catch (error) {
            console.error('Error showing page:', error);
            notificationManager.error('Failed to load page');
        }
    }

    /**
     * Update navigation UI
     */
    updateNavigation(pageId) {
        // Update navigation links (desktop)
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('bg-blue-50', 'text-blue-700', 'border-blue-500');
            link.classList.add('text-gray-500', 'hover:text-gray-700', 'border-transparent');
        });

        const activeLink = document.querySelector(`.nav-link[data-page="${pageId}"]`);
        if (activeLink) {
            activeLink.classList.remove('text-gray-500', 'hover:text-gray-700', 'border-transparent');
            activeLink.classList.add('bg-blue-50', 'text-blue-700', 'border-blue-500');
        }

        // Update mobile navigation links
        document.querySelectorAll('.mobile-nav-link').forEach(link => {
            link.classList.remove('bg-purple-50', 'border-purple-500', 'text-purple-700');
            link.classList.add('border-transparent', 'text-gray-500', 'hover:bg-gray-50', 'hover:border-gray-300', 'hover:text-gray-700');
        });

        const activeMobileLink = document.querySelector(`.mobile-nav-link[data-page="${pageId}"]`);
        if (activeMobileLink) {
            activeMobileLink.classList.remove('border-transparent', 'text-gray-500', 'hover:bg-gray-50', 'hover:border-gray-300', 'hover:text-gray-700');
            activeMobileLink.classList.add('bg-purple-50', 'border-purple-500', 'text-purple-700');
        }

        // Update page title
        this.updatePageTitle(pageId);
    }

    /**
     * Update page title
     */
    updatePageTitle(pageId) {
        const titles = {
            dashboard: 'Dashboard - Social Reply',
            review: 'Review Queue - Social Reply',
            settings: 'Settings - Social Reply',
            analytics: 'Analytics - Social Reply',
            history: 'History - Social Reply'
        };

        document.title = titles[pageId] || 'Social Reply Dashboard';
    }

    /**
     * Handle page changes for cleanup and initialization
     */
    handlePageChange(newPage, oldPage) {
        console.log(`🔄 Page changed: ${oldPage} → ${newPage}`);

        // Cleanup old page if needed
        if (oldPage && this.components[oldPage]) {
            const component = this.components[oldPage];
            if (typeof component.onPageLeave === 'function') {
                try {
                    component.onPageLeave();
                } catch (error) {
                    console.error(`Error in ${oldPage} cleanup:`, error);
                }
            }
        }

        // Initialize new page if needed
        if (newPage && this.components[newPage]) {
            const component = this.components[newPage];
            if (typeof component.onPageEnter === 'function') {
                try {
                    component.onPageEnter();
                } catch (error) {
                    console.error(`Error in ${newPage} initialization:`, error);
                }
            }
        }
    }

    /**
     * Update loading UI
     */
    updateLoadingUI(isLoading) {
        const loadingIndicator = document.getElementById('global-loading');
        if (loadingIndicator) {
            if (isLoading) {
                loadingIndicator.classList.remove('hidden');
            } else {
                loadingIndicator.classList.add('hidden');
            }
        }

        // Update cursor
        document.body.style.cursor = isLoading ? 'wait' : 'default';
    }

    /**
     * Handle initialization errors
     */
    handleInitializationError(error) {
        console.error('Application initialization failed:', error);

        // Show error page if possible
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.classList.remove('hidden');
            errorContainer.innerHTML = `
                <div class="text-center py-12">
                    <span class="material-symbols-outlined text-6xl text-red-500">error</span>
                    <h2 class="mt-4 text-xl font-semibold text-gray-900">Application Error</h2>
                    <p class="mt-2 text-gray-600">Failed to initialize the application. Please refresh the page.</p>
                    <button onclick="window.location.reload()"
                            class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        Refresh Page
                    </button>
                </div>
            `;
        }

        notificationManager.error('Application failed to initialize. Please refresh the page.');
    }

    /**
     * Cleanup resources
     */
    destroy() {
        console.log('🧹 Cleaning up application...');

        // Destroy components
        Object.entries(this.components).forEach(([name, component]) => {
            if (component && typeof component.destroy === 'function') {
                try {
                    component.destroy();
                    console.log(`✅ ${name} component destroyed`);
                } catch (error) {
                    console.error(`❌ Error destroying ${name} component:`, error);
                }
            }
        });

        // Clear state
        window.stateManager?.clear();

        this.isInitialized = false;
        console.log('✅ Application cleanup complete');
    }

    /**
     * Get application version and info
     */
    getInfo() {
        return {
            version: '2.0.0',
            initialized: this.isInitialized,
            components: Object.keys(this.components),
            currentPage: window.stateManager?.getState('currentPage'),
            loading: window.stateManager?.getState('ui.loading')
        };
    }
}

// Create global app instance
const app = new App();
window.app = app;

// Global functions for onclick handlers (backward compatibility)
window.showPage = (pageId) => app.showPage(pageId);
window.logout = async () => {
    try {
        await window.apiService.logout();
    } catch (error) {
        console.error('Logout error:', error);
        // Force logout even if API call fails
        localStorage.removeItem('auth_token');
        localStorage.removeItem('userRole');
        window.location.replace('/login');
    }
};

window.toggleUserMenu = () => {
    const userMenu = document.getElementById('userMenu');
    if (userMenu) {
        userMenu.classList.toggle('hidden');
    }
};

window.toggleMobileMenu = () => {
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu) {
        mobileMenu.classList.toggle('hidden');
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('📱 DOM loaded, initializing application...');
    try {
        await app.initialize();
    } catch (error) {
        console.error('Failed to initialize app:', error);
    }
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    app.destroy();
});

// Export for module usage
export default app;