/**
 * Agent Board - Board Rendering & Events
 */

const STATUS_CONFIG = {
    'BACKLOG': { color: 'gray', label: 'Backlog' },
    'READY': { color: 'cyan', label: 'Ready' },
    'IN_PROGRESS': { color: 'blue', label: 'In Progress' },
    'BLOCKED': { color: 'red', label: 'Blocked' },
    'REVIEW': { color: 'yellow', label: 'Review' },
    'DONE': { color: 'green', label: 'Done' }
};

let currentBoardData = [];

async function loadBoard() {
    try {
        const board = await api.getBoard();
        renderBoard(board);
        currentBoardData = board;
    } catch (error) {
        showToast('Failed to load board: ' + error.message, 'error');
        console.error('Load board error:', error);
    }
}

function renderBoard(board) {
    const container = document.getElementById('board');
    if (!board || !Array.isArray(board)) {
        container.innerHTML = '<div class="loading">No board data</div>';
        return;
    }

    container.innerHTML = '';

    board.forEach(column => {
        const columnEl = createColumnElement(column);
        container.appendChild(columnEl);
    });

    // Sort columns by order
    reorderColumns();
}

function createColumnElement(column) {
    const status = column.name;
    const cards = column.cards || [];
    
    const colDiv = document.createElement('div');
    colDiv.className = `column column-${status.toLowerCase()}`;
    colDiv.dataset.status = status;
    colDiv.dataset.columnId = column.id;

    // Header
    const header = document.createElement('div');
    header.className = 'column-header';
    header.innerHTML = `
        <span>${getStatusLabel(status)}</span>
        <span class="card-count">${cards.length}</span>
    `;
    colDiv.appendChild(header);

    // Cards container
    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'column-cards';
    
    if (cards.length === 0) {
        cardsContainer.innerHTML = '<div class="empty-column">No cards</div>';
    } else {
        cards.forEach(card => {
            cardsContainer.appendChild(createCardElement(card));
        });
    }
    
    colDiv.appendChild(cardsContainer);

    // Drag events for reordering (future enhancement)
    setupDropZone(cardsContainer, status);

    return colDiv;
}

function createCardElement(card) {
    const cardDiv = document.createElement('div');
    cardDiv.className = `card card-priority-${card.priority}`;
    cardDiv.dataset.cardId = card.id;
    
    // Priority label
    const priorityLabels = {
        0: '🔴 Critical',
        1: '🟠 High',
        2: '🟡 Medium',
        3: '⚪ Low'
    };

    cardDiv.innerHTML = `
        <div class="card-header">
            <span class="card-title">${escapeHtml(card.title)}</span>
            <span class="card-type">${card.type}</span>
        </div>
        <div class="card-meta">
            <span class="card-priority">${priorityLabels[card.priority] || 'Unknown'}</span>
            ${card.owner ? `<span class="card-owner">@${escapeHtml(card.owner)}</span>` : ''}
        </div>
        ${card.next_step ? `
        <div class="card-next-step">
            Next: ${escapeHtml(card.next_step)}
        </div>
        ` : ''}
    `;

    // Click to open details
    cardDiv.addEventListener('click', () => openCardDetail(card.id));

    return cardDiv;
}

function getStatusLabel(status) {
    const config = STATUS_CONFIG[status];
    return config ? config.label : status;
}

function reorderColumns() {
    const container = document.getElementById('board');
    const columns = Array.from(container.querySelectorAll('.column'));
    
    columns.sort((a, b) => {
        const aId = parseInt(a.dataset.columnId);
        const bId = parseInt(b.dataset.columnId);
        return aId - bId;
    });

    columns.forEach(col => container.appendChild(col));
}

function setupDropZone(container, status) {
    container.addEventListener('dragover', (e) => {
        e.preventDefault();
        container.style.backgroundColor = 'rgba(233, 69, 96, 0.1)';
    });

    container.addEventListener('dragleave', () => {
        container.style.backgroundColor = '';
    });

    container.addEventListener('drop', async (e) => {
        e.preventDefault();
        container.style.backgroundColor = '';
        
        const cardId = parseInt(e.dataTransfer.getData('text/plain'));
        if (cardId && status !== 'DONE') {
            try {
                await api.updateCard(cardId, { status: status });
                loadBoard(); // Reload to show updated state
                showToast(`Card moved to ${getStatusLabel(status)}`, 'success');
            } catch (error) {
                showToast('Failed to update card status', 'error');
                console.error(error);
            }
        }
    });

    // Store dragged ID
    container.addEventListener('dragstart', (e) => {
        const card = e.target.closest('.card');
        if (card) {
            e.dataTransfer.setData('text/plain', card.dataset.cardId);
        }
    });
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadBoard();
    
    // Auto-refresh every 30 seconds
    setInterval(loadBoard, 30000);
});
