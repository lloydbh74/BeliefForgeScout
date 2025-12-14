class Analytics {
    constructor() {
        this.container = document.getElementById('analytics-page');
        this.currentPage = 1;
        this.limit = 50;
        this.currentStatus = 'queued';
        this.searchTerm = '';
        this.currentPlatform = '';
    }

    async initialize() {
        console.log('Initializing Analytics component');
        this.render();
        await this.loadFunnelStats();
        await this.loadHistory();
        this.setupEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="space-y-6">
                <!-- Header -->
                <div class="md:flex md:items-center md:justify-between">
                    <div class="flex-1 min-w-0">
                        <h2 class="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
                            Analytics & History
                        </h2>
                    </div>
                </div>

                <!-- Platform Tabs -->
                <div class="sm:hidden">
                    <label for="tabs" class="sr-only">Select a platform</label>
                    <select id="tabs" name="tabs" class="block w-full focus:ring-purple-500 focus:border-purple-500 border-gray-300 rounded-md" onchange="window.analytics.switchPlatform(this.value)">
                        <option value="" ${this.currentPlatform === '' ? 'selected' : ''}>All Platforms</option>
                        <option value="twitter" ${this.currentPlatform === 'twitter' ? 'selected' : ''}>Twitter</option>
                        <option value="reddit" ${this.currentPlatform === 'reddit' ? 'selected' : ''}>Reddit</option>
                    </select>
                </div>
                <div class="hidden sm:block">
                    <div class="border-b border-gray-200">
                        <nav class="-mb-px flex space-x-8" aria-label="Tabs" id="platform-tabs">
                            <a href="#" onclick="event.preventDefault(); window.analytics.switchPlatform('')" 
                               class="${this.getTabClass('')} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm">
                                All Platforms
                            </a>
                            <a href="#" onclick="event.preventDefault(); window.analytics.switchPlatform('twitter')" 
                               class="${this.getTabClass('twitter')} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm">
                                Twitter
                            </a>
                            <a href="#" onclick="event.preventDefault(); window.analytics.switchPlatform('reddit')" 
                               class="${this.getTabClass('reddit')} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm">
                                Reddit
                            </a>
                        </nav>
                    </div>
                </div>

                <!-- Funnel Stats -->
                <div class="grid grid-cols-1 gap-5 sm:grid-cols-5">
                    <div class="bg-white overflow-hidden shadow rounded-lg">
                        <div class="px-4 py-5 sm:p-6">
                            <dt class="text-sm font-medium text-gray-500 truncate">Scraped</dt>
                            <dd class="mt-1 text-3xl font-semibold text-gray-900" id="funnel-scraped">-</dd>
                        </div>
                    </div>
                    <div class="bg-white overflow-hidden shadow rounded-lg">
                        <div class="px-4 py-5 sm:p-6">
                            <dt class="text-sm font-medium text-gray-500 truncate">Filtered</dt>
                            <dd class="mt-1 text-3xl font-semibold text-gray-900" id="funnel-filtered">-</dd>
                        </div>
                    </div>
                    <div class="bg-white overflow-hidden shadow rounded-lg">
                        <div class="px-4 py-5 sm:p-6">
                            <dt class="text-sm font-medium text-gray-500 truncate">Low Score</dt>
                            <dd class="mt-1 text-3xl font-semibold text-gray-900" id="funnel-scored-low">-</dd>
                        </div>
                    </div>
                    <div class="bg-white overflow-hidden shadow rounded-lg">
                        <div class="px-4 py-5 sm:p-6">
                            <dt class="text-sm font-medium text-gray-500 truncate">Deduplicated</dt>
                            <dd class="mt-1 text-3xl font-semibold text-gray-900" id="funnel-deduplicated">-</dd>
                        </div>
                    </div>
                    <div class="bg-white overflow-hidden shadow rounded-lg bg-purple-50 border-purple-200 border">
                        <div class="px-4 py-5 sm:p-6">
                            <dt class="text-sm font-medium text-purple-700 truncate">Queued</dt>
                            <dd class="mt-1 text-3xl font-semibold text-purple-900" id="funnel-queued">-</dd>
                        </div>
                    </div>
                </div>

                <!-- Filters -->
                <div class="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
                    <div class="md:flex md:items-center md:justify-between">
                        <div class="flex-1 min-w-0 flex space-x-4">
                            <select id="status-filter" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm rounded-md">
                                <option value="">All Statuses</option>
                                <option value="scraped">Scraped</option>
                                <option value="filtered">Filtered</option>
                                <option value="scored_low">Low Score</option>
                                <option value="deduplicated">Deduplicated</option>
                                <option value="queued" selected>Queued</option>
                            </select>
                            <input type="text" id="search-filter" placeholder="Search tweets..." class="shadow-sm focus:ring-purple-500 focus:border-purple-500 block w-full sm:text-sm border-gray-300 rounded-md">
                        </div>
                        <div class="mt-4 flex md:mt-0 md:ml-4">
                            <button type="button" id="refresh-btn" class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500">
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>

                <!-- History Table -->
                <div class="flex flex-col">
                    <div class="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                        <div class="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
                            <div class="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Time
                                            </th>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Tweet
                                            </th>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Details
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white divide-y divide-gray-200" id="history-table-body">
                                        <!-- Rows will be populated here -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Pagination -->
                <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6" id="pagination-controls">
                    <!-- Pagination logic here -->
                </div>
            </div>
        `;
    }

    getTabClass(platform) {
        if (this.currentPlatform === platform) {
            return 'border-purple-500 text-purple-600';
        }
        return 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300';
    }

    async switchPlatform(platform) {
        this.currentPlatform = platform;
        this.currentPage = 1;
        this.render(); // Re-render to update tab styles
        this.setupEventListeners(); // Re-bind events (inefficient but safe for now)
        await this.loadFunnelStats();
        await this.loadHistory();
    }

    async loadFunnelStats() {
        try {
            let url = '/analytics/funnel?days=7';
            if (this.currentPlatform) url += `&platform=${this.currentPlatform}`;
            const stats = await window.apiService.get(url);
            document.getElementById('funnel-scraped').textContent = stats.scraped;
            document.getElementById('funnel-filtered').textContent = stats.filtered;
            document.getElementById('funnel-scored-low').textContent = stats.scored_low;
            document.getElementById('funnel-deduplicated').textContent = stats.deduplicated;
            document.getElementById('funnel-queued').textContent = stats.queued;
        } catch (error) {
            console.error('Failed to load funnel stats:', error);
        }
    }

    async loadHistory() {
        try {
            const tbody = document.getElementById('history-table-body');
            tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">Loading...</td></tr>';

            let url = `/analytics/history?page=${this.currentPage}&limit=${this.limit}`;
            if (this.currentStatus) url += `&status=${this.currentStatus}`;
            if (this.searchTerm) url += `&search_term=${encodeURIComponent(this.searchTerm)}`;
            if (this.currentPlatform) url += `&platform=${this.currentPlatform}`;

            const response = await window.apiService.get(url);
            const { data, pagination } = response;

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No records found</td></tr>';
                return;
            }

            tbody.innerHTML = data.map(tweet => `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${new Date(tweet.scraped_at).toLocaleString()}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${this.getStatusColor(tweet.status)}">
                            ${tweet.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-900">
                        <div class="font-medium">
                            <a href="${tweet.url}" target="_blank" class="hover:text-purple-600 hover:underline">
                                @${tweet.author_username}
                            </a>
                        </div>
                        <div class="text-gray-500 truncate max-w-xs">
                            <a href="${tweet.url}" target="_blank" class="hover:text-gray-900">
                                ${tweet.tweet_text}
                            </a>
                        </div>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500">
                        ${this.formatDetails(tweet)}
                    </td>
                </tr>
            `).join('');

            this.renderPagination(pagination);

        } catch (error) {
            console.error('Failed to load history:', error);
            document.getElementById('history-table-body').innerHTML =
                '<tr><td colspan="4" class="px-6 py-4 text-center text-red-500">Error loading data</td></tr>';
        }
    }

    getStatusColor(status) {
        switch (status) {
            case 'queued': return 'bg-green-100 text-green-800';
            case 'filtered': return 'bg-red-100 text-red-800';
            case 'scored_low': return 'bg-yellow-100 text-yellow-800';
            case 'deduplicated': return 'bg-gray-100 text-gray-800';
            default: return 'bg-blue-100 text-blue-800';
        }
    }

    formatDetails(tweet) {
        if (tweet.rejection_reason) return `<span class="text-red-600">${tweet.rejection_reason}</span>`;
        if (tweet.score_details) return `Score: ${tweet.score_details.score}`;
        return '-';
    }

    renderPagination(pagination) {
        const controls = document.getElementById('pagination-controls');
        controls.innerHTML = `
            <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                    <p class="text-sm text-gray-700">
                        Showing <span class="font-medium">${(pagination.page - 1) * pagination.limit + 1}</span> to <span class="font-medium">${Math.min(pagination.page * pagination.limit, pagination.total)}</span> of <span class="font-medium">${pagination.total}</span> results
                    </p>
                </div>
                <div>
                    <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                        <button onclick="window.analytics.changePage(${pagination.page - 1})" ${pagination.page === 1 ? 'disabled' : ''} class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${pagination.page === 1 ? 'opacity-50 cursor-not-allowed' : ''}">
                            Previous
                        </button>
                        <button onclick="window.analytics.changePage(${pagination.page + 1})" ${pagination.page >= pagination.pages ? 'disabled' : ''} class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${pagination.page >= pagination.pages ? 'opacity-50 cursor-not-allowed' : ''}">
                            Next
                        </button>
                    </nav>
                </div>
            </div>
        `;
    }

    changePage(page) {
        if (page < 1) return;
        this.currentPage = page;
        this.loadHistory();
    }

    setupEventListeners() {
        document.getElementById('status-filter').addEventListener('change', (e) => {
            this.currentStatus = e.target.value;
            this.currentPage = 1;
            this.loadHistory();
        });

        document.getElementById('search-filter').addEventListener('input', (e) => {
            this.searchTerm = e.target.value;
            this.currentPage = 1;
            // Debounce could be added here
            this.loadHistory();
        });

        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadFunnelStats();
            this.loadHistory();
        });
    }
}

// Export for global usage
window.Analytics = Analytics;
