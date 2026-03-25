<script lang="ts">
    import { onMount, tick } from 'svelte';

    // --- TYPESCRIPT DEFINITIONS ---
    interface ChatMessage {
        id?: number;
        role: 'user' | 'bot' | string;
        content: string;
        usedTool?: boolean;
        copied?: boolean;
    }

    interface ChatSession {
        id: number;
        title: string;
        messages: ChatMessage[];
    }

    // CONFIG
    const API_URL = "http://127.0.0.1:8000/chat";
    const CLEAR_URL = "http://127.0.0.1:8000/clear";

    // STATE - Now strictly typed!
    let chatHistory: ChatSession[] = [];
    let currentSessionMessages: ChatMessage[] = [];
    let displayedMessages: ChatMessage[] = [];
    
    let inputText: string = '';
    let isTyping: boolean = false;
    let isSidebarClosed: boolean = false;
    let isReadOnly: boolean = false;
    let messagesContainer: HTMLElement;

    // INIT
    onMount(() => {
        const savedHistory = localStorage.getItem('genuine_webber_chats');
        if (savedHistory) {
            chatHistory = JSON.parse(savedHistory);
        }
        
        if (window.innerWidth < 768) {
            isSidebarClosed = true;
        }

        addMessageToUI("Hello! I am Genuine Webber. How can I help you today?", 'bot');
    });

    // --- SIDEBAR TOGGLE ---
    function toggleSidebar() {
        isSidebarClosed = !isSidebarClosed;
    }

    // --- COPY FUNCTION ---
    async function copyText(message: ChatMessage) {
        try {
            await navigator.clipboard.writeText(message.content);
            message.copied = true;
            displayedMessages = [...displayedMessages]; 
            
            setTimeout(() => {
                message.copied = false;
                displayedMessages = [...displayedMessages];
            }, 1500);
        } catch (err) {
            console.error('Failed to copy: ', err);
        }
    }

    // --- SCROLL TO BOTTOM ---
    async function scrollToBottom() {
        await tick();
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // --- ADD MESSAGE TO UI ---
    function addMessageToUI(text: string, sender: string, usedTool: boolean = false) {
        displayedMessages = [...displayedMessages, {
            id: Date.now() + Math.random(),
            content: text,
            role: sender,
            usedTool: usedTool,
            copied: false
        }];
        scrollToBottom();
    }

    // --- SEND MESSAGE ---
    async function sendMessage() {
        const text = inputText.trim();
        if (!text || isReadOnly) return;

        addMessageToUI(text, 'user');
        currentSessionMessages.push({ role: 'user', content: text });
        
        inputText = '';
        isTyping = true;
        scrollToBottom();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) throw new Error("Server Error");
            const data = await response.json();

            addMessageToUI(data.response, 'bot', data.used_tool);
            currentSessionMessages.push({ role: 'bot', content: data.response, usedTool: data.used_tool });

        } catch (error) {
            addMessageToUI("Error: Could not connect to server.", 'bot');
        } finally {
            isTyping = false;
            scrollToBottom();
            
            if (currentSessionMessages.length === 2) {
                saveCurrentSessionToHistory();
            }
        }
    }

    // --- NEW CHAT ---
    async function startNewChat() {
        if (currentSessionMessages.length > 0 && !isReadOnly) {
            saveCurrentSessionToHistory();
        }
        
        try { 
            await fetch(CLEAR_URL, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: "default" })
            });
        } catch (e) {
            console.error("Failed to clear backend memory");
        }
        
        isReadOnly = false;
        displayedMessages = [];
        currentSessionMessages = [];
        addMessageToUI("Started a new conversation.", 'bot');
        
        if (window.innerWidth < 768) {
            isSidebarClosed = true;
        }
    }

    // --- HISTORY MANAGEMENT ---
    function saveCurrentSessionToHistory() {
        if (currentSessionMessages.length < 2) return;
        
        // ADD HERE to get the content of the first message
        const summary = currentSessionMessages[0].content.substring(0, 25) + "..."; 
        
        const newSession: ChatSession = { 
            id: Date.now(), 
            title: summary, 
            messages: JSON.parse(JSON.stringify(currentSessionMessages)) 
        };
        
        chatHistory = [newSession, ...chatHistory];
        if (chatHistory.length > 20) chatHistory.pop();
        
        localStorage.setItem('genuine_webber_chats', JSON.stringify(chatHistory));
    }

    function loadHistory(id: number) {
        const session = chatHistory.find(c => c.id === id);
        if (!session) return;
        
        isReadOnly = true;
        currentSessionMessages = [];
        
        displayedMessages = session.messages.map(m => ({
            id: Date.now() + Math.random(),
            content: m.content,
            role: m.role,
            usedTool: m.usedTool,
            copied: false
        }));
        
        scrollToBottom();
        
        if (window.innerWidth < 768) {
            isSidebarClosed = true;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    }
</script>

<div class="app-container">
    <div class="sidebar" class:closed={isSidebarClosed}>
        <div class="logo-area">Genuine Webber</div>
        
        <button class="new-chat-btn" on:click={startNewChat}>
            <span>+</span> New Chat
        </button>

        <div class="history-label">Conversation History</div>
        <div class="history-list">
            {#each chatHistory as chat}
                <button class="history-item" on:click={() => loadHistory(chat.id)}>
                    <span>💬</span> {chat.title}
                </button>
            {/each}
        </div>
    </div>

    <div class="main-chat">
        <div class="chat-header">
            <div class="header-left">
                <button class="toggle-btn" on:click={toggleSidebar} title="Toggle Sidebar">
                    ☰
                </button>
                <div style="font-weight: 600; color: #374151;">WORKSPACE</div>
            </div>
            
            <div class="status-badge">
                <span class="status-dot"></span> Online
            </div>
        </div>

        <div class="messages-container" bind:this={messagesContainer}>
            {#if isReadOnly}
                <center style="color:#9ca3af; margin:10px; font-size:0.8rem">
                    Viewing Past Chat (Read-Only)
                </center>
            {/if}

            {#each displayedMessages as msg (msg.id)}
                <div class="message {msg.role}">
                    <div class="avatar">{msg.role === 'user' ? 'U' : 'G'}</div>
                    <div class="msg-content">
                        {#if msg.usedTool}
                            <div class="tool-badge">🔍 Search Tool Used</div>
                        {/if}
                        
                        {@html msg.content.replace(/\n/g, '<br>')}
                    </div>
                    
                    <button class="copy-btn" on:click={() => copyText(msg)} title="Copy text">
                        {#if msg.copied}
                            <span style="color: #10b981;">✅</span>
                        {:else}
                            📋
                        {/if}
                    </button>
                </div>
            {/each}

            {#if isTyping}
                <div class="typing">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
            {/if}
        </div>

        <div class="input-area">
            <div class="input-wrapper">
                <input 
                    type="text" 
                    bind:value={inputText} 
                    on:keydown={handleKeydown}
                    disabled={isTyping || isReadOnly}
                    placeholder={isReadOnly ? "Start a new chat to send a message..." : "Ask anything..."} 
                    autocomplete="off"
                >
                <button 
                    class="send-btn" 
                    on:click={sendMessage}
                    disabled={isTyping || isReadOnly || !inputText.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    </div>
</div>

<style>
    /* Scope global styles by wrapping everything in app-container */
    .app-container {
        --sidebar-width: 280px;
        --primary-color: #6366f1;
        --primary-hover: #4f46e5;
        --bg-dark: #111827;
        --bg-sidebar: #1f2937;
        --bg-chat: #ffffff;
        --text-light: #f3f4f6;
        --text-dark: #1f2937;
        --msg-user: #6366f1;
        --msg-bot: #f3f4f6;

        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        display: flex;
        height: 100vh;
        width: 100vw;
        background-color: var(--bg-dark);
        overflow: hidden;
    }

    /* --- SIDEBAR --- */
    .sidebar {
        width: var(--sidebar-width);
        background-color: var(--bg-sidebar);
        color: var(--text-light);
        display: flex;
        flex-direction: column;
        border-right: 1px solid #374151;
        transition: margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        flex-shrink: 0;
        z-index: 10;
    }

    .sidebar.closed {
        margin-left: calc(var(--sidebar-width) * -1);
    }

    .logo-area {
        padding: 20px;
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(to right, #6366f1, #a855f7);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-align: center;
        letter-spacing: 1px;
        border-bottom: 1px solid #374151;
        white-space: nowrap;
    }

    .new-chat-btn {
        margin: 20px;
        padding: 12px;
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: all 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    .new-chat-btn:hover {
        background-color: var(--primary-hover);
        transform: translateY(-2px);
    }

    .history-label {
        padding: 0 20px;
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #9ca3af;
        margin-bottom: 10px;
    }

    .history-list {
        flex: 1;
        overflow-y: auto;
        padding: 0 10px;
    }

    .history-item {
        /* New properties to reset button styles */
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        font-family: inherit;
        
        /* Original properties */
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: 6px;
        cursor: pointer;
        color: #d1d5db;
        font-size: 0.9rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        transition: background 0.2s;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .history-item:hover { background-color: #374151; }

    /* --- MAIN CHAT AREA --- */
    .main-chat {
        flex: 1;
        display: flex;
        flex-direction: column;
        background-color: var(--bg-chat);
        position: relative;
        width: 100%;
    }

    .chat-header {
        padding: 15px 25px;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        background: rgba(255,255,255,0.9);
        backdrop-filter: blur(5px);
        justify-content: space-between;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .toggle-btn {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 1.5rem;
        color: #374151;
        padding: 4px;
        border-radius: 6px;
        transition: background 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .toggle-btn:hover { background-color: #f3f4f6; }

    .status-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.85rem;
        color: #059669;
        background: #d1fae5;
        padding: 4px 12px;
        border-radius: 20px;
    }

    .status-dot { width: 8px; height: 8px; background: #059669; border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

    .messages-container {
        flex: 1;
        padding: 2rem;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        scroll-behavior: smooth;
    }

    .message {
        max-width: 80%;
        display: flex;
        gap: 1rem;
        opacity: 0;
        animation: slideIn 0.3s ease forwards;
        position: relative;
    }

    .copy-btn {
        position: absolute;
        top: -10px;
        right: -10px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        opacity: 0;
        transform: scale(0.8);
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #4b5563;
        font-size: 14px;
        z-index: 5;
    }

    .message:hover .copy-btn {
        opacity: 1;
        transform: scale(1);
    }

    .copy-btn:hover { background-color: #f3f4f6; color: var(--primary-color); }
    .copy-btn:active { transform: scale(0.9); }

    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message.user { align-self: flex-end; flex-direction: row-reverse; }
    .message.bot { align-self: flex-start; }

    .avatar {
        width: 35px;
        height: 35px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        flex-shrink: 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user .avatar { background: var(--primary-color); color: white; }
    .bot .avatar { background: var(--bg-dark); color: white; }

    .msg-content {
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 0.95rem;
        line-height: 1.5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        position: relative;
    }

    .user .msg-content {
        background: var(--msg-user);
        color: white;
        border-bottom-right-radius: 2px;
    }

    .bot .msg-content {
        background: var(--msg-bot);
        color: var(--text-dark);
        border-bottom-left-radius: 2px;
    }

    .tool-badge {
        display: inline-block;
        font-size: 0.7rem;
        background: rgba(0,0,0,0.05);
        color: #4b5563;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 6px;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* --- INPUT AREA --- */
    .input-area {
        padding: 20px;
        background: white;
        border-top: 1px solid #e5e7eb;
    }
    .input-wrapper {
        max-width: 900px;
        margin: 0 auto;
        position: relative;
        display: flex;
        gap: 10px;
    }
    input[type="text"] {
        flex: 1;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        outline: none;
        transition: all 0.3s;
        font-size: 1rem;
    }
    input[type="text"]:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    input[type="text"]:disabled {
        background-color: #f3f4f6;
        cursor: not-allowed;
    }
    button.send-btn {
        padding: 0 25px;
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.1s;
    }
    button.send-btn:active { transform: scale(0.95); }
    button.send-btn:disabled { background: #9ca3af; cursor: not-allowed; }

    .typing {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-left: 50px;
        margin-bottom: 10px;
    }
    .dot { width: 6px; height: 6px; background: #9ca3af; border-radius: 50%; animation: bounce 1.4s infinite; }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }

    /* Scrollbars */
    :global(::-webkit-scrollbar) { width: 6px; }
    :global(::-webkit-scrollbar-track) { background: transparent; }
    :global(::-webkit-scrollbar-thumb) { background: #cbd5e1; border-radius: 3px; }
    :global(body) { margin: 0; padding: 0; }
</style>