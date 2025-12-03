// ================================================
// AI TEAM ULTIMATE DASHBOARD - JAVASCRIPT
// Sidebar + Floating Preview + Enhanced Features
// ================================================

// Global State
let currentAgent = 'Luna';
let currentAgentEmoji = '🌙';
let currentAgentRole = 'Research Analyst';
let imageMode = false;
let voiceMode = false;
let uploadedFile = null;
let recognition = null;
let speechSynthesis = window.speechSynthesis;

const agentGradients = {
    'Luna': 'linear-gradient(135deg, #667eea, #764ba2)',
    'Mila': 'linear-gradient(135deg, #f093fb, #f5576c)',
    'Sage': 'linear-gradient(135deg, #4facfe, #00f2fe)',
    'Ember': 'linear-gradient(135deg, #fa709a, #fee140)',
    'Sol': 'linear-gradient(135deg, #ffecd2, #fcb69f)',
    'Nova': 'linear-gradient(135deg, #a8edea, #fed6e3)',
    'Theo': 'linear-gradient(135deg, #ff9a9e, #fecfef)'
};

// ================================================
// INITIALIZATION
// ================================================

document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    checkAdminStatus();
    setupFileInput();
    initVoiceRecognition();
    loadCustomAgents();
    setupMobileToggle();
    
    setInterval(loadStats, 30000);
    document.addEventListener('click', handleOutsideClick);
});

function setupMobileToggle() {
    if (window.innerWidth <= 768) {
        document.getElementById('sidebarToggle').style.display = 'block';
    }
    
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            document.getElementById('sidebarToggle').style.display = 'block';
        } else {
            document.getElementById('sidebarToggle').style.display = 'none';
            document.getElementById('sidebar').classList.remove('active');
        }
    });
}

// ================================================
// SIDEBAR & NAVIGATION
// ================================================

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
}

function toggleMenu() {
    const menu = document.getElementById('dropdownMenu');
    menu.classList.toggle('active');
}

function handleOutsideClick(e) {
    const menu = document.getElementById('dropdownMenu');
    const menuBtn = e.target.closest('.menu-btn');
    if (!menuBtn && !menu.contains(e.target)) {
        menu.classList.remove('active');
    }
    
    // Close sidebar on mobile when clicking outside
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = e.target.closest('.sidebar-toggle');
        if (!sidebar.contains(e.target) && !sidebarToggle) {
            sidebar.classList.remove('active');
        }
    }
}

// ================================================
// AGENT SELECTION
// ================================================

function selectAgent(name, emoji, role) {
    currentAgent = name;
    currentAgentEmoji = emoji;
    currentAgentRole = role;
    
    // Update active state in sidebar
    document.querySelectorAll('.agent-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    // Update header
    const avatar = document.getElementById('currentAgentAvatar');
    avatar.textContent = emoji;
    avatar.style.background = agentGradients[name] || 'linear-gradient(135deg, #667eea, #764ba2)';
    document.getElementById('currentAgentName').textContent = name;
    
    // Update input placeholder
    document.getElementById('messageInput').placeholder = `Message ${name}...`;
    
    // Update welcome message
    const welcome = document.querySelector('.welcome');
    if (welcome) {
        welcome.innerHTML = `
            <h2>Hi! I'm ${name} ${emoji}</h2>
            <p>I'm your ${role.toLowerCase()}. How can I help you today?</p>
        `;
    }
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        toggleSidebar();
    }
}

// ================================================
// INPUT HANDLING
// ================================================

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function toggleImageMode() {
    imageMode = !imageMode;
    const btn = document.getElementById('imageBtn');
    const input = document.getElementById('messageInput');
    
    if (imageMode) {
        btn.classList.add('active');
        input.placeholder = '🎨 Describe the image you want to generate...';
    } else {
        btn.classList.remove('active');
        input.placeholder = `Message ${currentAgent}...`;
    }
}

// ================================================
// FILE HANDLING
// ================================================

function setupFileInput() {
    document.getElementById('fileInput').addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/upload-file', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.filename) {
                uploadedFile = data;
                document.getElementById('fileName').textContent = `📎 ${file.name}`;
                document.getElementById('filePreview').classList.add('active');
            }
        } catch (error) {
            console.error('Upload error:', error);
        }
    });
}

function removeFile() {
    uploadedFile = null;
    document.getElementById('filePreview').classList.remove('active');
    document.getElementById('fileInput').value = '';
}

// ================================================
// VOICE RECOGNITION
// ================================================

function initVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('messageInput').value = transcript;
            voiceMode = false;
            document.getElementById('voiceBtn').classList.remove('active');
        };
        
        recognition.onerror = function(event) {
            voiceMode = false;
            document.getElementById('voiceBtn').classList.remove('active');
        };
        
        recognition.onend = function() {
            voiceMode = false;
            document.getElementById('voiceBtn').classList.remove('active');
        };
    }
}

function toggleVoice() {
    if (!recognition) {
        alert('Voice input not supported in your browser. Try Chrome or Edge.');
        return;
    }
    
    voiceMode = !voiceMode;
    const btn = document.getElementById('voiceBtn');
    
    if (voiceMode) {
        btn.classList.add('active');
        recognition.start();
    } else {
        btn.classList.remove('active');
        recognition.stop();
    }
}

function speakText(text) {
    if (!speechSynthesis) return;
    
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    speechSynthesis.speak(utterance);
}

// ================================================
// SEND MESSAGE
// ================================================

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message && !uploadedFile) return;
    
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';
    
    let displayMessage = message;
    if (uploadedFile) {
        displayMessage = `📎 ${uploadedFile.original_filename}\n${message}`;
    }
    
    addMessage(displayMessage || '📎 File uploaded', 'user');
    input.value = '';
    input.style.height = 'auto';
    
    const typingId = showTyping();
    
    try {
        const selectedModel = document.getElementById('modelSelect').value;
        let endpoint = '/api/chat';
        let requestBody = {
            message: message || 'Please analyze this file',
            agent: currentAgent,
            model: selectedModel,
            file: uploadedFile
        };
        
        if (imageMode) {
            endpoint = '/api/generate-image-free';
            requestBody = {
                prompt: message,
                agent: currentAgent
            };
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        removeTyping(typingId);
        
        if (response.ok) {
            if (imageMode && data.image_url) {
                addMessage('Here\'s your generated image!', 'assistant', data.image_url);
            } else {
                const modelBadge = data.model_used ? getModelName(data.model_used) : '';
                addMessage(data.response, 'assistant', null, modelBadge);
            }
            loadStats();
        } else {
            addMessage(`Error: ${data.error || 'Failed to get response'}`, 'assistant');
        }
    } catch (error) {
        removeTyping(typingId);
        console.error('Send message error:', error);
        addMessage('Error: Failed to connect to server', 'assistant');
    }
    
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    
    if (imageMode) toggleImageMode();
    if (uploadedFile) removeFile();
}

// ================================================
// MESSAGE DISPLAY
// ================================================

function addMessage(text, type, imageUrl = null, modelBadge = '') {
    const container = document.getElementById('chatContainer');
    const welcome = container.querySelector('.welcome');
    if (welcome) welcome.remove();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatar = type === 'user' ? '👤' : currentAgentEmoji;
    const badge = modelBadge ? `<span class="model-badge">${modelBadge}</span>` : '';
    
    const isWebsite = type === 'assistant' && detectWebsite(text);
    
    if (imageUrl) {
        messageDiv.innerHTML = `
            <div class="avatar" style="${type === 'assistant' ? 'background: ' + (agentGradients[currentAgent] || 'linear-gradient(135deg, #667eea, #764ba2)') : 'background: #5436da'}">${avatar}</div>
            <div class="message-content">
                ${escapeHtml(text)}${badge}
                <div style="margin-top:12px;">
                    <img src="${imageUrl}" style="max-width:100%; border-radius:8px; cursor:pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" onclick="showFloatingPreview('image', '${imageUrl}')" alt="Generated image">
                </div>
            </div>
        `;
    } else if (isWebsite) {
        const code = extractWebsiteCode(text);
        const shortText = text.substring(0, 200) + (text.length > 200 ? '...' : '');
        messageDiv.innerHTML = `
            <div class="avatar" style="background: ${agentGradients[currentAgent] || 'linear-gradient(135deg, #667eea, #764ba2)'}">${avatar}</div>
            <div class="message-content">
                ${escapeHtml(shortText)}${badge}
                <div style="margin-top:12px; display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="btn btn-primary" style="flex: 1; min-width: 120px;" onclick='showFloatingPreview("website", \`${code.replace(/`/g, '\\`')}\`)'>👁️ Preview</button>
                    <button class="btn btn-secondary" style="flex: 1; min-width: 120px;" onclick='createWebsiteDownload(\`${code.replace(/`/g, '\\`')}\`)'>💻 Download</button>
                </div>
            </div>
        `;
    } else {
        const voiceBtn = type === 'assistant' ? `<button class="voice-btn" onclick="speakText(\`${text.replace(/`/g, '\\`').replace(/"/g, '&quot;')}\`)">🔊 Listen</button>` : '';
        messageDiv.innerHTML = `
            <div class="avatar" style="${type === 'assistant' ? 'background: ' + (agentGradients[currentAgent] || 'linear-gradient(135deg, #667eea, #764ba2)') : 'background: #5436da'}">${avatar}</div>
            <div class="message-content">
                ${escapeHtml(text)}${badge}
                ${voiceBtn}
            </div>
        `;
    }
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function showTyping() {
    const container = document.getElementById('chatContainer');
    const typingDiv = document.createElement('div');
    const id = 'typing-' + Date.now();
    typingDiv.id = id;
    typingDiv.className = 'message assistant';
    typingDiv.innerHTML = `
        <div class="avatar" style="background: ${agentGradients[currentAgent] || 'linear-gradient(135deg, #667eea, #764ba2)'}">${currentAgentEmoji}</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTyping(id) {
    const typing = document.getElementById(id);
    if (typing) typing.remove();
}

// ================================================
// FLOATING PREVIEW WINDOW
// ================================================

function showFloatingPreview(type, content) {
    const preview = document.getElementById('floatingPreview');
    const title = document.getElementById('previewTitle');
    const body = document.getElementById('floatingPreviewBody');
    const actions = document.getElementById('floatingPreviewActions');
    
    if (type === 'image') {
        title.textContent = 'Image Preview';
        body.innerHTML = `<img src="${content}" style="max-width:100%; border-radius:8px;">`;
        actions.innerHTML = `
            <button class="btn btn-primary" style="flex: 1;" onclick="downloadFromUrl('${content}')">📥 Download</button>
            <button class="btn btn-secondary" style="flex: 1;" onclick="copyToClipboard('${content}')">📋 Copy URL</button>
        `;
    } else if (type === 'website') {
        title.textContent = 'Website Preview';
        
        // Create blob URL for iframe
        const blob = new Blob([content], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        
        body.innerHTML = `<iframe class="preview-iframe" src="${url}"></iframe>`;
        actions.innerHTML = `
            <button class="btn btn-primary" style="flex: 1;" onclick='createWebsiteDownload(\`${content.replace(/`/g, '\\`')}\`)'>💻 Download</button>
            <button class="btn btn-secondary" style="flex: 1;" onclick='copyToClipboard(\`${content.replace(/`/g, '\\`')}\`)'>📋 Copy Code</button>
        `;
    }
    
    preview.classList.add('active');
}

function closeFloatingPreview() {
    document.getElementById('floatingPreview').classList.remove('active');
}

function minimizePreview() {
    // Could implement minimize functionality
    closeFloatingPreview();
}

// ================================================
// WEBSITE BUILDER
// ================================================

function detectWebsite(text) {
    return /<!DOCTYPE html>|<html|<\/html>/i.test(text);
}

function extractWebsiteCode(text) {
    const match = text.match(/```html\n([\s\S]*?)```/) || text.match(/(<!DOCTYPE[\s\S]*<\/html>)/i);
    return match ? match[1] : text;
}

function createWebsiteDownload(code) {
    const blob = new Blob([code], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'website_' + Date.now() + '.html';
    a.click();
    URL.revokeObjectURL(url);
}

// ================================================
// CUSTOM AGENTS
// ================================================

function openCustomAgentModal() {
    document.getElementById('customAgentModal').classList.add('active');
    toggleMenu();
}

function closeCustomAgentModal() {
    document.getElementById('customAgentModal').classList.remove('active');
    document.getElementById('customAgentForm').reset();
}

async function saveCustomAgent(event) {
    event.preventDefault();
    
    const name = document.getElementById('agentName').value;
    const role = document.getElementById('agentRole').value;
    const emoji = document.getElementById('agentEmoji').value || '✨';
    const prompt = document.getElementById('agentPrompt').value;
    
    try {
        const response = await fetch('/api/custom-agents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                role: role,
                emoji: emoji,
                instructions: `You are ${name}, a ${role}. ${prompt}`
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('✅ Custom agent created!');
            closeCustomAgentModal();
            loadCustomAgents();
        } else {
            alert('Error: ' + (data.error || 'Failed to create agent'));
        }
    } catch (error) {
        alert('Error: Failed to connect');
    }
}

async function loadCustomAgents() {
    try {
        const response = await fetch('/api/custom-agents', { credentials: 'include' });
        const data = await response.json();
        
        const container = document.getElementById('customAgentsList');
        container.innerHTML = '';
        
        if (data.agents.length > 0) {
            document.getElementById('customAgentsTitle').style.display = 'block';
            
            data.agents.forEach(agent => {
                const item = document.createElement('div');
                item.className = 'agent-item';
                item.innerHTML = `
                    <div class="agent-avatar" style="background: linear-gradient(135deg, #667eea, #764ba2);">${agent.emoji || '✨'}</div>
                    <div class="agent-info">
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-role">${agent.role || 'Custom Agent'}</div>
                    </div>
                `;
                item.onclick = () => selectAgent(agent.name, agent.emoji || '✨', agent.role || 'Custom Agent');
                container.appendChild(item);
            });
        }
    } catch (error) {
        console.error('Error loading custom agents:', error);
    }
}

// ================================================
// PROMPT BUILDER
// ================================================

function openPromptBuilder() {
    document.getElementById('promptBuilderModal').classList.add('active');
    toggleMenu();
}

function closePromptBuilder() {
    document.getElementById('promptBuilderModal').classList.remove('active');
}

function buildPrompt() {
    const input = document.getElementById('promptInput').value.trim();
    const style = document.getElementById('promptStyle').value;
    
    if (!input) {
        alert('Please describe what you want help with');
        return;
    }
    
    const styles = {
        'detailed': `Please provide a comprehensive and detailed response to the following:\n\n${input}\n\nInclude:\n- Thorough explanation\n- Relevant examples\n- Step-by-step guidance\n- Best practices and tips\n- Potential challenges and solutions`,
        'concise': `${input}\n\nProvide a concise, direct answer focusing on the key points.`,
        'creative': `Here's what I need:\n\n${input}\n\nPlease approach this creatively with:\n- Original ideas\n- Unique perspectives\n- Engaging examples\n- Innovative solutions`,
        'professional': `Request:\n\n${input}\n\nPlease provide a professional response with:\n- Formal language\n- Industry best practices\n- Expert-level insights\n- Professional recommendations`,
        'casual': `Hey! ${input}\n\nKeep it friendly and casual, but still helpful!`
    };
    
    document.getElementById('promptOutput').value = styles[style] || styles['detailed'];
}

function usePrompt() {
    const prompt = document.getElementById('promptOutput').value;
    if (!prompt) {
        alert('Generate a prompt first');
        return;
    }
    
    document.getElementById('messageInput').value = prompt;
    closePromptBuilder();
    document.getElementById('messageInput').focus();
}

// ================================================
// HISTORY & STATS
// ================================================

async function viewHistory() {
    try {
        const response = await fetch('/api/history', { credentials: 'include' });
        const data = await response.json();
        
        if (!response.ok) {
            alert('Error loading chat history');
            toggleMenu();
            return;
        }
        
        const history = data.history || [];
        
        if (history.length === 0) {
            alert('No chat history yet. Start chatting to build your history!');
            toggleMenu();
            return;
        }
        
        // Create history modal
        let historyHTML = '<div class="history-modal-backdrop" onclick="closeHistoryModal()">';
        historyHTML += '<div class="history-modal" onclick="event.stopPropagation()">';
        historyHTML += '<div class="history-header">';
        historyHTML += '<h2>📜 Chat History</h2>';
        historyHTML += '<button onclick="closeHistoryModal()" class="history-close">✕</button>';
        historyHTML += '</div>';
        historyHTML += '<div class="history-content">';
        
        history.forEach(item => {
            const timestamp = new Date(item.timestamp).toLocaleString();
            historyHTML += `
                <div class="history-item">
                    <div class="history-meta">
                        <span class="history-agent">${item.agent}</span>
                        <span class="history-time">${timestamp}</span>
                    </div>
                    <div class="history-message">
                        <strong>You:</strong> ${item.message}
                    </div>
                    <div class="history-response">
                        <strong>${item.agent}:</strong> ${item.response.substring(0, 200)}${item.response.length > 200 ? '...' : ''}
                    </div>
                </div>
            `;
        });
        
        historyHTML += '</div></div></div>';
        
        // Add to page
        document.body.insertAdjacentHTML('beforeend', historyHTML);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading chat history');
    }
    toggleMenu();
}

function closeHistoryModal() {
    const modal = document.querySelector('.history-modal-backdrop');
    if (modal) {
        modal.remove();
    }
}

async function clearAllChat() {
    if (!confirm('Clear all chat history?')) return;
    
    try {
        const response = await fetch('/api/clear-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ agent: 'all' })
        });
        
        if (response.ok) {
            document.getElementById('chatContainer').innerHTML = '<div class="welcome"><h2>All chats cleared!</h2><p>Start fresh.</p></div>';
            alert('✅ Chats cleared');
        }
    } catch (error) {
        alert('Error clearing chats');
    }
    toggleMenu();
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats', { credentials: 'include' });
        const data = await response.json();
        document.getElementById('messages-used').textContent = data.messages_today || 0;
        document.getElementById('daily-limit').textContent = data.daily_limit || 25;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function checkAdminStatus() {
    try {
        const response = await fetch('/api/user-info', { credentials: 'include' });
        const data = await response.json();
        if (data.is_admin) {
            document.getElementById('adminLink').style.display = 'block';
            document.getElementById('adminSidebarLink').style.display = 'flex';
            document.getElementById('promoSidebarLink').style.display = 'flex';
        }
    } catch (error) {
        console.error('Error checking admin:', error);
    }
}

function openAgentLibrary() {
    alert('Agent library - Full view coming soon!');
    toggleMenu();
}

// ================================================
// UTILITY FUNCTIONS
// ================================================

function getModelName(key) {
    const models = {
        'claude-sonnet-4.5': 'Sonnet 4.5',
        'claude-opus-4': 'Opus 4',
        'claude-haiku-4.5': 'Haiku 4.5',
        'gpt-4o': 'GPT-4o',
        'gpt-4-turbo': 'GPT-4 Turbo',
        'gpt-4o-mini': 'GPT-4o Mini',
        'gemini-2.0-flash': 'Gemini 2.0',
        'gemini-1.5-pro': 'Gemini 1.5 Pro'
    };
    return models[key] || key;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

function downloadFromUrl(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = 'download_' + Date.now() + '.png';
    a.click();
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('✅ Copied!');
    }).catch(() => {
        alert('Failed to copy');
    });
}
