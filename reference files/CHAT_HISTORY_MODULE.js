// ============================================
// CHAT HISTORY DROPDOWN MODULE
// ============================================
// Add this JavaScript to your dashboard.html

let currentConversationId = null;
let conversations = [];

// Load all conversations from API
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations', {
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Failed to load conversations');
        
        const data = await response.json();
        conversations = data.conversations || [];
        
        updateHistoryDropdown();
        
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Update the history dropdown menu with conversations
function updateHistoryDropdown() {
    const dropdown = document.getElementById('historyDropdownMenu');
    if (!dropdown) return;
    
    if (conversations.length === 0) {
        dropdown.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #6b7280;">
                <p>No chat history yet</p>
                <p style="font-size: 12px; margin-top: 5px;">Start a conversation to see it here!</p>
            </div>
        `;
        return;
    }
    
    // Group conversations by date
    const grouped = groupConversationsByDate(conversations);
    
    let html = '<div style="max-height: 400px; overflow-y: auto;">';
    
    // Add "New Chat" button at top
    html += `
        <div class="history-item history-new-chat" onclick="startNewChat()">
            <div class="history-icon">✨</div>
            <div class="history-content">
                <div class="history-title">New Chat</div>
                <div class="history-time">Start fresh conversation</div>
            </div>
        </div>
        <div style="border-bottom: 1px solid #e5e7eb; margin: 10px 0;"></div>
    `;
    
    // Add conversations by date group
    for (const [groupName, convs] of Object.entries(grouped)) {
        html += `<div class="history-group-label">${groupName}</div>`;
        
        convs.forEach(conv => {
            const isActive = currentConversationId === conv.id;
            html += `
                <div class="history-item ${isActive ? 'active' : ''}" onclick="loadConversation(${conv.id})">
                    <div class="history-icon">${getAgentIcon(conv.agent)}</div>
                    <div class="history-content">
                        <div class="history-title">${conv.title}</div>
                        <div class="history-time">${formatTime(conv.updated_at)}</div>
                    </div>
                    <button class="history-delete" onclick="deleteConversation(${conv.id}, event)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                        </svg>
                    </button>
                </div>
            `;
        });
    }
    
    html += '</div>';
    dropdown.innerHTML = html;
}

// Group conversations by date (Today, Yesterday, Last 7 Days, etc.)
function groupConversationsByDate(conversations) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    
    const groups = {
        'Today': [],
        'Yesterday': [],
        'Last 7 Days': [],
        'Older': []
    };
    
    conversations.forEach(conv => {
        const convDate = new Date(conv.updated_at);
        const convDay = new Date(convDate.getFullYear(), convDate.getMonth(), convDate.getDate());
        
        if (convDay.getTime() === today.getTime()) {
            groups['Today'].push(conv);
        } else if (convDay.getTime() === yesterday.getTime()) {
            groups['Yesterday'].push(conv);
        } else if (convDate >= lastWeek) {
            groups['Last 7 Days'].push(conv);
        } else {
            groups['Older'].push(conv);
        }
    });
    
    // Remove empty groups
    Object.keys(groups).forEach(key => {
        if (groups[key].length === 0) delete groups[key];
    });
    
    return groups;
}

// Get agent icon emoji
function getAgentIcon(agentName) {
    const icons = {
        'Luna': '🌙',
        'Mila': '🦉',
        'Sage': '🌱',
        'Ember': '🔥',
        'Sol': '☀️',
        'Nova': '⚡',
        'Theo': '🌿'
    };
    return icons[agentName] || '🤖';
}

// Format timestamp
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now - date) / 60000);
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Load specific conversation
async function loadConversation(convId) {
    try {
        // Close dropdown
        toggleHistoryDropdown();
        
        const response = await fetch(`/api/conversation/${convId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Failed to load conversation');
        
        const data = await response.json();
        
        // Clear current chat
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.innerHTML = '';
        
        // Set current conversation
        currentConversationId = data.id;
        
        // Switch to the conversation's agent
        if (data.agent && typeof switchAgent === 'function') {
            switchAgent(data.agent);
        }
        
        // Load messages
        data.messages.forEach(msg => {
            displayUserMessage(msg.message);
            displayAssistantMessage(msg.response);
        });
        
        // Update dropdown to show active conversation
        updateHistoryDropdown();
        
        showNotification(`Loaded: ${data.title}`);
        
    } catch (error) {
        console.error('Error loading conversation:', error);
        showNotification('Failed to load conversation', 'error');
    }
}

// Start new chat
function startNewChat() {
    // Clear chat container
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = '';
    
    // Reset conversation ID
    currentConversationId = null;
    
    // Show welcome message
    const welcomeMsg = document.createElement('div');
    welcomeMsg.className = 'welcome';
    welcomeMsg.innerHTML = `
        <h2>Hi! I'm ${getCurrentAgent()} ${getAgentIcon(getCurrentAgent())}</h2>
        <p>I'm ready to help you. What can I do for you today?</p>
    `;
    chatContainer.appendChild(welcomeMsg);
    
    // Close dropdown
    toggleHistoryDropdown();
    
    // Update dropdown
    updateHistoryDropdown();
    
    showNotification('Started new chat');
}

// Delete conversation
async function deleteConversation(convId, event) {
    event.stopPropagation();
    
    if (!confirm('Delete this conversation?')) return;
    
    try {
        const response = await fetch(`/api/conversation/${convId}/delete`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Failed to delete');
        
        // Remove from local array
        conversations = conversations.filter(c => c.id !== convId);
        
        // If this was the current conversation, start new chat
        if (currentConversationId === convId) {
            startNewChat();
        } else {
            updateHistoryDropdown();
        }
        
        showNotification('Conversation deleted');
        
    } catch (error) {
        console.error('Error deleting conversation:', error);
        showNotification('Failed to delete conversation', 'error');
    }
}

// Toggle history dropdown
function toggleHistoryDropdown() {
    const dropdown = document.getElementById('historyDropdownMenu');
    if (!dropdown) return;
    
    const isVisible = dropdown.style.display === 'block';
    
    // Hide all dropdowns first
    document.querySelectorAll('.dropdown-menu, .user-dropdown').forEach(d => {
        d.style.display = 'none';
        d.classList.remove('active', 'show');
    });
    
    if (!isVisible) {
        dropdown.style.display = 'block';
        dropdown.classList.add('active');
        // Load latest conversations
        loadConversations();
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const historyBtn = document.getElementById('historyBtn');
    const dropdown = document.getElementById('historyDropdownMenu');
    
    if (historyBtn && dropdown && !historyBtn.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.style.display = 'none';
        dropdown.classList.remove('active');
    }
});

// Load conversations on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConversations();
});

console.log('✅ Chat History module loaded!');
