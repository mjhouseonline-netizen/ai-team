// ================================================
// AI TEAM ULTIMATE DASHBOARD - JAVASCRIPT
// Sidebar + Floating Preview + Enhanced Features
// ================================================

// Global State
// Note: imageMode and recognition are declared in dashboard.html to avoid redeclaration errors
let currentAgent = 'Luna';
let currentAgentEmoji = '🌙';
let currentAgentRole = 'Research Analyst';
let voiceMode = false;
let uploadedFile = null;
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
    const input = document.getElementById('messageInput');
    
    if (imageMode) {
        input.placeholder = '🎨 Describe the image you want to generate...';
        input.style.borderColor = '#10a37f';
        input.style.borderWidth = '2px';
        // Visual feedback
        const notification = document.createElement('div');
        notification.textContent = '🎨 Image Mode Active!';
        notification.style.cssText = 'position:fixed;top:20px;right:20px;background:#10a37f;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:10000;font-weight:600;';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 2000);
    } else {
        input.placeholder = `Message ${currentAgent}...`;
        input.style.borderColor = '';
        input.style.borderWidth = '';
    }
    input.focus();
}

// ================================================
// FILE HANDLING
// ================================================

function setupFileInput() {
    // File input is handled by the HTML's own implementation
    // This function is kept for compatibility but doesn't override the HTML handler
    console.log('✅ File input handler initialized');
}

// Note: removeFile() is defined in dashboard.html
// Do not override it here to avoid conflicts

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
            // Check if upgrade is required (403 Forbidden with upgrade_required flag)
            if (response.status === 403 && data.upgrade_required) {
                // Show upgrade modal instead of error message
                const modelName = getModelName(data.blocked_model || selectedModel);
                const requiredTier = data.required_tier || 'a paid plan';
                const currentTier = data.current_tier || 'free';

                // Call the modal function (defined in dashboard.html)
                if (typeof showUpgradeModal === 'function') {
                    showUpgradeModal(modelName, requiredTier, currentTier);
                } else {
                    // Fallback to error message if modal function not available
                    addMessage(`⚠️ Upgrade Required: ${data.error}\n\n💡 Click here to upgrade: /pricing`, 'assistant');
                }
            } else {
                // Show regular error message
                addMessage(`Error: ${data.error || 'Failed to get response'}`, 'assistant');
            }
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
    const outputField = document.getElementById('promptOutput');
    
    if (!input) {
        alert('Please describe what you want help with');
        return;
    }
    
    // Create prompts using the 7 Pillars of Effective Prompting:
    // 1. Task/Goal, 2. Context, 3. Exemplars, 4. Persona, 5. Format, 6. Tone, 7. Constraints
    let enhancedPrompt = '';
    
    switch(style) {
        case 'detailed':
            enhancedPrompt = `TASK: ${input}

ROLE: Act as an expert consultant with deep knowledge in this area.

CONTEXT: I need comprehensive understanding and practical guidance. This is important for [my work/project/learning] and I want to make informed decisions.

FORMAT: Please structure your response with:
- Clear explanation of key concepts
- Step-by-step action plan
- Real-world examples demonstrating the concepts
- Best practices and industry standards
- Common pitfalls and how to avoid them
- Recommended tools or next steps

TONE: Professional yet accessible. Use clear explanations without oversimplifying.

CONSTRAINTS: Focus on actionable, practical advice. If you need more information to give the best answer, ask specific clarifying questions.`;
            break;
            
        case 'concise':
            enhancedPrompt = `TASK: ${input}

ROLE: Act as an efficient expert who values clarity and brevity.

FORMAT: Provide a direct, focused response in 3-5 sentences that gives me exactly what I need to know.

TONE: Clear, straightforward, no fluff.

CONSTRAINTS: 
- Essential information only
- Skip background unless critical
- Use simple language
- Get straight to the answer`;
            break;
            
        case 'creative':
            enhancedPrompt = `TASK: ${input}

ROLE: Act as a creative innovator and brainstorming partner with fresh perspectives.

CONTEXT: I'm looking for unique, imaginative approaches that go beyond conventional thinking.

FORMAT: Present your ideas as:
- 2-3 creative concepts with vivid descriptions
- Unexpected angles I might not have considered
- Practical examples showing how ideas could work
- Ways to blend creativity with feasibility

TONE: Enthusiastic, inspiring, and imaginative while staying grounded.

CONSTRAINTS: Ideas should be creative but implementable. Explain the "why" behind each suggestion.`;
            break;
            
        case 'professional':
            enhancedPrompt = `TASK: ${input}

ROLE: Act as a senior business consultant with expertise in this domain.

CONTEXT: This is for a professional/business context where strategic thinking and industry standards matter.

FORMAT: Provide a business-focused analysis including:
- Strategic considerations and business implications
- Data-driven recommendations when applicable
- Industry best practices and benchmarks
- Risk assessment and mitigation strategies
- Implementation roadmap

TONE: Formal, authoritative, business-appropriate.

CONSTRAINTS: Use professional terminology appropriately. Back recommendations with reasoning. Consider ROI and practical business constraints.`;
            break;
            
        case 'casual':
            enhancedPrompt = `TASK: ${input}

ROLE: Act as a knowledgeable friend who explains things in a relatable way.

CONTEXT: I want solid advice without the formality. Help me understand this like you're chatting over coffee.

FORMAT: Explain in a conversational way using:
- Everyday language and relatable examples
- Personal anecdotes or common scenarios
- Practical tips I can use right away
- Simple explanations of any necessary technical terms

TONE: Friendly, warm, approachable. Like talking to someone who really gets it.

CONSTRAINTS: Keep it conversational but still informative. No jargon unless you explain it simply.`;
            break;
            
        default:
            enhancedPrompt = input;
    }
    
    outputField.value = enhancedPrompt;
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
        
        // Group ALL messages by agent (not by date)
        const agentChats = {};
        history.forEach(item => {
            const agent = item.agent;
            if (!agentChats[agent]) {
                agentChats[agent] = {
                    agent: agent,
                    messages: [],
                    lastTimestamp: item.timestamp
                };
            }
            agentChats[agent].messages.push(item);
            // Update last timestamp if this message is more recent
            if (new Date(item.timestamp) > new Date(agentChats[agent].lastTimestamp)) {
                agentChats[agent].lastTimestamp = item.timestamp;
            }
        });
        
        // Create history modal
        let historyHTML = '<div class="history-modal-backdrop" onclick="closeHistoryModal()">';
        historyHTML += '<div class="history-modal" onclick="event.stopPropagation()">';
        historyHTML += '<div class="history-header">';
        historyHTML += '<h2>📜 Chat History</h2>';
        historyHTML += '<button onclick="closeHistoryModal()" class="history-close">✕</button>';
        historyHTML += '</div>';
        historyHTML += '<div class="history-content">';
        
        // Sort agents by most recent activity
        const sortedAgents = Object.values(agentChats).sort((a, b) => 
            new Date(b.lastTimestamp) - new Date(a.lastTimestamp)
        );
        
        sortedAgents.forEach((agentChat, index) => {
            const msgCount = agentChat.messages.length;
            const firstMsg = agentChat.messages[0];
            const lastDate = new Date(agentChat.lastTimestamp).toLocaleDateString();
            const preview = firstMsg.message.substring(0, 80);
            
            // Get agent emoji
            const agentEmojis = {
                'Luna': '🌙',
                'Mila': '🐉',
                'Sage': '🦉',
                'Ember': '🦁',
                'Sol': '🐤',
                'Nova': '🌌',
                'Theo': '🐰'
            };
            const emoji = agentEmojis[agentChat.agent] || '🤖';
            
            historyHTML += `
                <div class="history-item" onclick="loadAgentHistory('${escapeHtml(agentChat.agent)}', ${index})" style="cursor: pointer; transition: all 0.2s;">
                    <div class="history-meta" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="history-agent" style="font-weight: 600; color: #10a37f; font-size: 16px;">
                            ${emoji} ${escapeHtml(agentChat.agent)}
                        </span>
                        <span class="history-count" style="background: #10a37f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                            ${msgCount} messages
                        </span>
                    </div>
                    <div class="history-time" style="color: #666; font-size: 13px; margin-bottom: 6px;">
                        Last active: ${lastDate}
                    </div>
                    <div class="history-preview" style="color: #374151; font-size: 14px; line-height: 1.4;">
                        ${escapeHtml(preview)}${preview.length >= 80 ? '...' : ''}
                    </div>
                </div>
            `;
        });
        
        historyHTML += '</div></div></div>';
        
        // Store agent chats for later access
        window.agentHistory = sortedAgents;
        
        // Add to page
        document.body.insertAdjacentHTML('beforeend', historyHTML);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading chat history');
    }
    toggleMenu();
}

function loadAgentHistory(agent, agentIndex) {
    // Close history modal
    closeHistoryModal();
    
    // Get agent's chat history
    const agentChat = window.agentHistory[agentIndex];
    if (!agentChat) return;
    
    // Switch to the agent
    switchAgent(agent);
    
    // Clear current chat
    const container = document.getElementById('chatContainer');
    container.innerHTML = '';
    
    // Load ALL messages from this agent in chronological order
    agentChat.messages.forEach(msg => {
        addMessage(msg.message, 'user');
        addMessage(msg.response, 'assistant');
    });
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    // Show notification
    const notification = document.createElement('div');
    notification.textContent = `📜 Loaded ${agentChat.messages.length} messages with ${agent}`;
    notification.style.cssText = 'position:fixed;top:20px;right:20px;background:#10a37f;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:10000;font-weight:600;';
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
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
        const response = await fetch('/api/user-stats', { credentials: 'include' });
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

async function openAgentLibrary() {
    toggleMenu();
    
    const modal = document.getElementById('agentLibraryModal');
    const loading = document.getElementById('libraryLoading');
    const empty = document.getElementById('libraryEmpty');
    const grid = document.getElementById('libraryGrid');
    
    // Show modal
    modal.style.display = 'block';
    
    // Show loading state
    loading.style.display = 'block';
    empty.style.display = 'none';
    grid.style.display = 'none';
    grid.innerHTML = '';
    
    try {
        // Load custom agents
        const response = await fetch('/api/custom-agents', {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (!data.agents || data.agents.length === 0) {
            // No agents yet
            empty.style.display = 'block';
        } else {
            // Show agents in grid
            grid.style.display = 'grid';
            
            data.agents.forEach(agent => {
                const card = document.createElement('div');
                card.className = 'library-agent-card';
                
                card.innerHTML = `
                    <div class="library-agent-emoji">${agent.emoji || '🤖'}</div>
                    <div class="library-agent-name">${escapeHtml(agent.name)}</div>
                    <div class="library-agent-role">${escapeHtml(agent.role)}</div>
                    <div class="library-agent-personality">${escapeHtml(agent.personality || 'A helpful AI assistant')}</div>
                    <div class="library-agent-actions">
                        <button class="library-action-btn library-chat-btn" onclick="chatWithLibraryAgent('${escapeHtml(agent.name)}', ${agent.id})">
                            💬 Chat
                        </button>
                        <button class="library-action-btn library-delete-btn" onclick="deleteLibraryAgent(${agent.id}, '${escapeHtml(agent.name)}')">
                            🗑️
                        </button>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error loading agent library:', error);
        loading.style.display = 'none';
        empty.style.display = 'block';
        document.getElementById('libraryEmpty').innerHTML = `
            <div style="font-size: 60px; margin-bottom: 20px;">⚠️</div>
            <h3 style="color: #333; margin-bottom: 10px;">Error Loading Agents</h3>
            <p style="color: #666; margin-bottom: 20px;">Please try again later</p>
            <button onclick="closeAgentLibrary()" style="background: var(--primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer;">Close</button>
        `;
    }
}

function closeAgentLibrary() {
    document.getElementById('agentLibraryModal').style.display = 'none';
}

function chatWithLibraryAgent(agentName, agentId) {
    closeAgentLibrary();
    switchAgent(agentName);
    document.getElementById('messageInput').focus();
}

async function deleteLibraryAgent(agentId, agentName) {
    if (!confirm(`Delete "${agentName}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/custom-agents/${agentId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            // Reload the library
            openAgentLibrary();
            
            // Also remove from sidebar if it exists
            const sidebarAgents = document.querySelectorAll('.agent-item');
            sidebarAgents.forEach(item => {
                if (item.querySelector('.agent-name')?.textContent === agentName) {
                    item.remove();
                }
            });
        } else {
            alert('Failed to delete agent. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting agent:', error);
        alert('Error deleting agent. Please try again.');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

async function downloadFromUrl(url) {
    try {
        // Fetch the file to handle cross-origin resources
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch file');

        // Convert to blob
        const blob = await response.blob();

        // Create object URL and download
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objectUrl;

        // Try to extract filename from URL or use default
        const urlPath = new URL(url).pathname;
        const filename = urlPath.split('/').pop() || 'download_' + Date.now() + '.png';
        a.download = filename;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Clean up object URL
        URL.revokeObjectURL(objectUrl);
    } catch (error) {
        console.error('Download failed:', error);
        // Fallback to direct download for same-origin resources
        const a = document.createElement('a');
        a.href = url;
        a.download = 'download_' + Date.now() + '.png';
        a.click();
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('✅ Copied!');
    }).catch(() => {
        alert('Failed to copy');
    });
}
