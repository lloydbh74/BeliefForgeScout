/**
 * Review Queue Component
 * Handles reply review and approval workflow
 */
import stateManager from '../core/StateManager.js';
import apiService from '../services/ApiService.js';
import notificationManager from '../utils/NotificationManager.js';
import Security from '../utils/Security.js';

class ReviewQueue {
    constructor() {
        this.isLoading = false;
        this.currentEditId = null;
        this.refreshInterval = null;

        this.initializeEventListeners();
        this.setupStateSubscriptions();
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        // Setup global event delegation for dynamic content
        document.addEventListener('click', (event) => {
            this.handleEventDelegation(event);
        });

        // Setup keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            this.handleKeyboardShortcuts(event);
        });
    }

    /**
     * Setup state management subscriptions
     */
    setupStateSubscriptions() {
        // Subscribe to page changes
        stateManager.subscribe('currentPage', (newPage) => {
            if (newPage === 'review') {
                this.startAutoRefresh();
                this.loadReviewQueue();
            } else {
                this.stopAutoRefresh();
                this.cancelAllEdits();
            }
        });

        // Subscribe to bot status changes for auto-refresh
        stateManager.subscribe('bot.isActive', () => {
            if (stateManager.getState('currentPage') === 'review') {
                this.loadReviewQueue();
            }
        });
    }

    /**
     * Start auto-refresh interval
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            if (!this.currentEditId) { // Don't refresh if editing
                this.loadReviewQueue();
            }
        }, 15000); // Refresh every 15 seconds
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
     * Handle event delegation for dynamic content
     */
    handleEventDelegation(event) {
        const target = event.target;
        const action = target.dataset.action;

        if (!action) return;

        const replyId = target.closest('[data-reply-id]')?.dataset.replyId;
        if (!replyId && ['approve', 'reject', 'edit', 'save', 'cancel'].includes(action)) {
            return;
        }

        switch (action) {
            case 'approve':
                event.preventDefault();
                this.approveReply(replyId);
                break;
            case 'reject':
                event.preventDefault();
                this.rejectReply(replyId);
                break;
            case 'edit':
                event.preventDefault();
                this.editReply(replyId);
                break;
            case 'save':
                event.preventDefault();
                this.saveEdit(replyId);
                break;
            case 'cancel':
                event.preventDefault();
                this.cancelEdit(replyId);
                break;
            case 'bulk-approve':
                event.preventDefault();
                this.bulkApprove();
                break;
            case 'bulk-reject':
                event.preventDefault();
                this.bulkReject();
                break;
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        // Only handle shortcuts when on review page
        if (stateManager.getState('currentPage') !== 'review') return;

        // Ctrl/Cmd + Enter to approve when focused on a reply
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            const focusedReply = document.activeElement.closest('[data-reply-id]');
            if (focusedReply) {
                const replyId = focusedReply.dataset.replyId;
                this.approveReply(replyId);
            }
        }

        // Escape to cancel editing
        if (event.key === 'Escape' && this.currentEditId) {
            this.cancelEdit(this.currentEditId);
        }
    }

    /**
     * Load review queue data
     */
    async loadReviewQueue() {
        if (this.isLoading) {
            console.log('Review queue already loading, skipping...');
            return;
        }

        this.isLoading = true;
        stateManager.setState('ui.loading', true);

        try {
            const response = await apiService.getPendingReplies();
            if (response && response.replies) {
                stateManager.setState('data.reviewQueue', response.replies);
                this.displayReplies(response.replies);
            } else {
                this.displayEmptyState();
            }
        } catch (error) {
            console.error('Error loading review queue:', error);
            notificationManager.error('Failed to load review queue');
            this.displayEmptyState(true);
        } finally {
            this.isLoading = false;
            stateManager.setState('ui.loading', false);
        }
    }

    /**
     * Display replies in the queue
     */
    displayReplies(replies) {
        const container = document.getElementById('review-queue');
        if (!container) return;

        if (!replies || replies.length === 0) {
            this.displayEmptyState();
            return;
        }

        const repliesHtml = replies.map(reply => this.createReplyCard(reply)).join('');
        Security.safeSetHTML(container, repliesHtml);

        // Update bulk action buttons
        this.updateBulkActions(replies.length);
    }

    /**
     * Display empty state
     */
    displayEmptyState(error = false) {
        const container = document.getElementById('review-queue');
        if (!container) return;

        const emptyHtml = `
            <div class="text-center py-12">
                <span class="material-symbols-outlined text-6xl ${error ? 'text-red-300' : 'text-gray-300'}">
                    ${error ? 'error' : 'inbox'}
                </span>
                <p class="mt-4 text-lg font-medium ${error ? 'text-red-600' : 'text-gray-500'}">
                    ${error ? 'Error loading replies' : 'No replies pending review'}
                </p>
                <p class="text-sm text-gray-400 mt-1">
                    ${error ? 'Please try refreshing the page' : 'New replies will appear here for your approval'}
                </p>
                ${error ? `
                    <button onclick="reviewQueue.loadReviewQueue()"
                            class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                        Retry
                    </button>
                ` : ''}
            </div>
        `;

        container.innerHTML = emptyHtml;
        this.updateBulkActions(0);
    }

    /**
     * Create reply card HTML
     */
    createReplyCard(reply) {
        const priorityColors = {
            critical: 'bg-red-100 text-red-800',
            high: 'bg-yellow-100 text-yellow-800',
            medium: 'bg-blue-100 text-blue-800',
            low: 'bg-gray-100 text-gray-800'
        };

        const scoreColor = this.getScoreColor(reply.score || 0);
        const isEditing = this.currentEditId === reply.id;

        return `
            <div class="border border-gray-200 rounded-lg p-4 space-y-3 hover:shadow-md transition-shadow ${isEditing ? 'ring-2 ring-blue-500' : ''}"
                 data-reply-id="${reply.id}">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2 mb-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${priorityColors[reply.commercial_category] || priorityColors.medium}">
                                ${reply.commercial_category || 'medium'}
                            </span>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${scoreColor}">
                                Score: ${reply.score || 0}/100
                            </span>
                            ${reply.tweet_author ? `
                                <span class="text-sm text-gray-500">
                                    @${Security.escapeHtml(reply.tweet_author)}
                                    ${reply.tweet_author_followers ? `(${reply.tweet_author_followers.toLocaleString()} followers)` : ''}
                                </span>
                            ` : ''}
                        </div>

                        <div class="bg-gray-50 p-3 rounded-md mb-3">
                            <p class="text-sm font-medium text-gray-700 mb-2">Original Tweet:</p>
                            <p class="text-gray-800">${Security.sanitizeText(reply.tweet_text || '')}</p>
                            ${reply.tweet_url ? `
                                <a href="${Security.escapeHtml(reply.tweet_url)}"
                                   target="_blank"
                                   class="text-blue-600 hover:text-blue-800 text-sm mt-2 inline-block">
                                    View on Twitter →
                                </a>
                            ` : ''}
                        </div>

                        ${isEditing ? this.createEditMode(reply) : this.createViewMode(reply)}
                    </div>
                </div>

                ${!isEditing ? this.createActionButtons(reply.id) : ''}
            </div>
        `;
    }

    /**
     * Create view mode HTML
     */
    createViewMode(reply) {
        return `
            <div class="bg-blue-50 p-3 rounded-md">
                <p class="text-sm font-medium text-blue-800 mb-1">Generated Reply:</p>
                <p class="text-gray-800">${Security.sanitizeText(reply.generated_reply || '')}</p>
            </div>
        `;
    }

    /**
     * Create edit mode HTML
     */
    createEditMode(reply) {
        return `
            <div class="bg-yellow-50 border border-yellow-200 p-3 rounded-md">
                <p class="text-sm font-medium text-yellow-800 mb-2">Edit Reply:</p>
                <textarea id="edit-reply-${reply.id}"
                          class="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          rows="4"
                          maxlength="280"
                          placeholder="Edit your reply here...">${Security.escapeHtml(reply.generated_reply || '')}</textarea>
                <div class="flex justify-between items-center mt-2">
                    <span id="char-count-${reply.id}" class="text-sm text-gray-500">
                        ${(reply.generated_reply || '').length}/280 characters
                    </span>
                    <div class="flex space-x-2">
                        <button onclick="reviewQueue.cancelEdit(${reply.id})"
                                class="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm transition-colors">
                            Cancel
                        </button>
                        <button onclick="reviewQueue.saveEdit(${reply.id})"
                                class="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 text-sm transition-colors">
                            Save Changes
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create action buttons
     */
    createActionButtons(replyId) {
        return `
            <div class="flex justify-end space-x-2">
                <button data-action="edit"
                        data-reply-id="${replyId}"
                        class="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm transition-colors">
                    <span class="material-symbols-outlined text-sm">edit</span>
                </button>
                <button data-action="reject"
                        data-reply-id="${replyId}"
                        class="px-3 py-1.5 bg-red-100 text-red-700 rounded-md hover:bg-red-200 text-sm transition-colors">
                    Reject
                </button>
                <button data-action="approve"
                        data-reply-id="${replyId}"
                        class="px-3 py-1.5 bg-green-100 text-green-700 rounded-md hover:bg-green-200 text-sm transition-colors">
                    Approve & Post
                </button>
            </div>
        `;
    }

    /**
     * Get score color based on value
     */
    getScoreColor(score) {
        if (score >= 80) return 'bg-green-100 text-green-800';
        if (score >= 60) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    }

    /**
     * Approve a reply
     */
    async approveReply(replyId) {
        try {
            const loadingId = notificationManager.loading('Approving reply...');

            const result = await apiService.approveReply(replyId);

            notificationManager.remove(loadingId);

            if (result) {
                notificationManager.success('Reply approved and posted successfully');
                this.loadReviewQueue(); // Refresh the queue

                // Update dashboard stats if on dashboard page
                if (stateManager.getState('currentPage') === 'dashboard') {
                    window.dashboard?.loadDashboardData();
                }
            }
        } catch (error) {
            console.error('Failed to approve reply:', error);
            notificationManager.error('Failed to approve reply');
        }
    }

    /**
     * Reject a reply
     */
    async rejectReply(replyId) {
        try {
            const result = await apiService.rejectReply(replyId);
            if (result) {
                notificationManager.info('Reply rejected');
                this.loadReviewQueue(); // Refresh the queue
            }
        } catch (error) {
            console.error('Failed to reject reply:', error);
            notificationManager.error('Failed to reject reply');
        }
    }

    /**
     * Start editing a reply
     */
    editReply(replyId) {
        if (this.currentEditId && this.currentEditId !== replyId) {
            this.cancelEdit(this.currentEditId);
        }

        this.currentEditId = replyId;

        // Reload the display to show edit mode
        const replies = stateManager.getState('data.reviewQueue');
        this.displayReplies(replies);

        // Focus on textarea and setup character counter
        setTimeout(() => {
            const textarea = document.getElementById(`edit-reply-${replyId}`);
            const charCount = document.getElementById(`char-count-${replyId}`);

            if (textarea && charCount) {
                textarea.focus();
                textarea.select();

                // Setup character counter
                textarea.addEventListener('input', () => {
                    const length = textarea.value.length;
                    charCount.textContent = `${length}/280 characters`;
                    charCount.className = length > 280 ? 'text-sm text-red-500' : 'text-sm text-gray-500';
                });
            }
        }, 100);
    }

    /**
     * Save edited reply
     */
    async saveEdit(replyId) {
        const textarea = document.getElementById(`edit-reply-${replyId}`);
        if (!textarea) return;

        const replyText = textarea.value.trim();
        if (!replyText) {
            notificationManager.warning('Reply cannot be empty');
            return;
        }

        if (replyText.length > 280) {
            notificationManager.warning('Reply exceeds 280 character limit');
            return;
        }

        try {
            const loadingId = notificationManager.loading('Saving reply...');

            const result = await apiService.editReply(replyId, replyText);

            notificationManager.remove(loadingId);

            if (result) {
                notificationManager.success('Reply updated successfully');
                this.currentEditId = null;
                this.loadReviewQueue(); // Refresh the queue
            }
        } catch (error) {
            console.error('Failed to update reply:', error);
            notificationManager.error('Failed to update reply');
        }
    }

    /**
     * Cancel editing a reply
     */
    cancelEdit(replyId) {
        this.currentEditId = null;
        this.loadReviewQueue(); // Reload to cancel editing
    }

    /**
     * Cancel all edits
     */
    cancelAllEdits() {
        this.currentEditId = null;
    }

    /**
     * Bulk approve all replies
     */
    async bulkApprove() {
        const replies = stateManager.getState('data.reviewQueue');
        if (!replies || replies.length === 0) {
            notificationManager.info('No replies to approve');
            return;
        }

        notificationManager.confirm(
            `Approve all ${replies.length} pending replies?`,
            async () => {
                try {
                    const loadingId = notificationManager.loading(`Approving ${replies.length} replies...`);

                    // Approve replies in parallel with a limit
                    const promises = replies.map(reply =>
                        apiService.approveReply(reply.id).catch(error => {
                            console.error(`Failed to approve reply ${reply.id}:`, error);
                            return null;
                        })
                    );

                    const results = await Promise.all(promises);
                    notificationManager.remove(loadingId);

                    const successCount = results.filter(r => r !== null).length;

                    if (successCount > 0) {
                        notificationManager.success(`Successfully approved ${successCount} replies`);
                    }

                    if (successCount < replies.length) {
                        notificationManager.warning(`${replies.length - successCount} replies failed to approve`);
                    }

                    this.loadReviewQueue(); // Refresh the queue
                } catch (error) {
                    notificationManager.remove(loadingId);
                    console.error('Bulk approve failed:', error);
                    notificationManager.error('Failed to approve replies');
                }
            }
        );
    }

    /**
     * Bulk reject all replies
     */
    async bulkReject() {
        const replies = stateManager.getState('data.reviewQueue');
        if (!replies || replies.length === 0) {
            notificationManager.info('No replies to reject');
            return;
        }

        notificationManager.confirm(
            `Reject all ${replies.length} pending replies?`,
            async () => {
                try {
                    const loadingId = notificationManager.loading(`Rejecting ${replies.length} replies...`);

                    // Reject replies in parallel with a limit
                    const promises = replies.map(reply =>
                        apiService.rejectReply(reply.id).catch(error => {
                            console.error(`Failed to reject reply ${reply.id}:`, error);
                            return null;
                        })
                    );

                    const results = await Promise.all(promises);
                    notificationManager.remove(loadingId);

                    const successCount = results.filter(r => r !== null).length;

                    if (successCount > 0) {
                        notificationManager.info(`Successfully rejected ${successCount} replies`);
                    }

                    this.loadReviewQueue(); // Refresh the queue
                } catch (error) {
                    notificationManager.remove(loadingId);
                    console.error('Bulk reject failed:', error);
                    notificationManager.error('Failed to reject replies');
                }
            }
        );
    }

    /**
     * Update bulk action buttons
     */
    updateBulkActions(count) {
        const bulkApproveBtn = document.getElementById('bulk-approve-btn');
        const bulkRejectBtn = document.getElementById('bulk-reject-btn');

        if (bulkApproveBtn) {
            bulkApproveBtn.disabled = count === 0;
            bulkApproveBtn.textContent = count > 0 ? `Approve All (${count})` : 'Approve All';
        }

        if (bulkRejectBtn) {
            bulkRejectBtn.disabled = count === 0;
            bulkRejectBtn.textContent = count > 0 ? `Reject All (${count})` : 'Reject All';
        }
    }

    /**
     * Cleanup resources
     */
    destroy() {
        this.stopAutoRefresh();
        this.cancelAllEdits();
    }
}

// Create and export singleton instance
const reviewQueue = new ReviewQueue();
window.reviewQueue = reviewQueue;

export default reviewQueue;