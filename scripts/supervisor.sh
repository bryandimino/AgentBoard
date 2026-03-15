#!/bin/bash

# Agent Board Supervisor Loop
# This script inspects board state and spawns subagents for READY cards

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/supervisor.log"
API_BASE="${API_BASE:-http://localhost:8001/api}"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S CST')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

log "🔄 Supervisor loop started"

# Fetch board state and statistics
fetch_stats() {
    log "📊 Fetching board statistics..."
    curl -s "${API_BASE}/stats" 2>/dev/null || echo '{"total":0,"ready":0,"in_progress":0,"done":0}'
}

fetch_ready_cards() {
    log "📋 Fetching READY cards for assignment..."
    curl -s "${API_BASE}/cards/ready" 2>/dev/null || echo '[]'
}

fetch_in_progress_cards() {
    log "🔍 Fetching IN_PROGRESS cards..."
    curl -s "${API_BASE}/cards/in-progress" 2>/dev/null || echo '[]'
}

# Analyze board state and decide next action
analyze_board() {
    local stats=$1
    
    local total=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))")
    local ready=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('ready', 0))")
    local in_progress=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('in_progress', 0))")
    
    log "📈 Board State: Total=$total, READY=$ready, IN_PROGRESS=$in_progress"
    
    # Decision logic (WIP limit = 1 for MVP)
    if [ "$in_progress" -gt 0 ]; then
        local decision="continue_existing"
        local reason="Agent already in progress with existing work"
    elif [ "$ready" -gt 0 ]; then
        local decision="start_new"
        local reason="Ready card available for assignment"
    else
        local decision="no_work"
        local reason="No actionable work within WIP limits"
    fi
    
    log "🤖 Decision: $decision - $reason"
    
    echo "{\"decision\": \"$decision\", \"reason\": \"$reason\"}"
}

# Spawn subagent for a card
spawn_subagent() {
    local card_id=$1
    local card_title=$2
    
    log "🚀 Spawning subagent for card #$card_id: $card_title"
    
    # Use OpenClaw sessions_spawn to create agent session
    openclaw sessions_spawn \
        --task "Execute work on Agent Board card #$card_id: $card_title. Follow acceptance criteria and update board after completion." \
        --label "board-card-$card_id-$(date +%Y%m%d-%H%M%S)" \
        --mode session \
        --runtime acp \
        --cwd "$PROJECT_ROOT" \
        2>&1 | tee -a "$LOG_FILE"
    
    local result=$?
    
    if [ $result -eq 0 ]; then
        log "✅ Subagent spawned successfully for card #$card_id"
        echo "{\"success\": true, \"card_id\": $card_id}"
    else
        log "❌ Failed to spawn subagent for card #$card_id"
        echo "{\"success\": false, \"card_id\": $card_id}"
    fi
}

# Main supervisor loop logic
run_supervisor_loop() {
    # Fetch current board state
    local stats=$(fetch_stats)
    local decision_result=$(analyze_board "$stats")
    
    local decision=$(echo "$decision_result" | python3 -c "import sys, json; print(json.load(sys.stdin).get('decision', 'unknown'))")
    local reason=$(echo "$decision_result" | python3 -c "import sys, json; print(json.load(sys.stdin).get('reason', ''))")
    
    # Log supervisor decision to API
    log "📝 Recording supervisor decision in execution logs..."
    curl -s -X POST "${API_BASE}/logs" \
        -H "Content-Type: application/json" \
        -d "{\"action\": \"supervisor_loop\", \"message\": \"Supervisor: $decision - $reason\"}" \
        >> "$LOG_FILE" 2>&1 || log "⚠️ Could not log decision (API may be unavailable)"
    
    case $decision in
        continue_existing)
            # Get first in-progress card and update its status
            log "🔄 Continuing existing work..."
            ;;
            
        start_new)
            # Get READY cards and assign highest priority one
            local ready_cards=$(fetch_ready_cards)
            
            if echo "$ready_cards" | python3 -c "import sys, json; cards = json.load(sys.stdin); exit(0 if len(cards) > 0 else 1)" 2>/dev/null; then
                # Sort by priority and get first card
                local card_id=$(echo "$ready_cards" | python3 -c "import sys, json; cards = sorted(json.load(sys.stdin), key=lambda x: (x.get('priority', 99), x.get('created_at'))); print(cards[0].get('id'))")
                local card_title=$(echo "$ready_cards" | python3 -c "import sys, json; cards = sorted(json.load(sys.stdin), key=lambda x: (x.get('priority', 99), x.get('created_at'))); print(cards[0].get('title'))")
                
                log "🎯 Selected READY card #$card_id: $card_title"
                
                # Update card to IN_PROGRESS
                curl -s -X PATCH "${API_BASE}/cards/$card_id" \
                    -H "Content-Type: application/json" \
                    -d '{"status": "IN_PROGRESS"}' \
                    >> "$LOG_FILE" 2>&1 || log "⚠️ Could not update card status"
                
                # Spawn subagent
                spawn_subagent "$card_id" "$card_title"
            else
                log "⚠️ No READY cards found, despite stats indicating some exist"
            fi
            ;;
            
        no_work)
            log "✅ No actionable work - all tasks complete or blocked"
            echo "No work to do"
            ;;
    esac
    
    log "🏁 Supervisor loop completed"
}

# Main execution
run_supervisor_loop
