const STORE_LABEL_OVERRIDES = {
    'kunesbuickgmcgreenfield': 'Kunes Buick GMC of Greenfield',
    'kunesbuickgmcoakcreek': 'Kunes Buick GMC of Oak Creek',
    'kunescdjrelkhorn': 'Kunes CDJR of Elkhorn',
    'kuneschevroletdevan': 'Kunes Chevrolet of Delavan',
    'kuneschevroletgmclakegeneva': 'Kunes Chevrolet GMC of Lake Geneva',
    'kunesfordantioch': 'Kunes Ford of Antioch',
    'kunesforddevan': 'Kunes Ford of Delavan',
    'kuneshopechevy': 'Kunes Chevy Hope'
};

function formatNumber(value, fallback = '-') {
    if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
        return fallback;
    }
    const numeric = typeof value === 'string' ? Number(value) : value;
    if (!Number.isFinite(numeric)) {
        return fallback;
    }
    return numeric.toLocaleString('en-US');
}

function formatCurrency(value, { withSign = false, decimals = 0, fallback = '—' } = {}) {
    if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
        return fallback;
    }

    const numeric = typeof value === 'string' ? Number(value) : value;
    if (!Number.isFinite(numeric)) {
        return fallback;
    }

    const formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });

    const absFormatted = formatter.format(Math.abs(numeric));
    if (withSign) {
        if (numeric > 0) return `+${absFormatted}`;
        if (numeric < 0) return `-${absFormatted}`;
        return absFormatted;
    }

    return numeric < 0 ? `-${absFormatted}` : absFormatted;
}

function normalizeStoreName(storeId) {
    if (!storeId) {
        return 'All Stores';
    }

    const lower = storeId.toLowerCase();
    if (STORE_LABEL_OVERRIDES[lower]) {
        return STORE_LABEL_OVERRIDES[lower];
    }

    return lower
        .replace(/[-_]/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/(\d+)/g, ' $1 ')
        .split(' ')
        .filter(Boolean)
        .map(segment => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(' ');
}

function getFriendlyStoreLabel(store) {
    if (!store) {
        return 'All Stores';
    }

    if (typeof store === 'string') {
        return normalizeStoreName(store);
    }

    if (store.label) {
        return store.label;
    }

    if (store.id) {
        return normalizeStoreName(store.id);
    }

    return 'All Stores';
}

async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        throw new Error('Authentication required');
    }

    const authOptions = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
            Authorization: `Bearer ${token}`
        }
    };

    let response;
    try {
        response = await fetch(url, authOptions);
    } catch (error) {
        console.error('Network error while calling API:', error);
        throw error;
    }

    if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }

    if (response.status === 403) {
        console.warn('Forbidden response from API:', url);
        try {
            const cloned = response.clone();
            const payload = await cloned.json();
            const detail = (payload && (payload.detail || payload.error || payload.message)) || '';
            const normalized = String(detail).toLowerCase();
            if (normalized.includes('could not validate credentials') || normalized.includes('not authenticated')) {
                localStorage.removeItem('token');
                window.location.href = '/login';
                throw new Error('Authentication required');
            }
        } catch (authError) {
            console.warn('Unable to inspect 403 response payload', authError);
        }
    }

    return response;
}

function closeModal() {
    if (window.dashboard && typeof window.dashboard.closeModal === 'function') {
        window.dashboard.closeModal();
    }
}

class GlobalDateFilter {
    constructor(onChange) {
        this.onChange = onChange;
        this.currentFilter = 'last_month';
        this.customStartDate = null;
        this.customEndDate = null;

        this.dropdown = document.getElementById('global-date-filter');
        this.modal = document.getElementById('dateRangeModal');
        this.startInput = document.getElementById('start-date');
        this.endInput = document.getElementById('end-date');
        this.applyButton = document.getElementById('apply-date-range');
        this.quickButtons = Array.from(document.querySelectorAll('.quick-select-btn'));
        this.thisYearButton = document.getElementById('this-year-btn');

        this.bindEvents();
        this.updateRangeDisplay();
    }

    bindEvents() {
        if (this.dropdown) {
            this.dropdown.addEventListener('change', (event) => {
                this.handleFilterChange(event.target.value);
            });
        }

        if (this.applyButton) {
            this.applyButton.addEventListener('click', () => {
                this.applyCustomRange();
            });
        }

        if (this.thisYearButton) {
            this.thisYearButton.addEventListener('click', () => {
                const now = new Date();
                const start = new Date(now.getFullYear(), 0, 1);
                const end = now;
                this.customStartDate = start.toISOString().split('T')[0];
                this.customEndDate = end.toISOString().split('T')[0];
                if (this.startInput && this.endInput) {
                    this.startInput.value = this.customStartDate;
                    this.endInput.value = this.customEndDate;
                }
            });
        }

        if (this.quickButtons.length > 0) {
            this.quickButtons.forEach((button) => {
                button.addEventListener('click', () => {
                    const days = Number(button.dataset.days || 0);
                    if (!Number.isFinite(days) || days <= 0) {
                        return;
                    }
                    const today = new Date();
                    const start = new Date();
                    start.setDate(today.getDate() - (days - 1));
                    this.customStartDate = start.toISOString().split('T')[0];
                    this.customEndDate = today.toISOString().split('T')[0];
                    if (this.startInput && this.endInput) {
                        this.startInput.value = this.customStartDate;
                        this.endInput.value = this.customEndDate;
                    }
                });
            });
        }

        document.querySelectorAll('[data-date-modal-close]').forEach((button) => {
            button.addEventListener('click', () => {
                this.closeModal();
            });
        });

        if (this.modal) {
            this.modal.addEventListener('click', (event) => {
                if (event.target === this.modal) {
                    this.closeModal();
                }
            });
        }
    }

    handleFilterChange(newFilter) {
        if (newFilter === 'custom') {
            this.currentFilter = 'custom';
            this.openModal();
            return;
        }

        this.currentFilter = newFilter;
        this.customStartDate = null;
        this.customEndDate = null;
        this.updateRangeDisplay();
        this.notifyChange();
    }

    openModal() {
        if (!this.modal) {
            return;
        }

        this.modal.classList.remove('hidden');
        const today = new Date();

        if (this.startInput) {
            if (this.customStartDate) {
                this.startInput.value = this.customStartDate;
            } else {
                const defaultStart = new Date();
                defaultStart.setDate(today.getDate() - 29);
                this.startInput.value = defaultStart.toISOString().split('T')[0];
            }
        }

        if (this.endInput) {
            this.endInput.value = this.customEndDate || today.toISOString().split('T')[0];
        }
    }

    closeModal() {
        if (this.modal) {
            this.modal.classList.add('hidden');
        }
        if (this.dropdown && this.currentFilter !== 'custom') {
            this.dropdown.value = this.currentFilter;
        }
    }

    applyCustomRange() {
        if (!this.startInput || !this.endInput) {
            return;
        }

        const startValue = this.startInput.value;
        const endValue = this.endInput.value;

        if (!startValue || !endValue) {
            return;
        }

        if (new Date(startValue) > new Date(endValue)) {
            [this.startInput.value, this.endInput.value] = [endValue, startValue];
        }

        this.customStartDate = this.startInput.value;
        this.customEndDate = this.endInput.value;
        this.currentFilter = 'custom';
        this.closeModal();
        this.updateRangeDisplay();
        this.notifyChange();
    }

    getDateRange() {
        const today = new Date();
        const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        const startOfYear = new Date(today.getFullYear(), 0, 1);

        if (this.currentFilter === 'custom' && this.customStartDate && this.customEndDate) {
            return {
                start: this.customStartDate,
                end: this.customEndDate,
                label: this.getCustomLabel()
            };
        }

        switch (this.currentFilter) {
            case 'mtd':
                return {
                    start: startOfMonth.toISOString().split('T')[0],
                    end: today.toISOString().split('T')[0],
                    label: 'Month to Date'
                };
            case 'this_month': {
                const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                return {
                    start: startOfMonth.toISOString().split('T')[0],
                    end: endOfMonth.toISOString().split('T')[0],
                    label: 'This Month'
                };
            }
            case 'last_month': {
                const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                const end = new Date(today.getFullYear(), today.getMonth(), 0);
                return {
                    start: start.toISOString().split('T')[0],
                    end: end.toISOString().split('T')[0],
                    label: 'Last Month'
                };
            }
            case 'ytd':
                return {
                    start: startOfYear.toISOString().split('T')[0],
                    end: today.toISOString().split('T')[0],
                    label: 'Year to Date'
                };
            default:
                return {
                    start: startOfMonth.toISOString().split('T')[0],
                    end: today.toISOString().split('T')[0],
                    label: 'Month to Date'
                };
        }
    }

    getCustomLabel() {
        if (!this.customStartDate || !this.customEndDate) {
            return 'Custom Range';
        }
        const start = new Date(this.customStartDate);
        const end = new Date(this.customEndDate);
        const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        return `${startStr} - ${endStr}`;
    }

    updateRangeDisplay() {
        const display = document.getElementById('current-range-display');
        if (display) {
            const range = this.getDateRange();
            display.textContent = `${range.label} (${range.start} to ${range.end})`;
        }
    }

    notifyChange() {
        if (typeof this.onChange === 'function') {
            this.onChange(this.getDateRange());
        }
    }
}

class DashboardApp {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.currentSearch = '';
        this.statusFilter = '';
        this.descriptionFilter = '';
        this.selectedStoreId = '';
        this.currentDateRange = null;
        this.statistics = null;
        this.vehicles = [];
        this.filteredVehicles = [];
        this.pagination = null;
        this.stores = [];
        this.isUserMenuOpen = false;

        this.cacheDom();
    }

    cacheDom() {
        this.dom = {
            totalVehicles: document.getElementById('total-vehicles'),
            descriptionsUpdated: document.getElementById('descriptions-updated'),
            totalFeatures: document.getElementById('total-features'),
            timeSaved: document.getElementById('time-saved'),
            storeSelect: document.getElementById('store-select'),
            searchInput: document.getElementById('search'),
            searchClear: document.getElementById('search-clear'),
            statusFilter: document.getElementById('status-filter'),
            descriptionFilter: document.getElementById('description-filter'),
            refreshButton: document.getElementById('refresh-button'),
            prevBtn: document.getElementById('prev-btn'),
            nextBtn: document.getElementById('next-btn'),
            currentPage: document.getElementById('current-page'),
            totalPages: document.getElementById('total-pages'),
            pagination: document.getElementById('pagination'),
            resultsCount: document.getElementById('results-count'),
            tableBody: document.getElementById('vehicles-table-body'),
            bookValueCards: document.getElementById('book-value-cards-container'),
            bookValueSummary: document.getElementById('book-value-summary'),
            bookValueEmpty: document.getElementById('sidebar-empty'),
            bookValueLoading: document.getElementById('sidebar-loading'),
            toastContainer: document.getElementById('toast-container'),
            userMenuButton: document.getElementById('user-menu-button'),
            userMenu: document.getElementById('user-menu'),
            logoutButton: document.getElementById('logout-button'),
            userMenuName: document.getElementById('user-menu-name'),
            userMenuRole: document.getElementById('user-menu-role'),
            userMenuUsername: document.getElementById('user-menu-username'),
            userMenuRoleBadge: document.getElementById('user-menu-role-badge'),
            sidebarToggle: document.getElementById('sidebar-toggle'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            bookValueSidebar: document.getElementById('book-value-sidebar'),
            manageUsersLink: document.getElementById('manage-users-link'),
            addDealershipLink: document.getElementById('add-dealership-link')
        };
    }

    async init() {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
                return;
            }

            this.bindEvents();
            await this.loadCurrentUser();
            await this.loadStores();

            this.globalDateFilter = new GlobalDateFilter((range) => {
                this.handleDateRangeChange(range);
            });
            window.globalDateFilter = this.globalDateFilter;
            this.currentDateRange = this.globalDateFilter.getDateRange();

            await Promise.all([
                this.loadStatistics(),
                this.loadVehicles()
            ]);
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showToast('Failed to load dashboard data', 'error');
        }
    }

    bindEvents() {
        if (this.dom.storeSelect) {
            this.dom.storeSelect.addEventListener('change', (event) => {
                this.handleStoreChange(event.target.value);
            });
        }

        if (this.dom.searchInput) {
            this.dom.searchInput.addEventListener('input', (event) => {
                this.handleSearchInput(event.target.value);
            });
            this.dom.searchInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    this.currentPage = 1;
                    this.loadVehicles();
                }
            });
        }

        if (this.dom.searchClear) {
            this.dom.searchClear.addEventListener('click', () => {
                this.clearSearch();
            });
        }

        if (this.dom.statusFilter) {
            this.dom.statusFilter.addEventListener('change', (event) => {
                this.statusFilter = event.target.value;
                this.applyClientFilters();
            });
        }

        if (this.dom.descriptionFilter) {
            this.dom.descriptionFilter.addEventListener('change', (event) => {
                this.descriptionFilter = event.target.value;
                this.applyClientFilters();
            });
        }

        if (this.dom.refreshButton) {
            this.dom.refreshButton.addEventListener('click', () => {
                this.refreshDashboard();
            });
        }

        if (this.dom.prevBtn) {
            this.dom.prevBtn.addEventListener('click', () => {
                if (this.pagination && this.pagination.has_prev) {
                    this.currentPage -= 1;
                    this.loadVehicles();
                }
            });
        }

        if (this.dom.nextBtn) {
            this.dom.nextBtn.addEventListener('click', () => {
                if (this.pagination && this.pagination.has_next) {
                    this.currentPage += 1;
                    this.loadVehicles();
                }
            });
        }

        if (this.dom.userMenuButton) {
            this.dom.userMenuButton.addEventListener('click', (event) => {
                event.stopPropagation();
                this.toggleUserMenu(!this.isUserMenuOpen);
            });
        }

        if (this.dom.manageUsersLink) {
            this.dom.manageUsersLink.addEventListener('click', (event) => {
                event.preventDefault();
                this.toggleUserMenu(false);
                window.location.href = '/users';
            });
        }

        if (this.dom.addDealershipLink) {
            this.dom.addDealershipLink.addEventListener('click', (event) => {
                event.preventDefault();
                this.toggleUserMenu(false);
                window.location.href = '/dealerships/add';
            });
        }

        if (this.dom.logoutButton) {
            this.dom.logoutButton.addEventListener('click', (event) => {
                event.preventDefault();
                localStorage.removeItem('token');
                window.location.href = '/login';
            });
        }

        document.addEventListener('click', (event) => {
            if (!this.dom.userMenu || !this.dom.userMenuButton) {
                return;
            }

            if (this.isUserMenuOpen) {
                const clickedInsideMenu = this.dom.userMenu.contains(event.target);
                const clickedButton = this.dom.userMenuButton.contains(event.target);
                if (!clickedInsideMenu && !clickedButton) {
                    this.toggleUserMenu(false);
                }
            }
        });

        if (this.dom.sidebarToggle) {
            this.dom.sidebarToggle.addEventListener('click', () => {
                this.openSidebar();
            });
        }

        if (this.dom.sidebarOverlay) {
            this.dom.sidebarOverlay.addEventListener('click', () => {
                this.closeSidebar();
            });
        }
    }

    toggleUserMenu(forceState) {
        if (!this.dom.userMenu) {
            return;
        }

        const shouldOpen = typeof forceState === 'boolean' ? forceState : !this.isUserMenuOpen;
        this.isUserMenuOpen = shouldOpen;
        if (shouldOpen) {
            this.dom.userMenu.classList.remove('hidden');
        } else {
            this.dom.userMenu.classList.add('hidden');
        }
    }

    openSidebar() {
        if (!this.dom.bookValueSidebar || !this.dom.sidebarOverlay) {
            return;
        }
        this.dom.bookValueSidebar.classList.add('mobile-open');
        this.dom.sidebarOverlay.classList.add('active');
    }

    closeSidebar() {
        if (!this.dom.bookValueSidebar || !this.dom.sidebarOverlay) {
            return;
        }
        this.dom.bookValueSidebar.classList.remove('mobile-open');
        this.dom.sidebarOverlay.classList.remove('active');
    }

    async loadCurrentUser() {
        try {
            const response = await authenticatedFetch('/api/me');
            const data = await response.json();
            if (!data || !data.id) {
                throw new Error('Unexpected user payload');
            }
            this.currentUser = data;
            this.populateUserMenu(data);
        } catch (error) {
            console.error('Failed to load current user:', error);
            this.showToast('Unable to load user profile', 'error');
        }
    }

    populateUserMenu(user) {
        if (!user) {
            return;
        }

        if (this.dom.userMenuName) {
            this.dom.userMenuName.textContent = user.username || 'User';
        }

        if (this.dom.userMenuRole) {
            this.dom.userMenuRole.textContent = user.role_display || user.role || '';
        }

        if (this.dom.userMenuUsername) {
            this.dom.userMenuUsername.textContent = user.username || 'User';
        }

        if (this.dom.userMenuRoleBadge) {
            this.dom.userMenuRoleBadge.textContent = user.role_display || user.role || '';
        }
    }

    async loadStores() {
        try {
            const response = await authenticatedFetch('/api/stores');
            const data = await response.json();
            if (!data || !data.success) {
                throw new Error(data?.detail || 'Failed to load stores');
            }

            const stores = Array.isArray(data.stores) ? data.stores : [];
            this.stores = stores.map((store) => ({
                id: typeof store === 'string' ? store : store.id,
                label: getFriendlyStoreLabel(store)
            })).filter((store) => store.id);

            this.populateStoreSelect();
        } catch (error) {
            console.error('Failed to load stores:', error);
            this.showToast('Unable to load store list', 'error');
        }
    }

    populateStoreSelect() {
        if (!this.dom.storeSelect) {
            return;
        }

        this.dom.storeSelect.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'All Stores';
        this.dom.storeSelect.appendChild(defaultOption);

        const sortedStores = [...this.stores].sort((a, b) => a.label.localeCompare(b.label));
        sortedStores.forEach((store) => {
            const option = document.createElement('option');
            option.value = store.id || '';
            option.textContent = store.label || store.id;
            this.dom.storeSelect.appendChild(option);
        });

        if (!this.selectedStoreId && this.currentUser && Array.isArray(this.currentUser.store_ids) && this.currentUser.store_ids.length === 1) {
            this.selectedStoreId = this.currentUser.store_ids[0];
        }

        this.dom.storeSelect.value = this.selectedStoreId || '';
        window.selectedStoreId = this.selectedStoreId || '';
    }

    handleStoreChange(storeId) {
        this.selectedStoreId = storeId || '';
        window.selectedStoreId = this.selectedStoreId;
        this.currentPage = 1;
        this.refreshDashboard();
    }

    handleDateRangeChange(range) {
        this.currentDateRange = range;
        this.currentPage = 1;
        this.refreshDashboard();
    }

    handleSearchInput(value) {
        this.currentSearch = value;
        if (this.dom.searchClear) {
            this.dom.searchClear.style.display = value ? 'block' : 'none';
        }
    }

    clearSearch() {
        if (this.dom.searchInput) {
            this.dom.searchInput.value = '';
        }
        this.currentSearch = '';
        if (this.dom.searchClear) {
            this.dom.searchClear.style.display = 'none';
        }
        this.currentPage = 1;
        this.loadVehicles();
    }

    refreshDashboard() {
        Promise.all([
            this.loadStatistics(),
            this.loadVehicles()
        ]).catch((error) => {
            console.error('Error refreshing dashboard:', error);
        });
    }

    async loadStatistics() {
        try {
            if (this.dom.bookValueLoading) {
                this.dom.bookValueLoading.classList.add('active');
            }

            const params = new URLSearchParams();
            if (this.currentDateRange && this.currentDateRange.start && this.currentDateRange.end) {
                params.append('start_date', this.currentDateRange.start);
                params.append('end_date', this.currentDateRange.end);
            }

            if (this.selectedStoreId) {
                params.append('store_id', this.selectedStoreId);
            }

            const url = params.toString() ? `/api/statistics?${params}` : '/api/statistics';
            const response = await authenticatedFetch(url);
            const data = await response.json();

            if (!data || !data.success) {
                throw new Error(data?.detail || 'Failed to load statistics');
            }

            this.statistics = data.statistics;
            this.renderStatistics();
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showToast('Unable to load statistics', 'error');
        } finally {
            if (this.dom.bookValueLoading) {
                this.dom.bookValueLoading.classList.remove('active');
            }
        }
    }

    renderStatistics() {
        if (!this.statistics) {
            return;
        }

        const stats = this.statistics;
        if (this.dom.totalVehicles) {
            this.dom.totalVehicles.textContent = formatNumber(stats.total_vehicles || 0, '0');
        }
        if (this.dom.descriptionsUpdated) {
            this.dom.descriptionsUpdated.textContent = formatNumber(stats.descriptions_updated || 0, '0');
        }
        if (this.dom.totalFeatures) {
            this.dom.totalFeatures.textContent = formatNumber(stats.total_features_marked || 0, '0');
        }
        if (this.dom.timeSaved) {
            let timeDisplay = stats.time_saved_formatted || '';
            if (typeof timeDisplay === 'string') {
                timeDisplay = timeDisplay.replace(/\s*\d+\s*minutes?/gi, '').trim();
            }

            if (!timeDisplay) {
                const minutesTotal = stats.time_saved_minutes || 0;
                const hours = Math.floor(minutesTotal / 60);
                if (hours > 0) {
                    timeDisplay = `${hours} hour${hours === 1 ? '' : 's'}`;
                } else {
                    timeDisplay = `${minutesTotal} minute${minutesTotal === 1 ? '' : 's'}`;
                }
            }

            this.dom.timeSaved.textContent = timeDisplay;
        }

        const insights = stats.book_value_insights_mtd || {};
        this.renderBookValueCards(insights, stats.total_book_value_mtd || 0);
    }

    renderBookValueCards(insights, totalDifference) {
        if (!this.dom.bookValueCards || !this.dom.bookValueSummary || !this.dom.bookValueEmpty) {
            return;
        }

        const categories = insights.categories || {};
        const categoryKeys = Object.keys(categories);

        this.dom.bookValueCards.innerHTML = '';

        if (categoryKeys.length === 0) {
            this.dom.bookValueEmpty.classList.add('active');
            this.dom.bookValueSummary.textContent = 'No book value updates captured yet.';
            return;
        }

        this.dom.bookValueEmpty.classList.remove('active');
        this.dom.bookValueSummary.textContent = insights.summary || `${formatCurrency(totalDifference, { withSign: true })} total change`;

        categoryKeys.sort((a, b) => {
            const diffA = categories[a]?.difference || 0;
            const diffB = categories[b]?.difference || 0;
            return Math.abs(diffB) - Math.abs(diffA);
        });

        categoryKeys.forEach((category) => {
            const data = categories[category] || {};
            const difference = data.difference || 0;
            const amountClass = difference > 0 ? 'positive' : difference < 0 ? 'negative' : 'neutral';
            const card = document.createElement('div');
            card.className = `book-value-card ${amountClass}`;
            card.innerHTML = `
                <div class="card-header">
                    <div class="card-source">${this.escapeHtml(category)}</div>
                    <div class="card-amount ${amountClass}">${formatCurrency(difference, { withSign: true })}</div>
                </div>
            `;

            this.dom.bookValueCards.appendChild(card);
        });
    }

    async loadVehicles() {
        try {
            const params = new URLSearchParams({
                page: String(this.currentPage),
                per_page: String(this.perPage)
            });

            if (this.currentSearch) {
                params.append('search', this.currentSearch.trim());
            }

            if (this.currentDateRange && this.currentDateRange.start && this.currentDateRange.end) {
                params.append('start_date', this.currentDateRange.start);
                params.append('end_date', this.currentDateRange.end);
            }

            if (this.selectedStoreId) {
                params.append('store_id', this.selectedStoreId);
            }

            const url = `/api/vehicles?${params.toString()}`;
            const response = await authenticatedFetch(url);
            const data = await response.json();

            if (!data || !data.success) {
                throw new Error(data?.detail || 'Failed to load vehicles');
            }

            this.vehicles = Array.isArray(data.vehicles) ? data.vehicles : [];
            this.pagination = data.pagination;
            this.applyClientFilters();
            return true;
        } catch (error) {
            console.error('Failed to load vehicles:', error);
            this.showToast('Unable to load vehicles', 'error');
            return false;
        }
    }

    applyClientFilters() {
        const vehicles = Array.isArray(this.vehicles) ? [...this.vehicles] : [];

        let filtered = vehicles;
        if (this.statusFilter) {
            filtered = filtered.filter((vehicle) => {
                const status = (vehicle.processing_status || '').toLowerCase();
                if (this.statusFilter === 'success') {
                    return vehicle.processing_successful;
                }
                if (this.statusFilter === 'failed') {
                    return status === 'failed' || (!vehicle.processing_successful && status !== 'processing');
                }
                if (this.statusFilter === 'pending') {
                    return status === 'pending' || status === 'processing';
                }
                return true;
            });
        }

        if (this.descriptionFilter) {
            filtered = filtered.filter((vehicle) => {
                if (this.descriptionFilter === 'updated') {
                    return vehicle.description_updated;
                }
                if (this.descriptionFilter === 'not_updated') {
                    return !vehicle.description_updated;
                }
                return true;
            });
        }

        this.filteredVehicles = filtered;
        this.renderVehicles();
    }

    renderVehicles() {
        if (!this.dom.tableBody) {
            return;
        }

        if (this.filteredVehicles.length === 0) {
            this.dom.tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-10 text-center text-sm text-slate-500">
                        No vehicles match the current filters.
                    </td>
                </tr>
            `;
            this.updateResultsCount(this.pagination, true);
            this.renderPagination(this.pagination, true);
            return;
        }

        const rows = this.filteredVehicles.map((vehicle) => {
            const statusInfo = this.getVehicleStatusInfo(vehicle);
            return `
                <tr data-id="${vehicle.id}" class="group cursor-pointer hover:bg-slate-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-semibold text-slate-800">${this.escapeHtml(vehicle.vehicle_name || vehicle.name || `Vehicle #${vehicle.stock_number}`)}</div>
                        <div class="text-xs text-slate-500">${vehicle.vin ? `VIN …${this.escapeHtml(vehicle.vin.slice(-6))}` : 'VIN unavailable'}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">${this.escapeHtml(vehicle.stock_number || '—')}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">${this.escapeHtml(vehicle.processing_date || 'Unknown')}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-full ${statusInfo.badgeClass}">
                            ${statusInfo.icon ? `<i class="${statusInfo.icon}"></i>` : ''}${statusInfo.label}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');

        this.dom.tableBody.innerHTML = rows;
        this.attachRowHandlers();
        this.updateResultsCount(this.pagination, false);
        this.renderPagination(this.pagination, false);
    }

    attachRowHandlers() {
        if (!this.dom.tableBody) {
            return;
        }

        const rows = Array.from(this.dom.tableBody.querySelectorAll('tr[data-id]'));
        rows.forEach((row) => {
            row.addEventListener('click', () => {
                const vehicleId = Number(row.getAttribute('data-id'));
                if (Number.isFinite(vehicleId)) {
                    this.showVehicleDetails(vehicleId);
                }
            });
        });
    }

    getVehicleStatusInfo(vehicle) {
        const status = (vehicle.processing_status || '').toLowerCase();
        if (vehicle.no_build_data_found) {
            return {
                label: 'No Build Data',
                badgeClass: 'bg-amber-100 text-amber-700',
                icon: 'fas fa-clipboard-list'
            };
        }
        if (status === 'processing') {
            return {
                label: 'Processing',
                badgeClass: 'bg-blue-100 text-blue-700',
                icon: 'fas fa-spinner fa-spin'
            };
        }
        if (status === 'pending') {
            return {
                label: 'Pending',
                badgeClass: 'bg-slate-100 text-slate-700',
                icon: 'fas fa-clock'
            };
        }
        if (vehicle.processing_successful) {
            return {
                label: 'Completed',
                badgeClass: 'bg-emerald-100 text-emerald-700',
                icon: 'fas fa-check-circle'
            };
        }
        return {
            label: 'Failed',
            badgeClass: 'bg-rose-100 text-rose-700',
            icon: 'fas fa-times-circle'
        };
    }

    updateResultsCount(pagination, isEmpty) {
        if (!this.dom.resultsCount || !pagination) {
            return;
        }

        if (isEmpty) {
            this.dom.resultsCount.textContent = 'No results found';
            return;
        }

        const start = (pagination.page - 1) * pagination.per_page + 1;
        const end = Math.min(pagination.page * pagination.per_page, pagination.total);
        const filterInfo = this.currentDateRange ? ` (${this.currentDateRange.label})` : '';
        this.dom.resultsCount.textContent = `Showing ${start}-${end} of ${pagination.total} vehicles${filterInfo}`;
    }

    renderPagination(pagination, isEmpty) {
        if (!this.dom.pagination || !this.dom.prevBtn || !this.dom.nextBtn || !this.dom.currentPage || !this.dom.totalPages) {
            return;
        }

        if (!pagination || pagination.pages <= 1 || isEmpty) {
            this.dom.pagination.style.display = 'none';
            return;
        }

        this.dom.pagination.style.display = 'flex';
        this.dom.prevBtn.disabled = !pagination.has_prev;
        this.dom.nextBtn.disabled = !pagination.has_next;
        this.dom.currentPage.textContent = pagination.page;
        this.dom.totalPages.textContent = pagination.pages;
    }

    async showVehicleDetails(vehicleId) {
        try {
            const response = await authenticatedFetch(`/api/vehicle/${vehicleId}`);
            const data = await response.json();
            if (!data || !data.success) {
                throw new Error(data?.detail || 'Failed to load vehicle details');
            }
            this.displayVehicleModal(data.vehicle);
        } catch (error) {
            console.error('Failed to load vehicle details:', error);
            this.showToast('Unable to load vehicle details', 'error');
        }
    }

    displayVehicleModal(vehicle) {
        const modal = document.getElementById('vehicle-modal');
        const modalTitle = document.getElementById('modal-vehicle-title');
        const modalBody = document.getElementById('modal-vehicle-body');
        if (!modal || !modalTitle || !modalBody) {
            return;
        }

        modalTitle.textContent = vehicle.vehicle_name || vehicle.name || `Vehicle #${vehicle.stock_number}`;
        modalBody.innerHTML = this.renderVehicleDetails(vehicle);
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    renderVehicleDetails(vehicle) {
        const bookValuesSection = this.renderBookValuesTable(vehicle);
        const description = this.escapeHtml(vehicle.final_description || vehicle.ai_generated_description || 'No description available.');

        return `
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="space-y-4">
                    <div class="bg-slate-50 rounded-xl p-4">
                        <h4 class="text-sm font-semibold text-slate-600 uppercase tracking-widest mb-3">Vehicle Summary</h4>
                        <div class="space-y-2 text-sm text-slate-700">
                            <p><span class="font-semibold text-slate-900">Stock #:</span> ${this.escapeHtml(vehicle.stock_number || '—')}</p>
                            <p><span class="font-semibold text-slate-900">VIN:</span> ${this.escapeHtml(vehicle.vin || '—')}</p>
                            <p><span class="font-semibold text-slate-900">Processed:</span> ${this.escapeHtml(vehicle.processing_date || 'Unknown')}</p>
                            <p><span class="font-semibold text-slate-900">Processing Status:</span> ${this.escapeHtml(vehicle.processing_status || (vehicle.processing_successful ? 'Completed' : 'Failed'))}</p>
                        </div>
                    </div>
                    ${bookValuesSection}
                </div>
                <div class="space-y-4">
                    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                        <h4 class="text-sm font-semibold text-slate-600 uppercase tracking-widest mb-3">Final Description</h4>
                        <p class="text-sm leading-relaxed text-slate-700 whitespace-pre-line">${description}</p>
                    </div>
                </div>
            </div>
        `;
    }

    renderBookValuesTable(vehicle) {
        if (!vehicle.book_values_after_processing || !vehicle.book_values_before_processing) {
            return '';
        }

        let beforeData = {};
        let afterData = {};
        try {
            beforeData = typeof vehicle.book_values_before_processing === 'string'
                ? JSON.parse(vehicle.book_values_before_processing)
                : vehicle.book_values_before_processing;
        } catch (error) {
            console.warn('Failed to parse book_values_before_processing');
        }
        try {
            afterData = typeof vehicle.book_values_after_processing === 'string'
                ? JSON.parse(vehicle.book_values_after_processing)
                : vehicle.book_values_after_processing;
        } catch (error) {
            console.warn('Failed to parse book_values_after_processing');
        }

        const categories = new Set([...Object.keys(beforeData || {}), ...Object.keys(afterData || {})]);
        if (categories.size === 0) {
            return '';
        }

        const rows = Array.from(categories).map((category) => {
            const before = parseFloat((beforeData?.[category] || '0').toString().replace(/[^0-9.-]/g, ''));
            const after = parseFloat((afterData?.[category] || '0').toString().replace(/[^0-9.-]/g, ''));
            const difference = after - before;
            const diffText = formatCurrency(difference, { withSign: true });
            const diffClass = difference > 0 ? 'text-emerald-600' : difference < 0 ? 'text-rose-600' : 'text-slate-500';
            return `
                <tr>
                    <td class="px-3 py-2 text-xs font-semibold text-slate-600 uppercase tracking-wide">${this.escapeHtml(category)}</td>
                    <td class="px-3 py-2 text-sm text-slate-600 text-right">${formatCurrency(before, { fallback: '—' })}</td>
                    <td class="px-3 py-2 text-sm text-slate-600 text-right">${formatCurrency(after, { fallback: '—' })}</td>
                    <td class="px-3 py-2 text-sm ${diffClass} text-right">${diffText}</td>
                </tr>
            `;
        }).join('');

        return `
            <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <h4 class="text-sm font-semibold text-slate-600 uppercase tracking-widest mb-3">Book Values</h4>
                <div class="overflow-x-auto">
                    <table class="min-w-full text-sm">
                        <thead class="bg-slate-50 text-xs uppercase text-slate-500">
                            <tr>
                                <th class="px-3 py-2 text-left">Category</th>
                                <th class="px-3 py-2 text-right">Before</th>
                                <th class="px-3 py-2 text-right">After</th>
                                <th class="px-3 py-2 text-right">Difference</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    closeModal() {
        const modal = document.getElementById('vehicle-modal');
        if (!modal) {
            return;
        }
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    escapeHtml(value) {
        if (value === null || value === undefined) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    showToast(message, type = 'info') {
        if (!this.dom.toastContainer) {
            return;
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${this.escapeHtml(message)}</span>
        `;

        this.dom.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    window.dashboard = app;
    app.init();
});
