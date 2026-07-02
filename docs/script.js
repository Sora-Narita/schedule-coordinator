// ===== Global State =====
// API_BASE を Render バックエンドに設定（後で修正します）
let API_BASE = 'http://localhost:5000/api';
let currentEventId = null;
let currentUserName = '';
let selectedSlots = new Set();

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    // 環境に応じて API_BASE を設定
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
        // 本番環境では Render API を使用（URLは後で更新）
        API_BASE = 'https://YOUR_RENDER_API_URL/api';
    }
    
    loadEvents();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('eventSelect').addEventListener('change', onEventSelect);
    document.getElementById('userName').addEventListener('input', (e) => {
        currentUserName = e.target.value;
    });
}

// ===== Event Management =====
async function loadEvents() {
    try {
        const response = await fetch(`${API_BASE}/events`);
        const events = await response.json();
        
        const select = document.getElementById('eventSelect');
        select.innerHTML = '<option value="">-- 新規作成 または 既存から選択 --</option>';
        
        events.forEach(event => {
            const option = document.createElement('option');
            option.value = event.id;
            option.textContent = event.title;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load events:', error);
        alert('イベント読み込みエラー: バックエンドに接続できません');
    }
}

function onEventSelect() {
    const select = document.getElementById('eventSelect');
    const value = select.value;
    
    if (value === '') {
        document.getElementById('newEventForm').style.display = 'flex';
        document.getElementById('scheduleSection').style.display = 'none';
    } else {
        document.getElementById('newEventForm').style.display = 'none';
        currentEventId = parseInt(value);
        loadSchedule();
    }
}

async function createEvent() {
    const title = document.getElementById('eventTitle').value;
    const description = document.getElementById('eventDescription').value;
    
    if (!title) {
        alert('イベント名を入力してください');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description })
        });
        
        const event = await response.json();
        currentEventId = event.id;
        
        document.getElementById('eventTitle').value = '';
        document.getElementById('eventDescription').value = '';
        document.getElementById('newEventForm').style.display = 'none';
        
        await loadEvents();
        document.getElementById('eventSelect').value = event.id;
        
        loadSchedule();
    } catch (error) {
        console.error('Failed to create event:', error);
        alert('イベント作成に失敗しました');
    }
}

// ===== Schedule Management =====
async function loadSchedule() {
    try {
        const response = await fetch(`${API_BASE}/events/${currentEventId}`);
        const event = await response.json();
        
        document.getElementById('selectedEventTitle').textContent = event.title;
        document.getElementById('scheduleSection').style.display = 'block';
        
        renderScheduleGrid(event);
        updateBestSlot();
    } catch (error) {
        console.error('Failed to load schedule:', error);
    }
}

function renderScheduleGrid(event) {
    const grid = document.getElementById('scheduleGrid');
    grid.innerHTML = '';
    
    if (event.dates.length === 0) {
        grid.innerHTML = '<p style="text-align: center; color: #999;">日付がまだ追加されていません。"+日付を追加"ボタンから追加してください。</p>';
        return;
    }
    
    event.dates.forEach(scheduleDate => {
        const dateRow = document.createElement('div');
        dateRow.className = 'date-row';
        
        const dateStr = new Date(scheduleDate.date).toLocaleDateString('ja-JP', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        dateRow.innerHTML = `<div class="date-header">${dateStr}</div>`;
        
        const slotsContainer = document.createElement('div');
        slotsContainer.className = 'time-slots-container';
        
        // Create time slots for full day (0-23 hours)
        for (let hour = 0; hour < 24; hour++) {
            const existingSlot = scheduleDate.time_slots.find(s => s.hour === hour);
            const slot = createTimeSlotElement(scheduleDate.id, existingSlot);
            slotsContainer.appendChild(slot);
        }
        
        dateRow.appendChild(slotsContainer);
        grid.appendChild(dateRow);
    });
}

function createTimeSlotElement(scheduleDateId, timeSlot) {
    const slot = document.createElement('div');
    slot.className = 'time-slot';
    
    if (!timeSlot) {
        // Empty slot - create placeholder
        const hour = 0;
        slot.innerHTML = `
            <div class="time-hour">${String(hour).padStart(2, '0')}:00</div>
        `;
        return slot;
    }
    
    const hour = timeSlot.hour;
    const voteCount = timeSlot.votes_count || 0;
    const userVoted = timeSlot.voters.includes(currentUserName);
    
    slot.innerHTML = `
        <div class="time-hour">${String(hour).padStart(2, '0')}:00</div>
        <div class="vote-count">${voteCount} 票</div>
    `;
    
    slot.dataset.timeSlotId = timeSlot.id;
    
    if (userVoted) {
        slot.classList.add('selected');
        selectedSlots.add(timeSlot.id);
    }
    
    // Setup drag and click events
    setupSlotInteraction(slot);
    
    return slot;
}

function setupSlotInteraction(slot) {
    slot.addEventListener('click', () => toggleSlot(slot));
    
    // Drag events for visual feedback
    slot.addEventListener('dragstart', (e) => {
        slot.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    });
    
    slot.addEventListener('dragend', () => {
        slot.classList.remove('dragging');
    });
}

async function toggleSlot(slot) {
    const timeSlotId = slot.dataset.timeSlotId;
    
    if (!timeSlotId) {
        alert('まずユーザー名を入力してください');
        return;
    }
    
    if (!currentUserName) {
        alert('ユーザー名を入力してください');
        return;
    }
    
    try {
        if (slot.classList.contains('selected')) {
            // Remove vote
            await fetch(`${API_BASE}/time-slots/${timeSlotId}/unvote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voter_name: currentUserName })
            });
            slot.classList.remove('selected');
            selectedSlots.delete(parseInt(timeSlotId));
        } else {
            // Add vote
            await fetch(`${API_BASE}/time-slots/${timeSlotId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voter_name: currentUserName })
            });
            slot.classList.add('selected');
            selectedSlots.add(parseInt(timeSlotId));
        }
        
        // Refresh schedule to show updated vote counts
        await loadSchedule();
    } catch (error) {
        console.error('Failed to toggle vote:', error);
        alert('投票に失敗しました');
    }
}

// ===== Date Management =====
function addNewDate() {
    document.getElementById('dateModal').style.display = 'flex';
}

function closeDateModal() {
    document.getElementById('dateModal').style.display = 'none';
    document.getElementById('dateInput').value = '';
}

async function confirmDate() {
    const dateInput = document.getElementById('dateInput').value;
    
    if (!dateInput) {
        alert('日付を選択してください');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/events/${currentEventId}/dates`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: dateInput })
        });
        
        const scheduleDate = await response.json();
        
        // Add time slots for this date (0-23)
        const hours = Array.from({ length: 24 }, (_, i) => i);
        await fetch(`${API_BASE}/schedule-dates/${scheduleDate.id}/time-slots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hours })
        });
        
        closeDateModal();
        await loadSchedule();
    } catch (error) {
        console.error('Failed to add date:', error);
        alert('日付追加に失敗しました');
    }
}

// ===== Stats =====
async function updateBestSlot() {
    try {
        const response = await fetch(`${API_BASE}/events/${currentEventId}/best-slot`);
        const result = await response.json();
        
        const bestSlotDiv = document.getElementById('bestSlot');
        
        if (result.best_slots.length === 0) {
            bestSlotDiv.innerHTML = '<p>まだ投票がありません</p>';
            return;
        }
        
        let html = '';
        result.best_slots.forEach(slot => {
            const hour = String(slot.hour).padStart(2, '0');
            html += `
                <div class="best-slot-item">
                    <span>${hour}:00 - ${String(slot.hour + 1).padStart(2, '0')}:00</span>
                    <span class="slot-votes">${result.max_votes} 票</span>
                </div>
            `;
        });
        
        bestSlotDiv.innerHTML = html;
    } catch (error) {
        console.error('Failed to update best slot:', error);
    }
}

// Close modal on click outside
window.addEventListener('click', (event) => {
    const modal = document.getElementById('dateModal');
    if (event.target === modal) {
        closeDateModal();
    }
});
