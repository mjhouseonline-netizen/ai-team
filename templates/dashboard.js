// ================================================
// AI TEAM DASHBOARD - COMPLETE JAVASCRIPT
// Modern, Feature-Complete, Mobile-Optimized
// ================================================

// Global State
let currentAgent = 'Luna';
let imageMode = false;
let voiceMode = false;
let uploadedFile = null;
let recognition = null;
let speechSynthesis = window.speechSynthesis;

const agentEmojis = {
    'Luna': '🌙', 'Mila': '📋', 'Sage': '📝', 'Ember': '🎨',
    'Sol': '☀️', 'Nova': '💻', 'Theo': '⚡'
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
    
    // Update stats every 30 seconds
    setInterval(loadStats, 30000);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', handleOutsideClick);
});

// ================================================
// MENU & NAVIGATION
// ================================================

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
}

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    
    if (tab === 'chat') {
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.getElementById('chatTab').style.display = 'block';
    } else {
        document.querySelectorAll('.tab')[1].classList.add('active');
        document.getElementById('historyTab').style.display = 'block';
        loadHistory();
    }
}

// ================================================
// AGENT SELECTION
// ================================================

function selectAgent(name) {
    currentAgent = name;
    
    // Update active state
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.remove('active');
        if (card.textContent.includes(name)) {
            card.classList.add('active');
        }
    });
    
    // Update placeholder
    document.getElementById('messageInput').placeholder = `Message ${name}...`;
    
    // Update welcome message
    const welcome = document.querySelector('.welcome');
    if (welcome) {
        const agentDescriptions = {
            'Luna': 'I\'m your research analyst',
            'Mila': 'I\'m your task manager',
            'Sage': 'I\'m your content writer',
            'Ember': 'I\'m your creative director',
            'Sol': 'I\'m your wellness coach',
            'Nova': 'I\'m your tech specialist',
            'Theo': 'I\'m your strategy advisor'
        };
        welcome.innerHTML = `
            <h2>Hi! I'm ${name} ${agentEmojis[name]}</h2>
            <p>${agentDescriptions[name] || 'How can I help you today?'}</p>
        `;
    }
}

function selectCustomAgent(agent) {
    currentAgent = agent.name;
    
    document.querySelectorAll('.agent-card').forEach(card => card.classList.remove('active'));
    event.target.classList.add('active');
    
    document.getElementById('messageInput').placeholder = `Message ${agent.name}...`;
    
    const welcome = document.querySelector('.welcome');
    if (welcome) {
        welcome.innerHTML = `
            <h2>Hi! I'm ${agent.name} ✨</h2>
            <p>${agent.role || 'Custom AI Agent'}</p>
        `;
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
            } else {
                alert('File upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('File upload error');
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
            console.error('Speech recognition error:', event.error);
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

// ================================================
// TEXT-TO-SPEECH
// ================================================

function speakText(text) {
    if (!speechSynthesis) {
        alert('Text-to-speech not supported in your browser');
        return;
    }
    
    // Stop any ongoing speech
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
    
    // Display user message
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
        
        // Handle image generation
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
    
    const avatar = type === 'user' ? '👤' : agentEmojis[currentAgent];
    const badge = modelBadge ? `<span class="model-badge">${modelBadge}</span>` : '';
    
    // Check for website code
    const isWebsite = type === 'assistant' && detectWebsite(text);
    
    if (imageUrl) {
        messageDiv.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="message-content">
                ${escapeHtml(text)}${badge}
                <div style="margin-top:12px;">
                    <img src="${imageUrl}" style="max-width:100%; border-radius:8px; cursor:pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" onclick="previewImage('${imageUrl}')" alt="Generated image">
                </div>
            </div>
        `;
    } else if (isWebsite) {
        const code = extractWebsiteCode(text);
        const shortText = text.substring(0, 200) + (text.length > 200 ? '...' : '');
        messageDiv.innerHTML = `
            <div class="avatar">${avatar}</div>
            <div class="message-content">
                ${escapeHtml(shortText)}${badge}
                <div style="margin-top:12px; display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="btn btn-primary" style="flex: 1; min-width: 140px;" onclick='createWebsiteDownload(\`${code.replace(/`/g, '\\`')}\`)'>💻 Download Website</button>
                    <button class="btn btn-secondary" style="flex: 1; min-width: 140px;" onclick='previewWebsite(\`${code.replace(/`/g, '\\`')}\`)'>👁️ Preview Code</button>
                </div>
            </div>
        `;
    } else {
        const voiceBtn = type === 'assistant' ? `<button class="voice-btn" onclick="speakText(\`${text.replace(/`/g, '\\`').replace(/"/g, '&quot;')}\`)">🔊 Listen</button>` : '';
        messageDiv.innerHTML = `
            <div class="avatar">${avatar}</div>
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
        <div class="avatar">${agentEmojis[currentAgent]}</div>
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

function previewWebsite(code) {
    const modal = document.getElementById('previewModal');
    const body = document.getElementById('previewBody');
    body.innerHTML = `
        <h3 style="margin-bottom: 12px; color: var(--text-primary);">Website Code</h3>
        <div style="background: var(--bg-secondary); padding: 16px; border-radius: 8px; margin-bottom: 16px; max-height: 400px; overflow: auto;">
            <pre style="margin: 0; white-space: pre-wrap; font-size: 12px; line-height: 1.5; font-family: monospace;">${escapeHtml(code)}</pre>
        </div>
        <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary" style="flex: 1;" onclick='createWebsiteDownload(\`${code.replace(/`/g, '\\`')}\`)'>💻 Download</button>
            <button class="btn btn-secondary" style="flex: 1;" onclick='copyToClipboard(\`${code.replace(/`/g, '\\`')}\`)'>📋 Copy Code</button>
        </div>
    `;
    modal.classList.add('active');
}

// ================================================
// IMAGE PREVIEW
// ================================================

function previewImage(url) {
    const modal = document.getElementById('previewModal');
    const body = document.getElementById('previewBody');
    body.innerHTML = `
        <img src="${url}" style="max-width:100%; max-height: 70vh; border-radius:8px; display: block; margin: 0 auto;">
        <div style="display: flex; gap: 8px; margin-top: 16px;">
            <button class="btn btn-primary" style="flex: 1;" onclick="downloadFromUrl('${url}')">📥 Download</button>
            <button class="btn btn-secondary" style="flex: 1;" onclick="copyToClipboard('${url}')">📋 Copy URL</button>
        </div>
    `;
    modal.classList.add('active');
}

function closePreview() {
    document.getElementById('previewModal').classList.remove('active');
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
    const prompt = document.getElementById('agentPrompt').value;
    
    try {
        const response = await fetch('/api/custom-agent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                role: role,
                system_prompt: `You are ${name}, a ${role}. ${prompt}`
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('✅ Custom agent created successfully!');
            closeCustomAgentModal();
            loadCustomAgents();
        } else {
            alert('Error: ' + (data.error || 'Failed to create agent'));
        }
    } catch (error) {
        alert('Error: Failed to connect to server');
    }
}

async function loadCustomAgents() {
    try {
        const response = await fetch('/api/custom-agents', { credentials: 'include' });
        const data = await response.json();
        
        const agentGrid = document.getElementById('agentGrid');
        
        // Remove old custom agents
        const oldCustom = agentGrid.querySelectorAll('[data-custom="true"]');
        oldCustom.forEach(el => el.remove());
        
        // Add new custom agents before the "Custom" button
        const customBtn = agentGrid.querySelector('.custom-agent-btn');
        data.agents.forEach(agent => {
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.setAttribute('data-custom', 'true');
            card.textContent = `✨ ${agent.name}`;
            card.onclick = () => selectCustomAgent(agent);
            agentGrid.insertBefore(card, customBtn);
        });
    } catch (error) {
        console.error('Error loading custom agents:', error);
    }
}

// ================================================
// AGENT LIBRARY
// ================================================

function openAgentLibrary() {
    document.getElementById('agentLibraryModal').classList.add('active');
    toggleMenu();
    loadAgentLibraryContent();
}

function closeAgentLibrary() {
    document.getElementById('agentLibraryModal').classList.remove('active');
}

async function loadAgentLibraryContent() {
    const container = document.getElementById('agentLibraryContent');
    
    try {
        const response = await fetch('/api/custom-agents', { credentials: 'include' });
        const data = await response.json();
        
        if (data.agents.length === 0) {
            container.innerHTML = '<div class="welcome"><p>No custom agents yet. Create your first one!</p></div>';
            return;
        }
        
        let html = '<div class="library-grid">';
        data.agents.forEach(agent => {
            html += `
                <div class="library-item">
                    <h3>✨ ${agent.name}</h3>
                    <p>${agent.role || 'Custom Agent'}</p>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-primary" style="flex: 1;" onclick="useCustomAgent(${agent.id}, '${agent.name}'); closeAgentLibrary();">Use Agent</button>
                        <button class="btn btn-danger" style="flex: 1;" onclick="deleteCustomAgent(${agent.id})">Delete</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = '<div class="welcome"><p>Error loading agents</p></div>';
    }
}

function useCustomAgent(id, name) {
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.remove('active');
        if (card.textContent.includes(name)) {
            card.classList.add('active');
        }
    });
    currentAgent = name;
    document.getElementById('messageInput').placeholder = `Message ${name}...`;
}

async function deleteCustomAgent(id) {
    if (!confirm('Delete this custom agent?')) return;
    
    try {
        const response = await fetch(`/api/custom-agent/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Agent deleted successfully');
            loadCustomAgents();
            loadAgentLibraryContent();
        } else {
            alert('Error deleting agent');
        }
    } catch (error) {
        alert('Error: Failed to delete agent');
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
    if (!input) {
        alert('Please describe what you want help with');
        return;
    }
    
    // Simple prompt enhancement
    const enhanced = `I need help with the following task: ${input}\n\nPlease provide a detailed response that includes:\n1. A clear explanation\n2. Practical examples\n3. Step-by-step guidance if applicable\n4. Best practices and tips`;
    
    document.getElementById('promptOutput').value = enhanced;
}

function usePrompt() {
    const prompt = document.getElementById('promptOutput').value;
    if (!prompt) {
        alert('Generate a prompt first');
        return;
    }
    
    document.getElementById('messageInput').value = prompt;
    closePromptBuilder();
}

// ================================================
// HISTORY
// ================================================

async function loadHistory() {
    const container = document.getElementById('historyContainer');
    container.innerHTML = '<div class="welcome"><p>Loading history...</p></div>';
    
    try {
        const response = await fetch('/api/chat-history', { credentials: 'include' });
        const data = await response.json();
        
        if (!data.history || data.history.length === 0) {
            container.innerHTML = '<div class="welcome"><p>No chat history yet. Start a conversation!</p></div>';
            return;
        }
        
        let html = '<div style="padding: 20px;">';
        data.history.forEach((item, index) => {
            const date = new Date(item.timestamp).toLocaleString();
            html += `
                <div style="background: var(--bg-secondary); padding: 16px; border-radius: 12px; margin-bottom: 12px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap;">
                        <strong style="color: var(--primary);">${agentEmojis[item.agent_name] || '🤖'} ${item.agent_name}</strong>
                        <span style="font-size: 12px; color: var(--text-secondary);">${date}</span>
                    </div>
                    <div style="color: var(--text-secondary); font-size: 14px; margin-bottom: 8px;"><strong>You:</strong> ${item.message.substring(0, 150)}${item.message.length > 150 ? '...' : ''}</div>
                    <div style="color: var(--text-primary); font-size: 14px;"><strong>Response:</strong> ${item.response.substring(0, 150)}${item.response.length > 150 ? '...' : ''}</div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = '<div class="welcome"><p>Error loading history</p></div>';
    }
}

async function clearAllChat() {
    if (!confirm('This will clear ALL chat history. Continue?')) return;
    
    try {
        const response = await fetch('/api/clear-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ agent: 'all' })
        });
        
        if (response.ok) {
            document.getElementById('chatContainer').innerHTML = '<div class="welcome"><h2>All chats cleared!</h2><p>Start fresh with any agent.</p></div>';
            alert('✅ All chats cleared successfully');
        } else {
            alert('Error clearing chats');
        }
    } catch (error) {
        alert('Error: Failed to clear chats');
    }
}

// ================================================
// STATS & USER INFO
// ================================================

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
        }
    } catch (error) {
        console.error('Error checking admin:', error);
    }
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
        alert('✅ Copied to clipboard!');
    }).catch(err => {
        console.error('Copy failed:', err);
        alert('Failed to copy');
    });
}
