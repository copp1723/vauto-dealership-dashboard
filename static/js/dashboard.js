// Dashboard JavaScript - Vehicle Processing Dashboard
// Professional dashboard with search, filtering, and real-time updates

// Helper function for authenticated API calls
function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    const authOptions = {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    
    return fetch(url, authOptions).then(response => {
        if (response.status === 401 || response.status === 403) {
            // Token expired, invalid, or missing
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        return response;
    });
}

class VehicleDashboard {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.currentSearch = '';
        this.statusFilter = '';
        this.descriptionFilter = '';
        this.vehicles = [];
        this.statistics = {};
        this.recentActivity = [];
        this.currentVehicle = null;
        
        this.initializeEventListeners();
        this.loadInitialData();
    }

    authenticatedFetch(url, options = {}) {
        return authenticatedFetch(url, options);
    }

    initializeEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('search-input');
        const searchClear = document.getElementById('search-clear');
        const statusFilter = document.getElementById('status-filter');
        const descriptionFilter = document.getElementById('description-filter');

        // Search input with debouncing
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.currentSearch = e.target.value.trim();
                this.currentPage = 1;
                this.loadVehicles();
                this.updateSearchClearButton();
            }, 300);
        });

        // Search clear button
        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            this.currentSearch = '';
            this.currentPage = 1;
            this.loadVehicles();
            this.updateSearchClearButton();
        });

        // Filter changes
        statusFilter.addEventListener('change', (e) => {
            this.statusFilter = e.target.value;
            this.currentPage = 1;
            this.loadVehicles();
        });

        descriptionFilter.addEventListener('change', (e) => {
            this.descriptionFilter = e.target.value;
            this.currentPage = 1;
            this.loadVehicles();
        });

        // Modal close on background click
        document.getElementById('vehicle-modal').addEventListener('click', (e) => {
            if (e.target.id === 'vehicle-modal') {
                this.closeModal();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
            if (e.key === '/' && !e.target.matches('input, textarea')) {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }

    async loadInitialData() {
        try {
            this.showLoadingState();
            
            // Load all data concurrently
            await Promise.all([
                this.loadStatistics(),
                this.loadVehicles()
            ]);
            
            this.hideLoadingState();
            this.showToast('Dashboard loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showErrorState('Failed to load dashboard data');
            this.showToast('Failed to load dashboard data', 'error');
        }
    }

    async loadStatistics() {
        try {
            const response = await authenticatedFetch('/api/statistics');
            const data = await response.json();
            
            if (data.success) {
                this.statistics = data.statistics;
                this.updateStatisticsDisplay();
            } else {
                throw new Error(data.error || 'Failed to load statistics');
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
            throw error;
        }
    }

    updateStatisticsDisplay() {
        const stats = this.statistics;
        
        document.getElementById('total-vehicles').textContent = stats.total_vehicles || '0';
        document.getElementById('descriptions-updated').textContent = stats.descriptions_updated || '0';
        document.getElementById('total-features').textContent = stats.total_features_marked || '0';
        document.getElementById('no-fear-certs').textContent = stats.no_fear_certificates || '0';

        // Calculate featured vehicles count (successful vehicles processed in last 7 days)
        const featuredCount = this.vehicles ? this.vehicles.filter(v =>
            v.processing_successful &&
            v.processing_status !== 'processing' &&
            new Date(v.processing_date) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        ).length : 0;
        document.getElementById('featured-count').textContent = featuredCount.toString();
    }

    async loadVehicles() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                search: this.currentSearch
            });

            const response = await authenticatedFetch(`/api/vehicles?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.vehicles = data.vehicles;
                this.updateVehiclesDisplay();
                this.updatePagination(data.pagination);
                this.updateResultsCount(data.pagination);
            } else {
                throw new Error(data.error || 'Failed to load vehicles');
            }
        } catch (error) {
            console.error('Error loading vehicles:', error);
            this.showErrorState('Failed to load vehicles');
            throw error;
        }
    }

    updateVehiclesDisplay() {
        const vehiclesGrid = document.getElementById('vehicles-grid');

        if (this.vehicles.length === 0) {
            vehiclesGrid.innerHTML = `
                <div class="no-results">
                    <div class="error-icon">
                        <i class="fas fa-search"></i>
                    </div>
                    <p>No vehicles found matching your search criteria</p>
                    ${this.currentSearch ? `<button class="btn btn-primary" onclick="dashboard.clearSearch()">Clear Search</button>` : ''}
                </div>
            `;
            return;
        }

        const filteredVehicles = this.filterVehicles(this.vehicles);

        // Separate successful vehicles and sort by processing date (newest first)
        const successfulVehicles = filteredVehicles
            .filter(v => v.processing_successful && v.processing_status !== 'processing')
            .sort((a, b) => new Date(b.processing_date) - new Date(a.processing_date));

        const featuredVehicles = successfulVehicles.slice(0, 3);
        const remainingVehicles = filteredVehicles.filter(v => !featuredVehicles.includes(v));

        let html = '';

        // Featured vehicles section
        if (featuredVehicles.length > 0) {
            html += `
                <div class="featured-section">
                    <h3><i class="fas fa-star"></i> Recently Processed Vehicles</h3>
                    <div class="featured-grid">
                        ${featuredVehicles.map(vehicle => this.renderFeaturedVehicle(vehicle)).join('')}
                    </div>
                </div>
            `;
        }

        // Remaining vehicles section
        if (remainingVehicles.length > 0) {
            html += `
                <div class="remaining-section">
                    <h3><i class="fas fa-list"></i> All Vehicles</h3>
                    <div class="vehicle-list">
                        ${remainingVehicles.map(vehicle => this.renderVehicleListItem(vehicle)).join('')}
                    </div>
                </div>
            `;
        }

        vehiclesGrid.innerHTML = html;
    }

    renderFeaturedVehicle(vehicle) {
        return this.renderVehicleCard(vehicle);
    }

    renderVehicleCard(vehicle) {
        const statusClass = vehicle.processing_status === 'processing' ? 'processing' :
                           vehicle.processing_successful ? 'success' : 'failed';

        const statusIcon = vehicle.processing_status === 'processing' ? 'fa-spinner fa-spin' :
                          vehicle.processing_successful ? 'fa-check-circle' : 'fa-exclamation-circle';

        const statusText = vehicle.processing_status === 'processing' ? 'Processing' :
                          vehicle.processing_successful ? 'Complete' : 'Needs review';

        return `
            <div class="vehicle-card ${statusClass}" onclick="dashboard.showVehicleDetails(${vehicle.id})">
                <div class="vehicle-header">
                    <div>
                        <div class="vehicle-name">${this.escapeHtml(vehicle.vehicle_name || vehicle.name)}</div>
                        <div class="vehicle-stock">Stock #${this.escapeHtml(vehicle.stock_number)}</div>
                    </div>
                    <div class="vehicle-status ${statusClass}">
                        <i class="fas ${statusIcon}"></i> ${statusText}
                    </div>
                </div>

                <div class="vehicle-info">
                    ${vehicle.vin ? `
                        <div class="vehicle-detail">
                            <i class="fas fa-id-card"></i>
                            <span class="label">VIN:</span>
                            <span class="value">...${this.escapeHtml(vehicle.vin.slice(-6))}</span>
                        </div>
                    ` : ''}
                    <div class="vehicle-detail">
                        <i class="fas fa-clock"></i>
                        <span class="label">Processed:</span>
                        <span class="value">${this.escapeHtml(vehicle.processing_date)}</span>
                    </div>
                </div>

                <div class="vehicle-features">
                    <div class="feature-badges">
                        ${vehicle.features_count > 0 ? `
                            <span class="feature-badge">
                                <i class="fas fa-star"></i> ${vehicle.features_count} features
                            </span>
                        ` : ''}
                        ${vehicle.description_updated ? `
                            <span class="feature-badge description-status updated">
                                <i class="fas fa-edit"></i> Description Updated
                            </span>
                        ` : ''}
                    </div>
                </div>

                <div class="processing-status">
                    <div class="status-grid">
                        ${vehicle.book_values_processed ? `
                            <div class="status-item success">
                                <i class="fas fa-dollar-sign"></i>
                                <span>Book Values Processed</span>
                            </div>
                        ` : `
                            <div class="status-item pending">
                                <i class="fas fa-dollar-sign"></i>
                                <span>Book Values Pending</span>
                            </div>
                        `}
                        ${vehicle.media_tab_processed ? `
                            <div class="status-item success">
                                <i class="fas fa-images"></i>
                                <span>Media Processed</span>
                            </div>
                        ` : `
                            <div class="status-item pending">
                                <i class="fas fa-images"></i>
                                <span>Media Pending</span>
                            </div>
                        `}
                    </div>
                </div>

                ${vehicle.no_build_data_found ? `
                    <div class="no-build-data-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>No build data found for this vehicle</span>
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderVehicleListItem(vehicle) {
        return `
            <div class="vehicle-list-item" onclick="dashboard.showVehicleDetails(${vehicle.id})">
                <div class="list-item-main">
                    <div class="list-item-info">
                        <div class="list-item-name">${this.escapeHtml(vehicle.vehicle_name || vehicle.name)}</div>
                        <div class="list-item-details">
                            <span>Stock #${this.escapeHtml(vehicle.stock_number)}</span>
                            ${vehicle.vin ? `<span>VIN: ...${this.escapeHtml(vehicle.vin.slice(-6))}</span>` : ''}
                        </div>
                    </div>
                    <div class="list-item-status">
                        ${vehicle.processing_status === 'processing' ?
                            `<span class="status-badge processing"><i class="fas fa-spinner fa-spin"></i> Processing</span>` :
                            vehicle.processing_successful ?
                                `<span class="status-badge success"><i class="fas fa-check-circle"></i> Complete</span>` :
                                `<span class="status-badge muted"><i class="fas fa-info-circle"></i> Needs review</span>`
                        }
                    </div>
                </div>
                <div class="list-item-meta">
                    <span class="meta-item"><i class="fas fa-clock"></i> ${this.escapeHtml(vehicle.processing_date)}</span>
                    ${vehicle.features_count > 0 ? `<span class="meta-item"><i class="fas fa-star"></i> ${vehicle.features_count} features</span>` : ''}
                    ${vehicle.description_updated ? `<span class="meta-item updated"><i class="fas fa-edit"></i> Description Updated</span>` : ''}
                </div>
            </div>
        `;
    }

    filterVehicles(vehicles) {
        return vehicles.filter(vehicle => {
            // Status filter
            if (this.statusFilter) {
                if (this.statusFilter === 'success' && !vehicle.processing_successful) return false;
                if (this.statusFilter === 'failed' && vehicle.processing_successful) return false;
            }
            
            // Description filter
            if (this.descriptionFilter) {
                if (this.descriptionFilter === 'updated' && !vehicle.description_updated) return false;
                if (this.descriptionFilter === 'none' && vehicle.description_updated) return false;
            }
            
            return true;
        });
    }



    updatePagination(pagination) {
        const paginationElement = document.getElementById('pagination');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const currentPageElement = document.getElementById('current-page');
        const totalPagesElement = document.getElementById('total-pages');

        if (pagination.pages <= 1) {
            paginationElement.style.display = 'none';
            return;
        }

        paginationElement.style.display = 'flex';
        prevBtn.disabled = !pagination.has_prev;
        nextBtn.disabled = !pagination.has_next;
        currentPageElement.textContent = pagination.page;
        totalPagesElement.textContent = pagination.pages;
    }

    updateResultsCount(pagination) {
        const resultsCount = document.getElementById('results-count');
        const start = (pagination.page - 1) * pagination.per_page + 1;
        const end = Math.min(pagination.page * pagination.per_page, pagination.total);
        
        if (pagination.total === 0) {
            resultsCount.textContent = 'No results found';
        } else {
            resultsCount.textContent = `Showing ${start}-${end} of ${pagination.total} vehicles`;
        }
    }

    updateSearchClearButton() {
        const searchClear = document.getElementById('search-clear');
        const searchInput = document.getElementById('search-input');
        
        if (searchInput.value.trim()) {
            searchClear.style.display = 'block';
        } else {
            searchClear.style.display = 'none';
        }
    }

    async showVehicleDetails(vehicleId) {
        try {
            const response = await authenticatedFetch(`/api/vehicle/${vehicleId}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayVehicleModal(data.vehicle);
            } else {
                throw new Error(data.error || 'Failed to load vehicle details');
            }
        } catch (error) {
            console.error('Error loading vehicle details:', error);
            this.showToast('Failed to load vehicle details', 'error');
        }
    }

    displayVehicleModal(vehicle) {
        const modal = document.getElementById('vehicle-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const deleteBtn = document.getElementById('delete-vehicle-btn');

        // Store current vehicle for delete functionality
        this.currentVehicle = vehicle;

        modalTitle.textContent = vehicle.vehicle_name ? `${vehicle.vehicle_name} Details` : `Vehicle #${vehicle.stock_number} Details`;

        // Show delete button
        if (deleteBtn) {
            deleteBtn.style.display = 'inline-block';
        }

        // Parse starred features safely
        const starredFeatures = Array.isArray(vehicle.starred_features) ? vehicle.starred_features : [];
        const errors = Array.isArray(vehicle.errors_encountered) ? vehicle.errors_encountered : [];

        modalBody.innerHTML = `
            <div class="modal-section">
                <h4><i class="fas fa-info-circle"></i> Basic Information</h4>
                <div class="modal-grid">
                    ${vehicle.vehicle_name ? `
                        <div class="modal-field">
                            <label>Vehicle Name</label>
                            <value>${this.escapeHtml(vehicle.vehicle_name)}</value>
                        </div>
                    ` : ''}
                    <div class="modal-field">
                        <label>Stock Number</label>
                        <value>${this.escapeHtml(vehicle.stock_number || 'N/A')}</value>
                    </div>
                    <div class="modal-field">
                        <label>VIN</label>
                        <value>${this.escapeHtml(vehicle.vin || 'N/A')}</value>
                    </div>
                </div>
            </div>

            <div class="modal-section">
                <h4><i class="fas fa-cog"></i> Processing Summary</h4>
                <div class="modal-grid">
                    <div class="modal-field">
                        <label>Processing Date</label>
                        <value>${this.escapeHtml(vehicle.processing_date || 'N/A')}</value>
                    </div>
                    <div class="modal-field">
                        <label>Processing Status</label>
                        <value class="status ${vehicle.processing_status === 'processing' ? 'muted' : vehicle.processing_successful ? 'success' : 'danger'}">
                            ${vehicle.processing_status === 'processing' ? 'Processing...' :
                              vehicle.processing_status === 'pending' ? 'Pending' :
                              vehicle.processing_successful ? 'Successful' : 'Failed'}
                            ${vehicle.processing_status === 'processing' ? '<i class="fas fa-spinner fa-spin" style="margin-left: 8px;"></i>' : ''}
                        </value>
                    </div>
                    <div class="modal-field">
                        <label>Features Marked</label>
                        <value>${vehicle.marked_features_count || 0}</value>
                    </div>
                </div>
            </div>

            ${starredFeatures.length > 0 || vehicle.starred_features_summary ? `
                <div class="modal-section">
                    <h4><i class="fas fa-star"></i> Starred Features (${vehicle.marked_features_count || 0} total)</h4>
                    ${vehicle.starred_features_summary ? `
                        <div class="feature-summary">
                            <strong>Quick Summary:</strong> ${this.escapeHtml(vehicle.starred_features_summary)}
                        </div>
                    ` : ''}
                    ${starredFeatures.length > 0 ? `
                        <div class="feature-list">
                            ${starredFeatures.map(feature => `
                                <div class="feature-item">
                                    <i class="fas fa-star"></i>
                                    <span>${this.escapeHtml(feature.text || feature)}</span>
                                    ${feature.location ? `<small class="feature-location">${this.escapeHtml(feature.location)}</small>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            ` : ''}

            ${vehicle.feature_decisions_summary || vehicle.feature_decisions ? `
                <div class="modal-section">
                    <h4><i class="fas fa-robot"></i> AI Analysis Results</h4>
                    ${vehicle.feature_decisions_summary ? `
                        <div class="ai-summary">
                            <i class="fas fa-brain"></i>
                            <span>${this.escapeHtml(vehicle.feature_decisions_summary)}</span>
                        </div>
                    ` : ''}
                    ${vehicle.feature_decisions && Object.keys(vehicle.feature_decisions).length > 0 ? `
                        <div class="ai-decisions">
                            <button class="toggle-button" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                                <i class="fas fa-chevron-down"></i> View Detailed AI Analysis
                            </button>
                            <div class="ai-details" style="display: none;">
                                <pre>${JSON.stringify(vehicle.feature_decisions, null, 2)}</pre>
                            </div>
                        </div>
                    ` : ''}
                </div>
            ` : ''}

            <div class="modal-section">
                <h4><i class="fas fa-edit"></i> Description Information</h4>
                <div class="modal-field">
                    <label>Description Updated</label>
                    <value class="status ${vehicle.description_updated ? 'success' : 'muted'}">
                        ${vehicle.description_updated ? 'Yes' : 'No'}
                    </value>
                </div>
                ${vehicle.final_description ? `
                    <div class="modal-field">
                        <label>Final Description</label>
                        <div class="description-content">
                            ${this.formatDescription(vehicle.final_description)}
                        </div>
                    </div>
                ` : ''}
            </div>

            ${vehicle.media_totals_found && Object.keys(vehicle.media_totals_found).length > 0 ? `
                <div class="modal-section">
                    <h4><i class="fas fa-images"></i> Media Information</h4>
                    <div class="media-totals">
                        ${Object.entries(vehicle.media_totals_found).map(([key, value]) => `
                            <div class="media-item">
                                <span class="media-label">${this.escapeHtml(key)}:</span>
                                <span class="media-value">${this.escapeHtml(String(value))}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            ${(vehicle.book_values_before_processing && Object.keys(vehicle.book_values_before_processing).length > 0) || 
              (vehicle.book_values_after_processing && Object.keys(vehicle.book_values_after_processing).length > 0) ? `
                <div class="modal-section">
                    <h4><i class="fas fa-calculator"></i> Book Values</h4>
                    ${this.renderBookValues(vehicle.book_values_before_processing, vehicle.book_values_after_processing)}
                </div>
            ` : ''}

            ${vehicle.no_fear_certificate ? `
                <div class="modal-section">
                    <h4><i class="fas fa-certificate"></i> NO FEAR Certification</h4>
                    <div class="certification-badge">
                        <i class="fas fa-award"></i>
                        <span>This vehicle has NO FEAR certification</span>
                    </div>
                    ${vehicle.no_fear_certificate_text ? `
                        <div class="certification-text">
                            ${this.escapeHtml(vehicle.no_fear_certificate_text)}
                        </div>
                    ` : ''}
                </div>
            ` : ''}

            ${errors.length > 0 ? `
                <div class="modal-section">
                    <h4><i class="fas fa-exclamation-triangle"></i> Processing Errors</h4>
                    <div class="error-list">
                        ${errors.map(error => `
                            <div class="error-item">
                                <i class="fas fa-exclamation-circle"></i>
                                <span>${this.escapeHtml(error)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        const modal = document.getElementById('vehicle-modal');
        const deleteBtn = document.getElementById('delete-vehicle-btn');
        
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        
        // Clear current vehicle and hide delete button
        this.currentVehicle = null;
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
    }

    changePage(direction) {
        this.currentPage += direction;
        this.loadVehicles();
        
        // Scroll to top of vehicles section
        document.querySelector('.vehicles-section').scrollIntoView({ behavior: 'smooth' });
    }

    clearSearch() {
        document.getElementById('search-input').value = '';
        this.currentSearch = '';
        this.currentPage = 1;
        this.loadVehicles();
        this.updateSearchClearButton();
    }

    async refreshData() {
        const refreshButton = document.querySelector('.btn-outline');
        const originalContent = refreshButton.innerHTML;
        
        refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshButton.disabled = true;
        
        try {
            await this.loadInitialData();
            this.showToast('Data refreshed successfully', 'success');
        } catch (error) {
            this.showToast('Failed to refresh data', 'error');
        } finally {
            refreshButton.innerHTML = originalContent;
            refreshButton.disabled = false;
        }
    }

    showLoadingState() {
        document.getElementById('loading-state').style.display = 'block';
        document.getElementById('error-state').style.display = 'none';
        document.getElementById('vehicles-grid').style.display = 'none';
    }

    hideLoadingState() {
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('vehicles-grid').style.display = 'grid';
    }

    showErrorState(message) {
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('error-state').style.display = 'block';
        document.getElementById('error-message').textContent = message;
        document.getElementById('vehicles-grid').style.display = 'none';
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${this.escapeHtml(message)}</span>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove toast after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
        
        // Click to dismiss
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }

    escapeHtml(text) {
        if (typeof text !== 'string') {
            return text;
        }
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    formatDescription(description) {
        if (!description) return '';
        // Preserve line breaks and basic formatting
        return this.escapeHtml(description).replace(/\n/g, '<br>');
    }

    renderBookValues(bookValuesBefore, bookValuesAfter) {
        const hasBeforeValues = bookValuesBefore && Object.keys(bookValuesBefore).length > 0;
        const hasAfterValues = bookValuesAfter && Object.keys(bookValuesAfter).length > 0;
        
        if (!hasBeforeValues && !hasAfterValues) {
            return '<div class="book-values-empty">No book value data available</div>';
        }

        let html = '<div class="book-values-container">';

        // If we have both before and after values, show them side by side with differences
        if (hasBeforeValues && hasAfterValues) {
            const beforeKeys = Object.keys(bookValuesBefore);
            const afterKeys = Object.keys(bookValuesAfter);
            const allKeys = [...new Set([...beforeKeys, ...afterKeys])].sort();

            html += `
                <div class="book-values-comparison">
                    <div class="book-values-header">
                        <div class="key-column">Category</div>
                        <div class="before-column">Before Processing</div>
                        <div class="after-column">After Processing</div>
                        <div class="difference-column">Difference</div>
                    </div>
                    <div class="book-values-rows">
            `;

            allKeys.forEach(key => {
                const beforeValue = bookValuesBefore[key];
                const afterValue = bookValuesAfter[key];
                const beforeNum = this.parseBookValue(beforeValue);
                const afterNum = this.parseBookValue(afterValue);
                const difference = (beforeNum !== null && afterNum !== null) ? afterNum - beforeNum : null;
                
                html += `
                    <div class="book-value-row">
                        <div class="book-value-key">${this.escapeHtml(key)}</div>
                        <div class="book-value-before">${this.formatBookValue(beforeValue)}</div>
                        <div class="book-value-after">${this.formatBookValue(afterValue)}</div>
                        <div class="book-value-difference ${difference > 0 ? 'positive' : difference < 0 ? 'negative' : 'neutral'}">
                            ${difference !== null ? this.formatBookValueDifference(difference) : 'N/A'}
                        </div>
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        } else {
            // Show only the available values
            const values = hasBeforeValues ? bookValuesBefore : bookValuesAfter;
            const title = hasBeforeValues ? 'Before Processing' : 'After Processing';
            
            html += `
                <div class="book-values-single">
                    <div class="book-values-title">${title}</div>
                    <div class="book-values-list">
            `;

            Object.entries(values).forEach(([key, value]) => {
                html += `
                    <div class="book-value-item">
                        <span class="book-value-label">${this.escapeHtml(key)}:</span>
                        <span class="book-value-value">${this.formatBookValue(value)}</span>
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    parseBookValue(value) {
        if (value === null || value === undefined || value === '') return null;
        if (typeof value === 'number') return value;
        if (typeof value === 'string') {
            // Remove currency symbols, commas, and whitespace
            const cleaned = value.replace(/[$,\s]/g, '');
            const parsed = parseFloat(cleaned);
            return isNaN(parsed) ? null : parsed;
        }
        return null;
    }

    formatBookValue(value) {
        if (value === null || value === undefined || value === '') return 'N/A';
        if (typeof value === 'number') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(value);
        }
        return this.escapeHtml(String(value));
    }

    formatBookValueDifference(difference) {
        if (difference === 0) return '$0';
        const formatted = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(Math.abs(difference));
        return difference > 0 ? `+${formatted}` : `-${formatted}`;
    }
}

// Global functions for HTML onclick handlers
let dashboard;

function refreshData() {
    dashboard.refreshData();
}

function clearSearch() {
    dashboard.clearSearch();
}

function changePage(direction) {
    dashboard.changePage(direction);
}

function closeModal() {
    dashboard.closeModal();
}

function loadVehicles() {
    dashboard.loadVehicles();
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
    dashboard = new VehicleDashboard();
    
    // Add CSS for modal sections and processing status
    const style = document.createElement('style');
    style.textContent = `
        .modal-section {
            margin-bottom: 25px;
        }
        
        .modal-section h4 {
            font-size: 16px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .modal-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .modal-field {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .modal-field label {
            font-size: 12px;
            font-weight: 600;
            color: #718096;
            text-transform: uppercase;
        }
        
        .modal-field value {
            font-size: 14px;
            color: #2d3748;
            font-weight: 500;
        }
        
        .modal-field .status.success {
            color: #38a169;
        }
        
        .modal-field .status.danger {
            color: #e53e3e;
        }
        
        .modal-field .status.muted {
            color: #a0aec0;
        }
        
        .modal-field .status.warning {
            color: #d97706;
        }
        
        .feature-list, .error-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .feature-item, .error-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            background: #f7fafc;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .feature-item i {
            color: #ed8936;
        }
        
        .error-item i {
            color: #e53e3e;
        }
        
        .description-content {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
            color: #4a5568;
        }
        
        .certification-badge {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: linear-gradient(135deg, #fef5e7, #fed7a1);
            border-radius: 8px;
            color: #744210;
            font-weight: 600;
            margin-bottom: 10px;
        }
        
        .certification-text {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #4a5568;
        }
        
        .no-results {
            grid-column: 1 / -1;
            background: white;
            padding: 60px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }
        
        /* Processing status styles */
        .vehicle-card.processing {
            border: 2px solid #f59e0b;
            box-shadow: 0 8px 30px rgba(245, 158, 11, 0.2);
            animation: processingPulse 2s infinite;
        }
        
        @keyframes processingPulse {
            0%, 100% { box-shadow: 0 8px 30px rgba(245, 158, 11, 0.2); }
            50% { box-shadow: 0 8px 30px rgba(245, 158, 11, 0.4); }
        }
        
        .processing-indicator {
            display: inline-block;
            margin-left: 8px;
            color: #f59e0b;
        }
        
        .no-build-data-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 6px;
            padding: 8px 12px;
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #92400e;
            font-weight: 500;
        }
        
        .no-build-data-warning i {
            color: #f59e0b;
        }

        /* Feature Category Formatting */
        .feature-category {
            margin-bottom: 16px;
        }

        .category-title {
            font-weight: 600;
            font-size: 14px;
            color: #1f2937;
            margin: 0 0 8px 0;
            padding: 0;
        }

        .feature-list {
            margin: 0;
            padding-left: 16px;
            list-style-type: disc;
        }

        .feature-list li {
            margin-bottom: 4px;
            font-size: 13px;
            line-height: 1.4;
            color: #4b5563;
        }

        /* Modal description content styling */
        .description-content .feature-category {
            margin-bottom: 20px;
        }

        .description-content .category-title {
            font-size: 15px;
            color: #111827;
            margin-bottom: 10px;
        }

        .description-content .feature-list li {
            font-size: 14px;
            margin-bottom: 6px;
        }
        
        .vehicle-status.warning {
            background: #fef3c7;
            color: #92400e;
        }
        
        .vehicle-status.muted {
            background: #f3f4f6;
            color: #6b7280;
        }
        
        .modal-field .status.warning {
            color: #d97706;
        }
    `;
    document.head.appendChild(style);
});