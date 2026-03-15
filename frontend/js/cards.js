/**
 * Agent Board - Card Management & Interactions
 */

let currentCardId = null;

function openNewCardModal() {
    document.getElementById('modal-new-card').style.display = 'flex';
}

function closeNewCardModal() {
    document.getElementById('modal-new-card').style.display = 'none';
    document.getElementById('form-new-card').reset();
}

async function handleSubmitNewCard(e) {
    e.preventDefault();

    const cardData = {
        title: document.getElementById('input-title').value,
        type: document.getElementById('select-type').value,
        priority: parseInt(document.getElementById('input-priority').value),
        owner: document.getElementById('input-owner').value || null,
        role: document.getElementById('input-role').value || null
    };

    try {
        const result = await api.createCard(cardData);
        showToast('Card created successfully', 'success');
        closeNewCardModal();
        loadBoard();
    } catch (error) {
        showToast('Failed to create card: ' + error.message, 'error');
        console.error(error);
    }
}

async function openCardDetail(cardId) {
    try {
        currentCardId = cardId;
        
        // Get card details
        const card = await api.getCard(cardId);
        const stats = await api.getCardStats(cardId);
        
        document.getElementById('modal-card-title').textContent = `Card #${card.id}: ${card.title}`;
        
        const priorityLabels = {
            0: '🔴 Critical (P0)',
            1: '🟠 High (P1)',
            2: '🟡 Medium-Low (P2)',
            3: '⚪ Low (P3)'
        };

        const detailHtml = `
            <div style="margin-bottom: 1.5rem;">
                <h3>Status</h3>
                <span class="status-badge" style="background-color: var(--card-${card.status.toLowerCase()}); color: ${card.status === 'REVIEW' ? '#000' : '#fff'}">
                    ${getStatusLabel(card.status)}
                </span>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3>Priority</h3>
                <p>${priorityLabels[card.priority] || 'Unknown'}</p>
            </div>
            
            ${card.owner ? `
            <div style="margin-bottom: 1.5rem;">
                <h3>Owner</h3>
                <p>@${card.owner}</p>
            </div>
            ` : ''}
            
            ${card.role ? `
            <div style="margin-bottom: 1.5rem;">
                <h3>Role</h3>
                <p>${card.role}</p>
            </div>
            ` : ''}
            
            ${card.acceptance_criteria ? `
            <div style="margin-bottom: 1.5rem;">
                <h3>Acceptance Criteria</h3>
                <pre style="background-color: var(--bg-primary); padding: 0.75rem; border-radius: 4px; overflow-x: auto;">${escapeHtml(card.acceptance_criteria)}</pre>
            </div>
            ` : ''}
            
            ${card.blockers ? `
            <div style="margin-bottom: 1.5rem;">
                <h3>Blockers</h3>
                <p style="color: var(--danger); font-style: italic;">${escapeHtml(card.blockers)}</p>
            </div>
            ` : ''}
            
            ${card.next_step ? `
            <div style="margin-bottom: 1.5rem;">
                <h3>Next Step</h3>
                <p>${escapeHtml(card.next_step)}</p>
            </div>
            ` : ''}
            
            <div style="margin-bottom: 1.5rem;">
                <h3>Timeline</h3>
                <ul style="list-style: none; padding-left: 0;">
                    <li><strong>Created:</strong> ${new Date(card.created_at).toLocaleString()}</li>
                    ${card.started_at ? `<li><strong>Started:</strong> ${new Date(card.started_at).toLocaleString()}</li>` : ''}
                    ${card.completed_at ? `<li><strong>Completed:</strong> ${new Date(card.completed_at).toLocaleString()}</li>` : ''}
                </ul>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3>Activity Stats</h3>
                <p>Total actions: ${stats.logs_count}</p>
                <p>${card.status === 'IN_PROGRESS' && stats.duration_seconds ? `Time elapsed: ${Math.round(stats.duration_seconds / 60)} minutes` : ''}</p>
            </div>

            <button class="btn btn-secondary" id="btn-show-logs" style="width: 100%; margin-bottom: 1rem;">View Execution Logs</button>
            
            ${card.status !== 'DONE' ? `
            <button class="btn btn-primary" onclick="transitionCardStatus(${card.id}, 'READY')">Move to Ready</button>
            <button class="btn btn-accent" onclick="transitionCardStatus(${card.id}, 'IN_PROGRESS')">Start Work</button>
            ` : ''}
            
            ${card.status !== 'BACKLOG' ? `
            <button class="btn btn-secondary" onclick="transitionCardStatus(${card.id}, 'BACKLOG')">Move to Backlog</button>
            ` : ''}

            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--bg-card);">
                <h3>Danger Zone</h3>
                <button class="btn btn-secondary" style="color: var(--danger);" onclick="deleteCard(${card.id})">Delete Card</button>
            </div>
        `;

        document.getElementById('card-detail-content').innerHTML = detailHtml;
        
        // Add log button handler
        document.getElementById('btn-show-logs')?.addEventListener('click', () => showCardLogs(cardId));
        
        document.getElementById('modal-card-detail').style.display = 'flex';

    } catch (error) {
        showToast('Failed to load card details: ' + error.message, 'error');
        console.error(error);
    }
}

function closeCardDetail() {
    document.getElementById('modal-card-detail').style.display = 'none';
    currentCardId = null;
}

async function showCardLogs(cardId) {
    try {
        const logsData = await api.getCardLogs(cardId);
        
        if (!logsData.logs || logsData.logs.length === 0) {
            document.getElementById('logs-container').innerHTML = '<p>No execution logs yet.</p>';
        } else {
            const logsHtml = logsData.logs.map(log => `
                <div class="log-entry">
                    <div class="log-time">${new Date(log.created_at).toLocaleString()}</div>
                    <div class="log-message"><strong>${log.action}:</strong> ${escapeHtml(log.message)}</div>
                </div>
            `).join('');
            
            document.getElementById('logs-container').innerHTML = logsHtml;
        }
        
        document.getElementById('modal-logs').style.display = 'flex';

    } catch (error) {
        showToast('Failed to load logs: ' + error.message, 'error');
        console.error(error);
    }
}

function closeLogs() {
    document.getElementById('modal-logs').style.display = 'none';
}

async function transitionCardStatus(cardId, newStatus) {
    try {
        await api.updateCard(cardId, { status: newStatus });
        showToast(`Card moved to ${getStatusLabel(newStatus)}`, 'success');
        closeCardDetail();
        loadBoard();
    } catch (error) {
        showToast('Failed to update card status: ' + error.message, 'error');
        console.error(error);
    }
}

async function deleteCard(cardId) {
    if (!confirm(`Are you sure you want to delete card #${cardId}? This action cannot be undone.`)) {
        return;
    }

    try {
        await api.deleteCard(cardId);
        showToast('Card deleted successfully', 'success');
        closeCardDetail();
        loadBoard();
    } catch (error) {
        showToast('Failed to delete card: ' + error.message, 'error');
        console.error(error);
    }
}

// Initialize event handlers
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-new-card')?.addEventListener('click', openNewCardModal);
    document.getElementById('btn-cancel-create')?.addEventListener('click', closeNewCardModal);
    document.getElementById('form-new-card')?.addEventListener('submit', handleSubmitNewCard);
    document.getElementById('btn-close-detail')?.addEventListener('click', closeCardDetail);
    document.getElementById('btn-close-logs')?.addEventListener('click', closeLogs);
    document.getElementById('btn-refresh')?.addEventListener('click', loadBoard);
});
