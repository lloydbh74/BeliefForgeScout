/**
 * Centralized State Management for Dashboard
 * Eliminates global variables and provides reactive state updates
 */
class StateManager {
    constructor() {
        this.state = {
            currentPage: 'dashboard',
            bot: {
                isActive: false,
                pendingReplies: [],
                settings: {},
                config: {}
            },
            auth: {
                token: null,
                user: null,
                isAuthenticated: false
            },
            ui: {
                loading: false,
                notifications: [],
                activeElement: null
            },
            data: {
                dashboardStats: null,
                analytics: null,
                activityFeed: [],
                reviewQueue: [],
                history: []
            }
        };

        this.listeners = new Map();
        this.initializeFromStorage();
    }

    // Initialize state from localStorage
    initializeFromStorage() {
        try {
            const token = localStorage.getItem('auth_token');
            const userRole = localStorage.getItem('userRole');

            if (token) {
                this.state.auth.token = token;
                this.state.auth.isAuthenticated = true;
                this.state.auth.user = { role: userRole };
            }
        } catch (error) {
            console.error('Error initializing state from storage:', error);
        }
    }

    // Get current state (immutable)
    getState(path = null) {
        if (path) {
            return path.split('.').reduce((obj, key) => obj?.[key], this.state);
        }
        return { ...this.state };
    }

    // Update state and notify listeners
    setState(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((obj, key) => obj[key] = obj[key] || {}, this.state);

        const oldValue = target[lastKey];
        target[lastKey] = value;

        // Notify listeners
        this.notifyListeners(path, value, oldValue);
    }

    // Subscribe to state changes
    subscribe(path, callback) {
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Set());
        }
        this.listeners.get(path).add(callback);

        // Return unsubscribe function
        return () => {
            const pathListeners = this.listeners.get(path);
            if (pathListeners) {
                pathListeners.delete(callback);
                if (pathListeners.size === 0) {
                    this.listeners.delete(path);
                }
            }
        };
    }

    // Notify all listeners for a path
    notifyListeners(path, newValue, oldValue) {
        // Notify exact path listeners
        const exactListeners = this.listeners.get(path);
        if (exactListeners) {
            exactListeners.forEach(callback => {
                try {
                    callback(newValue, oldValue, path);
                } catch (error) {
                    console.error('Error in state listener:', error);
                }
            });
        }

        // Notify parent path listeners
        const pathParts = path.split('.');
        for (let i = pathParts.length - 1; i > 0; i--) {
            const parentPath = pathParts.slice(0, i).join('.');
            const parentListeners = this.listeners.get(parentPath);
            if (parentListeners) {
                parentListeners.forEach(callback => {
                    try {
                        callback(this.getState(parentPath), null, parentPath);
                    } catch (error) {
                        console.error('Error in parent state listener:', error);
                    }
                });
            }
        }
    }

    // Batch state updates for performance
    batchUpdate(updates) {
        const oldStates = {};

        // Apply all updates
        Object.entries(updates).forEach(([path, value]) => {
            oldStates[path] = this.getState(path);
            this.setState(path, value);
        });
    }

    // Clear state (for logout)
    clear() {
        this.state = {
            currentPage: 'dashboard',
            bot: {
                isActive: false,
                pendingReplies: [],
                settings: {},
                config: {}
            },
            auth: {
                token: null,
                user: null,
                isAuthenticated: false
            },
            ui: {
                loading: false,
                notifications: [],
                activeElement: null
            },
            data: {
                dashboardStats: null,
                analytics: null,
                activityFeed: [],
                reviewQueue: [],
                history: []
            }
        };

        // Notify all listeners
        this.listeners.forEach((listeners, path) => {
            listeners.forEach(callback => {
                try {
                    callback(this.getState(path), null, path);
                } catch (error) {
                    console.error('Error in state listener:', error);
                }
            });
        });
    }

    // Utility method to update nested objects
    updateNested(path, updates) {
        const current = this.getState(path) || {};
        this.setState(path, { ...current, ...updates });
    }
}

// Create singleton instance
const stateManager = new StateManager();

// Export for use in modules
window.stateManager = stateManager;
export default stateManager;