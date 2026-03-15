// Agent Board - Main Application Logic

class AgentBoard {
    constructor() {
        this.cards = [];
        this.currentModalCardId = null;
        this.init();
    }

    async init() {
        console.log('🚀 Agent Board initializing...');
        
        // Load cards on startup
        await this.loadCards();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initial stats update
        await this.updateStats();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (navigator.onLine) {
                this.loadCards().then(() => this.updateStats());
            }
        }, 30000);

        console.log('✅ Agent Board ready');
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('btn-refresh')?.addEventListener('click', () => {
            this.loadCards().then(() => this.updateStats());
            this.showToast('Board refreshed', 'success');
        });

        // Supervisor run button
        document.getElementById('btn-supervisor-run')?.addEventListener('click', () => {
            this.runSupervisorLoop();
        });

        // Add card buttons in columns
        document.querySelectorAll('.btn-add-card').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const status = e.target.dataset.status;
                this.openCardModal({ status: status || 'BACKLOG' });
            });
        });

        // Modal close functionality
        document.querySelectorAll('.modal-backdrop, .modal-dialog').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.classList.contains('modal-backdrop')) {
                    this.closeModal('card-modal');
                }
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal('card-modal');
            }
        });
    }

    async loadCards() {
        try {
            const cards = await api.getCards();
            
            // Sort by priority first, then created_at
            this.cards = cards.sort((a, b) => {
                if (a.priority !== b.priority) return a.priority - b.priority;
                return new Date(a.created_at) - new Date(b.created_at);
            });

            // Render board with all columns
            this.renderBoard();
            
            return cards;
        } catch (error) {
            console.error('Failed to load cards:', error);
            this.showToast(`Error loading cards: ${error.message}`, 'error');
            return [];
        }
    }

    renderBoard() {
        // Clear all columns
        Object.values(document.querySelectorAll('.column-cards')).forEach(col => {
            col.innerHTML = '';
        });

        // Group cards by status
        const cardsByStatus = {};
        this.cards.forEach(card => {
            if (!cardsByStatus[card.status]) {
                cardsByStatus[card.status] = [];
            }
            cardsByStatus[card.status].push(card);
        });

        // Render cards to each column
        for (const [status, cards] of Object.entries(cardsByStatus)) {
            const containerId = `column-${status.toLowerCase().replace('_', '-')}`;
            const container = document.getElementById(containerId);
            
            if (container) {
                container.innerHTML = '';

                // Add empty state message if no cards
                if (cards.length === 0) {
                    container.innerHTML = '<div class="card-empty-state">No cards in this column</div>';
                }

                // Render each card
                cards.forEach(card => {
                    const cardElement = this.createCardElement(card);
                    container.appendChild(cardElement);
                });

                // Update count badge
                const countEl = container.parentElement.querySelector('.card-count');
                if (countEl) {
                    countEl.textContent = cards.length;
                    countEl.style.display = 'inline-block';
                }
            }
        }

        // Update last refresh timestamp
        const now = new Date();
        document.getElementById('last-update').textContent = 
            `Last update: ${now.toLocaleTimeString()}`;
    }

    createCardElement(card) {
        const el = document.createElement('div');
        el.className = 'card';
        el.setAttribute('data-id', card.id);
        el.setAttribute('data-priority', card.priority);
        el.setAttribute('data-type', card.type);
        el.setAttribute('data-status', card.status);

        // Format priority label
        const priorityLabels = {
            0: 'Critical',
            1: 'High',
            2: 'Medium',
            3: 'Low'
        };

        // Format status label
        const statusLabels = {
            'BACKLOG': 'Backlog',
            'READY': 'Ready',
            'IN_PROGRESS': 'In Progress',
            'BLOCKED': 'Blocked',
            'REVIEW': 'Review',
            'DONE': 'Done'
        };

        el.innerHTML = `
            <div class="card-header">
                <span class="card-badge" data-type="${card.type}">${card.type}</span>
                <span class="card-status" data-status="${card.status}">${statusLabels[card.status] || card.status}</span>
            </div>
            <div class="card-body">
                <h3 class="card-title">${this.escapeHtml(card.title)}</h3>
                <p class="card-criteria">${this.escapeHtml(card.acceptance_criteria)}</p>
            </div>
            <div class="card-footer">
                <div class="card-meta">
                    ${card.owner ? `<span class="card-meta-item">👤 ${this.escapeHtml(card.owner)}</span>` : ''}
                    <span class="card-meta-item">Priority: ${priorityLabels[card.priority]}</span>
                </div>
                <div class="card-actions">
                    <button class="action-btn" onclick="openCardModal(${card.id})">Edit</button>
                </div>
            </div>
        `;

        // Make card clickable to edit
        el.addEventListener('click', (e) => {
            if (!e.target.classList.contains('action-btn')) {
                openCardModal(card.id);
            }
        });

        return el;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    async updateStats() {
        try {
            const stats = await api.getStats();
            
            // Update header stats
            document.getElementById('stats-total').textContent = `Total: ${stats.total}`;
            document.getElementById('stats-ready').textContent = `Ready: ${stats.ready}`;
            document.getElementById('stats-in-progress').textContent = `In Progress: ${stats.in_progress}`;

            // Update sidebar stats
            document.getElementById('sidebar-total').textContent = stats.total;
            document.getElementById('sidebar-ready').textContent = stats.ready;
            document.getElementById('sidebar-in-progress').textContent = stats.in_progress;
            document.getElementById('sidebar-done').textContent = stats.done || 0;

        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }

    async runSupervisorLoop() {
        try {
            const btn = document.getElementById('btn-supervisor-run');
            btn.disabled = true;
            btn.textContent = '⏳ Running...';

            const result = await api.runSupervisor();
            
            this.showToast(`Supervisor completed: ${result.decision}`, 'success');
            setTimeout(() => this.loadCards(), 1000); // Refresh board
            
        } catch (error) {
            console.error('Supervisor run failed:', error);
            this.showToast(`Error: ${error.message}`, 'error');
        } finally {
            const btn = document.getElementById('btn-supervisor-run');
            btn.disabled = false;
            btn.textContent = '▶ Run Supervisor Loop';
        }
    }

    openCardModal(cardIdOrData) {
        const form = document.getElementById('card-form');
        const title = document.getElementById('modal-title');
        const deleteBtn = document.getElementById('btn-delete-card');
        const modal = document.getElementById('card-modal');

        // Clear form first
        form.reset();
        
        if (typeof cardIdOrData === 'number') {
            // Edit existing card
            this.currentModalCardId = cardIdOrData;
            title.textContent = 'Edit Card';
            deleteBtn.classList.remove('hidden');

            // Load card data
            api.getCardById(cardIdOrData)
                .then(card => {
                    document.getElementById('card-id').value = card.id || '';
                    document.getElementById('card-title').value = card.title;
                    document.getElementById('card-type').value = card.type;
                    document.getElementById('card-priority').value = card.priority;
                    document.getElementById('card-owner').value = card.owner || '';
                    document.getElementById('card-status').value = card.status;
                    document.getElementById('card-role').value = card.role || '';
                    document.getElementById('card-acceptance').value = card.acceptance_criteria;
                    document.getElementById('card-next-step').value = card.next_step || '';
                    document.getElementById('card-blockers').value = card.blockers || '';
                })
                .catch(err => {
                    console.error('Failed to load card:', err);
                    this.showToast(`Error loading card: ${err.message}`, 'error');
                });

        } else {
            // Create new card
            this.currentModalCardId = null;
            title.textContent = 'Create New Card';
            deleteBtn.classList.add('hidden');

            if (cardIdOrData && cardIdOrData.status) {
                document.getElementById('card-status').value = cardIdOrData.status;
            }
        }

        // Show modal
        modal.classList.remove('hidden');
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('hidden');
        this.currentModalCardId = null;
    }

    async handleCardSubmit(event) {
        event.preventDefault();

        const form = event.target;
        const cardData = {
            title: form.title.value,
            type: form.type.value,
            priority: parseInt(form.priority.value),
            owner: form.owner.value || null,
            status: form.status.value,
            role: form.role.value || null,
            acceptance_criteria: form.acceptance.value,
            next_step: form.nextStep.value || null,
            blockers: form.blockers.value || null,
        };

        try {
            let result;
            
            if (this.currentModalCardId) {
                // Update existing card
                result = await api.updateCard(this.currentModalCardId, cardData);
                this.showToast('Card updated successfully');
            } else {
                // Create new card
                result = await api.createCard(cardData);
                this.showToast('Card created successfully');
            }

            // Close modal and refresh
            this.closeModal('card-modal');
            await this.loadCards();
            await this.updateStats();

        } catch (error) {
            console.error('Failed to save card:', error);
            this.showToast(`Error: ${error.message}`, 'error');
        }
    }

    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.agentBoard = new AgentBoard();
});

// Global helper functions for onclick handlers
function openCardModal(cardIdOrData) {
    if (window.agentBoard) {
        window.agentBoard.openCardModal(cardIdOrData);
    }
}

function closeModal(modalId) {
    if (window.agentBoard) {
        window.agentBoard.closeModal(modalId);
    }
}
