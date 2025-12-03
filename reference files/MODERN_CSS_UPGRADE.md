# 🎨 MODERN CSS UPGRADE - PASTE THIS INTO YOUR DASHBOARD

## Replace your entire `<style>` section with this modern CSS:

```css
/* ============================================
   MODERN CHATGPT-STYLE CSS
   Mobile-First, Clean, Professional
   ============================================ */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #10a37f;
    --primary-dark: #0d8c6f;
    --bg-main: #ffffff;
    --bg-secondary: #f9fafb;
    --bg-user: #f7f7f8;
    --text-primary: #374151;
    --text-secondary: #6b7280;
    --border: #e5e7eb;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg-main);
    color: var(--text-primary);
    line-height: 1.6;
    overflow-x: hidden;
}

/* Header - Modern & Clean */
.header, header {
    position: sticky;
    top: 0;
    background: var(--bg-main);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 1000;
    box-shadow: var(--shadow-sm);
}

.logo {
    font-size: 20px;
    font-weight: 600;
    color: var(--primary);
}

/* Dropdown Menu - Redesigned */
.dropdown-menu {
    position: absolute;
    top: 60px !important;
    right: 20px !important;
    background: white !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-lg) !important;
    padding: 8px !important;
    min-width: 200px !important;
    max-width: 200px !important;
    width: auto !important;
}

.dropdown-menu a {
    display: block;
    padding: 10px 14px !important;
    color: var(--text-primary) !important;
    text-decoration: none !important;
    border-radius: 6px !important;
    font-size: 14px !important;
    transition: all 0.2s !important;
    background: none !important;
    margin: 2px 0 !important;
}

.dropdown-menu a:hover {
    background: var(--bg-secondary) !important;
    color: var(--primary) !important;
}

/* Container - Centered like ChatGPT */
.container, .main-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}

/* Agent Cards - Modern Grid */
.agents-grid, .agent-grid {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)) !important;
    gap: 10px !important;
    padding: 20px !important;
    background: var(--bg-secondary) !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

.agent-card {
    background: white !important;
    border: 2px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
    text-align: center !important;
}

.agent-card:hover {
    border-color: var(--primary) !important;
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-md) !important;
}

.agent-card.active {
    background: var(--primary) !important;
    color: white !important;
    border-color: var(--primary) !important;
}

/* Model Selector - Clean & Modern */
.model-selector-container, .model-select-wrapper {
    padding: 16px 20px !important;
    background: white !important;
    border-bottom: 1px solid var(--border) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 12px !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

.model-select, #modelSelect {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    padding: 10px 16px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    color: var(--text-primary) !important;
    cursor: pointer !important;
    min-width: 280px !important;
    transition: all 0.2s !important;
}

.model-select:hover, #modelSelect:hover {
    border-color: var(--primary) !important;
}

.model-select:focus, #modelSelect:focus {
    outline: none !important;
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.1) !important;
}

/* Chat Container - Like ChatGPT */
#chatContainer, .chat-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding: 20px !important;
    min-height: calc(100vh - 400px) !important;
}

/* Messages - Modern Bubbles */
.chat-message {
    margin: 16px 0 !important;
    padding: 16px 0 !important;
    display: flex !important;
    gap: 12px !important;
}

.message-user {
    background: var(--bg-user) !important;
    margin: 16px -20px !important;
    padding: 20px !important;
    border-radius: 0 !important;
}

.message-agent {
    background: transparent !important;
}

.message-text {
    font-size: 15px !important;
    line-height: 1.7 !important;
    color: var(--text-primary) !important;
}

/* Input Area - ChatGPT Style */
.input-area {
    max-width: 900px !important;
    margin: 0 auto !important;
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    box-shadow: var(--shadow-sm) !important;
}

.input-area:focus-within {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.1) !important;
}

#messageInput {
    flex: 1 !important;
    border: none !important;
    background: none !important;
    font-size: 15px !important;
    outline: none !important;
    resize: none !important;
    font-family: inherit !important;
    color: var(--text-primary) !important;
    line-height: 1.5 !important;
    padding: 4px !important;
}

#messageInput::placeholder {
    color: var(--text-secondary) !important;
}

/* Buttons - Modern Style */
button, .btn, .send-btn, #sendBtn {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}

button:hover, .btn:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-1px) !important;
}

button:disabled {
    background: var(--border) !important;
    cursor: not-allowed !important;
    transform: none !important;
}

.attach-btn, .voice-input-btn, .image-btn {
    background: none !important;
    color: var(--text-secondary) !important;
    padding: 8px !important;
    font-size: 20px !important;
    border-radius: 6px !important;
}

.attach-btn:hover, .voice-input-btn:hover, .image-btn:hover {
    background: rgba(0, 0, 0, 0.05) !important;
    transform: none !important;
}

/* Stats Bar - Minimal */
.stats-bar {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: white !important;
    border-top: 1px solid var(--border) !important;
    padding: 12px 20px !important;
    display: flex !important;
    justify-content: center !important;
    gap: 24px !important;
    font-size: 13px !important;
    color: var(--text-secondary) !important;
    z-index: 100 !important;
}

.stat-item {
    display: flex !important;
    gap: 8px !important;
    align-items: center !important;
}

/* Tabs - Clean */
.tabs {
    display: flex !important;
    gap: 8px !important;
    padding: 16px 20px 0 !important;
    border-bottom: 1px solid var(--border) !important;
    background: white !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

.tab {
    background: none !important;
    border: none !important;
    padding: 10px 16px !important;
    cursor: pointer !important;
    color: var(--text-secondary) !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s !important;
    font-size: 14px !important;
}

.tab.active {
    color: var(--primary) !important;
    border-bottom-color: var(--primary) !important;
}

.tab:hover {
    color: var(--text-primary) !important;
    background: none !important;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .header {
        padding: 10px 16px !important;
    }
    
    .agents-grid, .agent-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        padding: 16px !important;
        gap: 8px !important;
    }
    
    .agent-card {
        padding: 12px !important;
        font-size: 14px !important;
    }
    
    .model-selector-container {
        padding: 12px 16px !important;
    }
    
    .model-select, #modelSelect {
        min-width: 100% !important;
        font-size: 13px !important;
    }
    
    #chatContainer, .chat-container {
        padding: 16px !important;
    }
    
    .message-user {
        margin: 16px -16px !important;
        padding: 16px !important;
    }
    
    .message-text {
        font-size: 14px !important;
    }
    
    .input-area {
        padding: 10px 12px !important;
    }
    
    #messageInput {
        font-size: 14px !important;
    }
    
    .stats-bar {
        gap: 16px !important;
        font-size: 12px !important;
        padding: 10px 16px !important;
    }
    
    .dropdown-menu {
        right: 16px !important;
        left: 16px !important;
        max-width: none !important;
    }
}

@media (max-width: 480px) {
    .logo {
        font-size: 16px !important;
    }
    
    .agents-grid {
        grid-template-columns: repeat(2, 1fr) !important;
    }
    
    .stats-bar {
        flex-wrap: wrap !important;
        justify-content: space-around !important;
    }
}

/* Remove old jungle theme */
.jungle-bg, .tropical-theme {
    background: var(--bg-main) !important;
}

/* Clean up any green gradients */
.gradient-green, .jungle-gradient {
    background: white !important;
}

/* Override any remaining old styles */
h1, h2, h3 {
    color: var(--text-primary) !important;
}

a {
    color: var(--primary) !important;
}

a:hover {
    color: var(--primary-dark) !important;
}
```

## 🚀 HOW TO APPLY:

1. **Open your current dashboard.html**
2. **Find the `<style>` section** (starts around line 7)
3. **Replace EVERYTHING between `<style>` and `</style>`** with the CSS above
4. **Save and deploy**

That's it! Your dashboard will look modern while keeping ALL features!

## ✅ WHAT THIS CHANGES:

- ❌ Removes jungle green theme
- ✅ Adds clean white/minimal design
- ✅ ChatGPT-style centered layout
- ✅ Better mobile responsive
- ✅ Modern buttons and inputs
- ✅ Professional appearance
- ✅ Keeps ALL your features!

## 🎨 COLOR CUSTOMIZATION:

Want to keep some green accents? Change this in the CSS:
```css
:root {
    --primary: #10a37f;  /* Change this color */
}
```

Try:
- `#10a37f` - Teal (ChatGPT style)
- `#2e7d32` - Green (keep jungle vibe but modern)
- `#5436da` - Purple (Claude style)
- `#0066ff` - Blue (professional)

---

This is the FASTEST way to modernize your UI without losing any features! 🚀
