// API Client - Communication with Backend

class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.checkConnection();
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            if (response.ok) {
                this.updateStatus('success');
                console.log('✅ API Connected:', this.baseURL);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            this.updateStatus('error');
            console.warn('❌ API Connection Failed:', error);
        }
    }

    updateStatus(status) {
        const indicator = document.getElementById('system-status');
        if (indicator) {
            indicator.className = `status-indicator status-${status}`;
            indicator.innerHTML = status === 'success' ? 
                '● API Connected' : 
                '○ API Disconnected';
        }
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            // Check if response is empty (204 No Content)
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    // Cards CRUD
    async getCards() {
        return this.request('/cards');
    }

    async getCardById(cardId) {
        return this.request(`/cards/${cardId}`);
    }

    async createCard(cardData) {
        return this.request('/cards', {
            method: 'POST',
            body: JSON.stringify(cardData),
        });
    }

    async updateCard(cardId, cardData) {
        return this.request(`/cards/${cardId}`, {
            method: 'PATCH',
            body: JSON.stringify(cardData),
        });
    }

    async deleteCard(cardId) {
        return this.request(`/cards/${cardId}`, {
            method: 'DELETE',
        });
    }

    // Card Logs
    async getCardLogs(cardId) {
        return this.request(`/cards/${cardId}/logs`);
    }

    async createLogEntry(logData) {
        return this.request('/logs', {
            method: 'POST',
            body: JSON.stringify(logData),
        });
    }

    // Board Queries
    async getReadyCards() {
        return this.request('/cards/ready');
    }

    async getInProgressCards() {
        return this.request('/cards/in-progress');
    }

    // Statistics
    async getStats() {
        return this.request('/stats');
    }

    // Supervisor Actions
    async runSupervisor() {
        return this.request('/supervisor/run', {
            method: 'POST',
        });
    }

    async getActiveRuns() {
        return this.request('/supervisor/active-runs');
    }

    async closeActiveRun(runId) {
        return this.request(`/supervisor/active-runs/${runId}/close`, {
            method: 'POST',
        });
    }
}

// Create global API client instance
const api = new APIClient();

// Update status periodically (every 30 seconds)
setInterval(() => api.checkConnection(), 30000);
