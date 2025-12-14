/**
 * Notification Manager
 * Centralized notification system with different types and auto-dismissal
 */
class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.defaultDuration = 4000;
        this.maxNotifications = 5;
        this.notificationId = 0;

        this.init();
    }

    /**
     * Initialize the notification container
     */
    init() {
        // Create notification container if it doesn't exist
        this.container = document.getElementById('notification-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'fixed top-4 right-4 z-50 space-y-2 pointer-events-none';
            document.body.appendChild(this.container);
        }
    }

    /**
     * Show a notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {Object} options - Additional options
     * @returns {number} - Notification ID
     */
    show(message, type = 'info', options = {}) {
        const {
            duration = this.defaultDuration,
            persistent = false,
            actions = [],
            icon = null,
            html = false
        } = options;

        const id = ++this.notificationId;

        // Remove oldest notifications if we exceed the limit
        if (this.notifications.size >= this.maxNotifications) {
            const oldestId = Math.min(...this.notifications.keys());
            this.remove(oldestId);
        }

        // Create notification element
        const notification = this.createNotification(id, message, type, options);

        // Add to container
        this.container.appendChild(notification);

        // Track notification
        this.notifications.set(id, {
            element: notification,
            timeout: null,
            persistent
        });

        // Auto-dismiss if not persistent
        if (!persistent && duration > 0) {
            const timeout = setTimeout(() => {
                this.remove(id);
            }, duration);

            this.notifications.get(id).timeout = timeout;
        }

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.remove('translate-x-full');
            notification.classList.add('translate-x-0', 'notification-enter');
        });

        return id;
    }

    /**
     * Create notification DOM element
     * @param {number} id - Notification ID
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     * @param {Object} options - Additional options
     * @returns {HTMLElement} - Notification element
     */
    createNotification(id, message, type, options) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} flex items-center p-4 rounded-lg shadow-lg border pointer-events-auto transform transition-all duration-300 translate-x-full`;
        notification.dataset.notificationId = id;

        const typeConfig = this.getTypeConfig(type);
        const { icon: defaultIcon, bgColor, textColor, borderColor } = typeConfig;

        const iconToUse = options.icon || defaultIcon;
        const messageContent = options.html ? message : Security.escapeHtml(message);

        notification.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <span class="material-symbols-outlined text-xl" style="color: ${textColor}">
                        ${iconToUse}
                    </span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium" style="color: ${textColor}">
                        ${messageContent}
                    </p>
                    ${options.actions && options.actions.length > 0 ? this.createActions(options.actions) : ''}
                </div>
                <div class="flex-shrink-0 ml-4">
                    <button
                        type="button"
                        class="inline-flex rounded-md p-1.5 hover:bg-black hover:bg-opacity-10 focus:outline-none focus:ring-2 focus:ring-offset-2"
                        onclick="notificationManager.remove(${id})"
                        aria-label="Dismiss notification"
                    >
                        <span class="material-symbols-outlined text-sm" style="color: ${textColor}">
                            close
                        </span>
                    </button>
                </div>
            </div>
        `;

        // Apply styling
        notification.style.backgroundColor = bgColor;
        notification.style.borderColor = borderColor;
        notification.style.borderWidth = '1px';
        notification.style.borderStyle = 'solid';

        return notification;
    }

    /**
     * Create action buttons for notification
     * @param {Array} actions - Array of action objects
     * @returns {string} - Action buttons HTML
     */
    createActions(actions) {
        return `
            <div class="mt-3 flex space-x-2">
                ${actions.map(action => `
                    <button
                        type="button"
                        class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded focus:outline-none focus:ring-2 focus:ring-offset-2 ${action.className}"
                        onclick="${action.onclick}"
                    >
                        ${action.text}
                    </button>
                `).join('')}
            </div>
        `;
    }

    /**
     * Get notification type configuration
     * @param {string} type - Notification type
     * @returns {Object} - Type configuration
     */
    getTypeConfig(type) {
        const configs = {
            success: {
                icon: 'check_circle',
                bgColor: '#10b981',
                textColor: '#ffffff',
                borderColor: '#059669'
            },
            error: {
                icon: 'error',
                bgColor: '#ef4444',
                textColor: '#ffffff',
                borderColor: '#dc2626'
            },
            warning: {
                icon: 'warning',
                bgColor: '#f59e0b',
                textColor: '#ffffff',
                borderColor: '#d97706'
            },
            info: {
                icon: 'info',
                bgColor: '#3b82f6',
                textColor: '#ffffff',
                borderColor: '#2563eb'
            }
        };

        return configs[type] || configs.info;
    }

    /**
     * Remove a notification
     * @param {number} id - Notification ID
     */
    remove(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        // Clear timeout if exists
        if (notification.timeout) {
            clearTimeout(notification.timeout);
        }

        // Animate out
        notification.element.classList.add('notification-leave');

        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            this.notifications.delete(id);
        }, 300);
    }

    /**
     * Remove all notifications
     */
    clear() {
        for (const id of this.notifications.keys()) {
            this.remove(id);
        }
    }

    /**
     * Show success notification
     * @param {string} message - Success message
     * @param {Object} options - Additional options
     */
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    /**
     * Show error notification
     * @param {string} message - Error message
     * @param {Object} options - Additional options
     */
    error(message, options = {}) {
        return this.show(message, 'error', {
            duration: 6000, // Longer for errors
            persistent: options.persistent !== false,
            ...options
        });
    }

    /**
     * Show warning notification
     * @param {string} message - Warning message
     * @param {Object} options - Additional options
     */
    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    /**
     * Show info notification
     * @param {string} message - Info message
     * @param {Object} options - Additional options
     */
    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    /**
     * Show confirmation dialog
     * @param {string} message - Confirmation message
     * @param {Function} onConfirm - Callback when confirmed
     * @param {Function} onCancel - Callback when cancelled
     * @param {Object} options - Additional options
     */
    confirm(message, onConfirm, onCancel = null, options = {}) {
        const {
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            title = 'Confirm Action'
        } = options;

        return this.show(`
            <div class="font-medium mb-2">${Security.escapeHtml(title)}</div>
            <div class="text-sm">${Security.escapeHtml(message)}</div>
        `, 'warning', {
            persistent: true,
            html: true,
            actions: [
                {
                    text: cancelText,
                    className: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
                    onclick: `notificationManager.remove(${this.show('', 'info')}); ${onCancel ? `(${onCancel})()` : ''}`
                },
                {
                    text: confirmText,
                    className: 'bg-red-600 text-white hover:bg-red-700',
                    onclick: `notificationManager.remove(${this.show('', 'info')}); ${onConfirm ? `(${onConfirm})()` : ''}`
                }
            ]
        });
    }

    /**
     * Show loading notification
     * @param {string} message - Loading message
     * @param {Object} options - Additional options
     */
    loading(message = 'Loading...', options = {}) {
        return this.show(message, 'info', {
            persistent: true,
            icon: 'hourglass_empty',
            ...options
        });
    }

    /**
     * Update existing notification
     * @param {number} id - Notification ID
     * @param {string} message - New message
     * @param {string} type - New type
     * @param {Object} options - Additional options
     */
    update(id, message, type = null, options = {}) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        const notificationElement = notification.element;

        if (type) {
            // Update type styling
            const typeConfig = this.getTypeConfig(type);
            notificationElement.className = `notification notification-${type} flex items-center p-4 rounded-lg shadow-lg border pointer-events-auto transform transition-all duration-300`;
            notificationElement.style.backgroundColor = typeConfig.bgColor;
            notificationElement.style.borderColor = typeConfig.borderColor;

            // Update icon
            const iconElement = notificationElement.querySelector('.material-symbols-outlined');
            if (iconElement) {
                iconElement.textContent = options.icon || typeConfig.icon;
                iconElement.style.color = typeConfig.textColor;
            }
        }

        // Update message
        const messageElement = notificationElement.querySelector('p');
        if (messageElement) {
            messageElement.textContent = message;
        }

        // Reset timeout if it was persistent
        if (!options.persistent && notification.timeout) {
            clearTimeout(notification.timeout);
            const newTimeout = setTimeout(() => {
                this.remove(id);
            }, options.duration || this.defaultDuration);
            notification.timeout = newTimeout;
        }
    }

    /**
     * Get notification count by type
     * @param {string} type - Notification type (optional)
     * @returns {number} - Notification count
     */
    getCount(type = null) {
        if (type) {
            let count = 0;
            for (const [id, notification] of this.notifications) {
                if (notification.element.classList.contains(`notification-${type}`)) {
                    count++;
                }
            }
            return count;
        }
        return this.notifications.size;
    }
}

// Create singleton instance
const notificationManager = new NotificationManager();

// Export for use in modules
window.notificationManager = notificationManager;
window.showNotification = (message, type, options) => notificationManager.show(message, type, options);

export default notificationManager;