/**
 * Settings Component
 * Handles the settings page logic, including loading/saving configuration
 * and managing dynamic lists (hashtags, keywords).
 */
import stateManager from '../core/StateManager.js';
import apiService from '../services/ApiService.js';
import notificationManager from '../utils/NotificationManager.js';
import Security from '../utils/Security.js';

class Settings {
    constructor() {
        this.isLoading = false;
        this.settings = null;

        // Bind methods to ensure correct 'this' context
        this.saveSettings = this.saveSettings.bind(this);
        this.addHashtag = this.addHashtag.bind(this);
        this.addKeyword = this.addKeyword.bind(this);
        this.validateCookies = this.validateCookies.bind(this);
    }

    /**
     * Initialize the component
     */
    async initialize() {
        // Expose methods globally for onclick handlers in HTML
        window.saveSettings = this.saveSettings;
        window.addHashtag = this.addHashtag;
        window.addKeyword = this.addKeyword;
        window.addSubreddit = this.addSubreddit.bind(this);
        window.validateCookies = this.validateCookies;

        // Expose remove functions which might be called from dynamic HTML
        window.removeHashtag = (index) => this.removeItem('hashtags', index);
        window.removeKeyword = (index) => this.removeItem('keywords', index);
        window.removeSubreddit = (index) => this.removeItem('subreddits', index);
        window.removeBanned_keyword = (index) => this.removeItem('banned_keywords', index);

        // Expose UI helpers
        window.switchSettingsTab = this.switchTab.bind(this);
        window.toggleSettingsSection = this.toggleSection.bind(this);

        // Load settings when entering the page
        this.loadSettings();
    }

    /**
     * Load settings from API
     */
    async loadSettings() {
        if (this.isLoading) return;

        this.isLoading = true;
        stateManager.setState('ui.loading', true);

        try {
            const response = await apiService.getSettings();
            if (response) {
                this.settings = response;
                this.populateForm(response);

                // Also check cookie status
                this.checkCookieStatus();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
            notificationManager.error('Failed to load settings');
        } finally {
            this.isLoading = false;
            stateManager.setState('ui.loading', false);
        }
    }

    /**
     * Populate form fields with settings data
     */
    populateForm(data) {
        // Filter Settings
        if (data.filters && data.filters.engagement) {
            this.setInputValue('min-followers', data.filters.engagement.min_followers);
            this.setInputValue('max-followers', data.filters.engagement.max_followers);
            this.setInputValue('min-likes', data.filters.engagement.min_likes);
            this.setInputValue('min-replies', data.filters.engagement.min_replies);
        }

        if (data.filters && data.filters.recency) {
            this.setInputValue('min-age-hours', data.filters.recency.min_age_hours);
            this.setInputValue('max-age-hours', data.filters.recency.max_age_hours);
        }

        if (data.filters && data.filters.content_quality) {
            this.setInputValue('min-length', data.filters.content_quality.min_length);
            this.setInputValue('max-length', data.filters.content_quality.max_length);
            this.setInputValue('reddit-max-length', data.filters.content_quality.reddit_max_length);
        }

        if (data.schedule && data.schedule.active_hours) {
            this.setInputValue('active-start', data.schedule.active_hours.start);
            this.setInputValue('active-end', data.schedule.active_hours.end);
        }

        // Targets (Hashtags & Keywords)
        if (data.targets) {
            this.renderList('hashtags', data.targets.hashtags || []);
            this.renderList('keywords', data.targets.keywords || []);
            this.renderList('subreddits', data.targets.subreddits || []);
        }

        // Hack: Map banned_keywords to targets for UI handling
        if (data.filters && data.filters.content_quality) {
            if (!this.settings.targets) this.settings.targets = {};
            this.settings.targets['banned_keywords'] = data.filters.content_quality.banned_keywords || [];
            this.renderList('banned_keywords', this.settings.targets['banned_keywords']);
        }
    }

    /**
     * Set input value safely
     */
    setInputValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.value = value !== undefined ? value : '';
        }
    }

    /**
     * Render a dynamic list (hashtags or keywords)
     */
    renderList(type, items) {
        const container = document.getElementById(`${type}-container`);
        if (!container) return;

        container.innerHTML = '';

        items.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'flex items-center space-x-2';
            div.innerHTML = `
                <input type="text" value="${Security.escapeHtml(item)}" 
                       class="flex-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
                       onchange="window.settings.updateListItem('${type}', ${index}, this.value)">
                <button onclick="window.remove${type.charAt(0).toUpperCase() + type.slice(1).replace(/s$/, '')}(${index})" 
                        class="text-red-600 hover:text-red-800 p-1">
                    <span class="material-symbols-outlined">delete</span>
                </button>
            `;
            container.appendChild(div);
        });

        // Update local state to match
        if (!this.settings) this.settings = { targets: {} };
        if (!this.settings.targets) this.settings.targets = {};
        this.settings.targets[type] = items;
    }

    /**
     * Add a new item to a list
     */
    addItem(type) {
        if (!this.settings || !this.settings.targets) return;

        const items = this.settings.targets[type] || [];
        items.push('');
        this.renderList(type, items);
    }

    addHashtag() {
        this.addItem('hashtags');
    }

    addKeyword() {
        this.addItem('keywords');
    }

    addSubreddit() {
        this.addItem('subreddits');
    }

    /**
     * Remove an item from a list
     */
    removeItem(type, index) {
        if (!this.settings || !this.settings.targets || !this.settings.targets[type]) return;

        const items = this.settings.targets[type];
        if (index >= 0 && index < items.length) {
            items.splice(index, 1);
            this.renderList(type, items);
        }
    }

    /**
     * Update an item in a list
     */
    updateListItem(type, index, value) {
        if (!this.settings || !this.settings.targets || !this.settings.targets[type]) return;

        const items = this.settings.targets[type];
        if (index >= 0 && index < items.length) {
            items[index] = value;
        }
    }

    /**
     * Save all settings
     */
    async saveSettings() {
        if (this.isLoading) return;

        try {
            const loadingId = notificationManager.loading('Saving settings...');
            this.isLoading = true;

            // Validate DOM elements
            const getVal = (id) => {
                const el = document.getElementById(id);
                if (!el) throw new Error(`Missing DOM element: ${id}`);
                return parseInt(el.value) || 0;
            };

            // Collect data from form
            const updates = {
                filters: {
                    content_quality: {
                        min_length: getVal('min-length'),
                        max_length: getVal('max-length'),
                        reddit_max_length: getVal('reddit-max-length'),
                        banned_keywords: (this.settings?.targets?.banned_keywords || []).filter(k => k && k.trim() !== '')
                    },
                    engagement: {
                        min_followers: getVal('min-followers'),
                        max_followers: getVal('max-followers'),
                        min_likes: getVal('min-likes'),
                        min_replies: getVal('min-replies')
                    },
                    recency: {
                        min_age_hours: getVal('min-age-hours'),
                        max_age_hours: getVal('max-age-hours')
                    }
                },
                targets: {
                    hashtags: (this.settings?.targets?.hashtags || []).filter(h => h && h.trim() !== ''),
                    keywords: (this.settings?.targets?.keywords || []).filter(k => k && k.trim() !== ''),
                    subreddits: (this.settings?.targets?.subreddits || []).filter(s => s && s.trim() !== '')
                },
                schedule: {
                    active_hours: {
                        start: document.getElementById('active-start')?.value || '09:00',
                        end: document.getElementById('active-end')?.value || '17:00'
                    }
                }
            };

            // Send to API
            await apiService.updateSettings(updates);

            notificationManager.remove(loadingId);
            notificationManager.success('Settings saved successfully');

            // Reload to ensure sync
            this.loadSettings();

        } catch (error) {
            console.error('Failed to save settings:', error);
            notificationManager.error(`DEBUG ERROR: ${error.name}: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Validate Twitter cookies
     */
    async validateCookies() {
        const cookiesInput = document.getElementById('twitter-cookies');
        if (!cookiesInput || !cookiesInput.value.trim()) {
            notificationManager.warning('Please enter cookies JSON first');
            return;
        }

        try {
            const loadingId = notificationManager.loading('Validating cookies...');

            // Basic JSON validation
            let cookies;
            try {
                cookies = JSON.parse(cookiesInput.value);
            } catch (e) {
                notificationManager.remove(loadingId);
                notificationManager.error('Invalid JSON format');
                return;
            }

            // Send to API
            const result = await apiService.validateCookies(cookies);

            notificationManager.remove(loadingId);

            if (result && result.status === 'valid') {
                notificationManager.success('Cookies are valid!');
                this.checkCookieStatus(); // Refresh status display
                cookiesInput.value = ''; // Clear input for security
            } else {
                notificationManager.error(result?.message || 'Cookies invalid');
            }

        } catch (error) {
            console.error('Cookie validation failed:', error);
            notificationManager.error('Cookie validation failed');
        }
    }

    /**
     * Switch Settings Tab
     */
    switchTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.settings-tab-content').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.settings-tab-btn').forEach(el => {
            el.classList.remove('border-purple-500', 'text-purple-600', 'bg-purple-50');
            el.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:bg-gray-50');
        });

        // Show selected
        const selectedContent = document.getElementById(`tab-${tabName}`);
        const selectedBtn = document.getElementById(`btn-tab-${tabName}`);

        if (selectedContent) selectedContent.classList.remove('hidden');
        if (selectedBtn) {
            selectedBtn.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:bg-gray-50');
            selectedBtn.classList.add('border-purple-500', 'text-purple-600', 'bg-purple-50');
        }
    }

    /**
     * Toggle Collapsible Section
     */
    toggleSection(sectionId) {
        const content = document.getElementById(`section-${sectionId}`);
        const icon = document.getElementById(`icon-${sectionId}`);

        if (content) {
            const isHidden = content.classList.contains('hidden');
            if (isHidden) {
                content.classList.remove('hidden');
                if (icon) icon.innerHTML = 'expand_less';
            } else {
                content.classList.add('hidden');
                if (icon) icon.innerHTML = 'expand_more';
            }
        }
    }

    /**
     * Check and display cookie status
     */
    async checkCookieStatus() {
        try {
            const status = await apiService.getCookieStatus();
            // This would update a status indicator in the UI
            // For now, we just log it as the UI element might need to be added
            console.log('Cookie status:', status);
        } catch (error) {
            console.error('Failed to check cookie status:', error);
        }
    }
}

// Create singleton instance
const settings = new Settings();
window.settings = settings;

export default settings;
