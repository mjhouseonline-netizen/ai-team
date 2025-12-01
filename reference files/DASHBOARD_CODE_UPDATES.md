# DASHBOARD.HTML - CRITICAL UPDATES FOR MODERN UI

## UPDATE 1: ADD MODEL SELECTOR (Add after line ~500, in the header area)

```html
<!-- Model Selector -->
<div class="model-selector-container" style="margin: 20px 0;">
    <label for="modelSelect" style="color: #90EE90; font-weight: 600; margin-right: 10px;">
        🤖 AI Model:
    </label>
    <select id="modelSelect" class="model-select" onchange="updateModelInfo()">
        <optgroup label="⚡ Claude (Anthropic)">
            <option value="claude-sonnet-4.5" selected>Sonnet 4.5 - Fast & Smart ($3/1M)</option>
            <option value="claude-opus-4">Opus 4 - Most Capable ($15/1M)</option>
            <option value="claude-haiku-4.5">Haiku 4.5 - Ultra Fast ($0.80/1M)</option>
        </optgroup>
        <optgroup label="🚀 GPT (OpenAI)">
            <option value="gpt-4o">GPT-4o - Latest Multimodal ($2.50/1M)</option>
            <option value="gpt-4-turbo">GPT-4 Turbo - Powerful ($10/1M)</option>
            <option value="gpt-4o-mini">GPT-4o Mini - Cheapest! ($0.15/1M)</option>
        </optgroup>
        <optgroup label="✨ Gemini (Google)">
            <option value="gemini-2.0-flash">Gemini 2.0 Flash - FREE Tier! 🎉</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro - 2M Context ($1.25/1M)</option>
        </optgroup>
    </select>
    <div id="modelInfo" style="margin-top: 10px; color: #90EE90; font-size: 0.9em;"></div>
</div>
```

## UPDATE 2: ADD MODERN CSS (Add to <style> section)

```css
/* Modern ChatGPT-Style Layout */
.model-select {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    border: 2px solid rgba(144, 238, 144, 0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 1em;
    min-width: 350px;
    cursor: pointer;
    transition: all 0.3s;
}

.model-select:hover {
    border-color: rgba(144, 238, 144, 0.6);
    background: rgba(255, 255, 255, 0.15);
}

.model-select optgroup {
    background: #1a4d2e;
    color: #FFD700;
    font-weight: bold;
    padding: 10px;
}

.model-select option {
    background: #1a4d2e;
    color: #fff;
    padding: 10px;
}

/* Chat Message Improvements */
.chat-message {
    margin: 15px 0;
    padding: 20px;
    border-radius: 12px;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    animation: fadeIn 0.3s;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message-user {
    background: rgba(144, 238, 144, 0.1);
    border-left: 4px solid #90EE90;
    text-align: left;
}

.message-agent {
    background: rgba(255, 255, 255, 0.05);
    border-left: 4px solid #FFD700;
}

.message-text {
    line-height: 1.6;
    word-wrap: break-word;
}

.model-badge {
    display: inline-block;
    background: rgba(144, 238, 144, 0.2);
    color: #90EE90;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85em;
    margin-left: 10px;
    border: 1px solid rgba(144, 238, 144, 0.4);
}

/* Preview Modal for Images */
.preview-modal {
    display: none;
    position: fixed;
    z-index: 99999;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.9);
    animation: fadeIn 0.3s;
}

.preview-modal-content {
    position: relative;
    margin: 5% auto;
    max-width: 90%;
    max-height: 90%;
    text-align: center;
}

.preview-modal-content img {
    max-width: 100%;
    max-height: 85vh;
    border-radius: 12px;
    box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
}

.preview-close {
    position: absolute;
    top: -40px;
    right: 0;
    color: #fff;
    font-size: 40px;
    font-weight: bold;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.1);
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
}

.preview-close:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: rotate(90deg);
}

/* Mobile Improvements */
@media (max-width: 768px) {
    .model-select {
        min-width: 100%;
        font-size: 0.9em;
    }
    
    .chat-message {
        padding: 15px;
        font-size: 0.95em;
    }
    
    .model-badge {
        display: block;
        margin: 10px 0 0 0;
    }
    
    .agent-card {
        padding: 15px;
    }
}

/* Clear Chat Button */
.clear-chat-btn {
    background: rgba(255, 107, 107, 0.2);
    color: #ff6b6b;
    border: 2px solid rgba(255, 107, 107, 0.4);
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    font-weight: 600;
}

.clear-chat-btn:hover {
    background: rgba(255, 107, 107, 0.3);
    transform: translateY(-2px);
}
```

## UPDATE 3: ADD PREVIEW MODAL HTML (Add before </body>)

```html
<!-- Image Preview Modal -->
<div id="previewModal" class="preview-modal" onclick="closePreview()">
    <span class="preview-close">&times;</span>
    <div class="preview-modal-content" onclick="event.stopPropagation()">
        <img id="previewImage" src="" alt="Preview">
    </div>
</div>
```

## UPDATE 4: UPDATE sendMessage FUNCTION (Replace existing sendMessage function)

```javascript
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message && !uploadedFile) return;
    
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';
    
    // Get selected model
    const selectedModel = document.getElementById('modelSelect').value;
    
    let displayMessage = message;
    if (uploadedFile) {
        displayMessage = `📎 ${uploadedFile.original_filename}\n${message}`;
    }
    
    addMessage(displayMessage || '📎 File uploaded', 'user');
    input.value = '';
    
    try {
        let endpoint = '/api/chat';
        let requestBody = {
            message: message || 'Please analyze this file',
            agent: currentAgent,
            model: selectedModel,  // NEW: Include selected model
            file: uploadedFile
        };

        // If in image mode, use image generation
        if (imageMode) {
            endpoint = '/api/generate-image-free';
            requestBody = {
                prompt: message,
                agent: currentAgent
            };
            
            addMessage('🎨 Generating your image...', 'agent', currentAgent);
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (imageMode && data.image_url) {
                const lastMsg = document.querySelector('.chat-message:last-child');
                if (lastMsg && lastMsg.textContent.includes('Generating')) {
                    lastMsg.remove();
                }
                
                let providerBadge = data.provider === 'pollinations' 
                    ? '<span class="model-badge">✨ FREE</span>'
                    : '<span class="model-badge">⭐ DALL-E 3</span>';
                
                addMessage(`Here's your generated image! ${providerBadge}`, 'agent', currentAgent, data.image_url);
            } else {
                // Add model badge to response
                const modelBadge = `<span class="model-badge">${getModelName(data.model_used || selectedModel)}</span>`;
                addMessage(data.response + modelBadge, 'agent', currentAgent);
            }
            loadStats();
        } else {
            addMessage('Error: ' + (data.error || 'Failed to get response'), 'agent', currentAgent);
        }
    } catch (error) {
        addMessage('Error: Failed to connect to server', 'agent', currentAgent);
    }
    
    if (uploadedFile) {
        removeFile();
    }
    
    if (imageMode) {
        toggleImageMode();
    }
    
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send 🚀';
}
```

## UPDATE 5: ADD NEW JAVASCRIPT FUNCTIONS (Add before closing </script>)

```javascript
// Model info display
function updateModelInfo() {
    const select = document.getElementById('modelSelect');
    const infoDiv = document.getElementById('modelInfo');
    const option = select.options[select.selectedIndex];
    const modelName = option.text;
    
    infoDiv.innerHTML = `Selected: <strong>${modelName}</strong>`;
}

// Get friendly model name
function getModelName(modelKey) {
    const models = {
        'claude-sonnet-4.5': 'Claude Sonnet 4.5',
        'claude-opus-4': 'Claude Opus 4',
        'claude-haiku-4.5': 'Claude Haiku 4.5',
        'gpt-4o': 'GPT-4o',
        'gpt-4-turbo': 'GPT-4 Turbo',
        'gpt-4o-mini': 'GPT-4o Mini',
        'gemini-2.0-flash': 'Gemini 2.0 Flash',
        'gemini-1.5-pro': 'Gemini 1.5 Pro'
    };
    return models[modelKey] || modelKey;
}

// Preview modal for images
function openPreview(imageSrc) {
    const modal = document.getElementById('previewModal');
    const img = document.getElementById('previewImage');
    modal.style.display = 'block';
    img.src = imageSrc;
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
}

// Clear chat history
async function clearChat() {
    if (!confirm('Clear all chat history with ' + currentAgent + '?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear-chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({agent: currentAgent})
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Clear chat container
            const container = document.getElementById('chatContainer');
            container.innerHTML = '<div class="welcome-message">Chat history cleared! Start a new conversation.</div>';
            alert('Chat history cleared!');
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Failed to clear chat');
    }
}

// Make images clickable for preview
function makeImagesClickable() {
    const images = document.querySelectorAll('.chat-message img');
    images.forEach(img => {
        img.style.cursor = 'pointer';
        img.onclick = () => openPreview(img.src);
    });
}

// Call after adding messages
setInterval(makeImagesClickable, 1000);

// Initialize model info on load
window.addEventListener('load', updateModelInfo);
```

## UPDATE 6: ADD CLEAR CHAT BUTTON (Add near the chat input area)

```html
<button onclick="clearChat()" class="clear-chat-btn" style="margin: 10px 0;">
    🗑️ Clear Chat History
</button>
```

---

# INTEGRATION NOTES:

1. Add these sections to your EXISTING dashboard.html
2. Keep all existing code - just add these new parts
3. Test each section after adding
4. The CSS goes in the <style> section
5. The JavaScript goes in the <script> section
6. The HTML gets added in appropriate places

This adds:
- ✅ Multi-model selector (8 models)
- ✅ Modern ChatGPT-style messages
- ✅ Preview modal for images
- ✅ Clear chat button
- ✅ Better mobile support
- ✅ Model badges on responses
