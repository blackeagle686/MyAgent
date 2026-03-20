document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const runBtn = document.getElementById('run-btn');
    const outputPanel = document.getElementById('output-content');
    const themeToggle = document.getElementById('theme-toggle');
    const sidebar = document.getElementById('code-sidebar');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar');
    const aiLoading = document.getElementById('ai-loading');

    let monacoEditor;
    let chatHistory = [];
    let currentSummary = "";


    // ================== Monaco Editor ==================

    if (document.getElementById('monaco-editor')) {
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], function () {
            monacoEditor = monaco.editor.create(document.getElementById('monaco-editor'), {
                value: "# Your code will appear here...",
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                fontSize: 14,
                minimap: { enabled: false },
                roundedSelection: true,
                scrollbar: { vertical: 'visible', horizontal: 'visible', useShadows: false },
                suggestOnTriggerCharacters: true,
                quickSuggestions: { other: true, comments: false, strings: true },
                parameterHints: { enabled: true },
                tabCompletion: "on",
                wordBasedSuggestions: "allDocuments",
                bracketPairColorization: { enabled: true }
            });
        });
    }

    // ================== Toggle Sidebar ==================
    toggleSidebarBtn?.addEventListener('click', () => {
        sidebar?.classList.toggle('collapsed');
    });

    // ================== Theme Toggle ==================
    themeToggle?.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);

        monacoEditor && monaco.editor.setTheme(newTheme === 'light' ? 'vs' : 'vs-dark');

        const icon = themeToggle.querySelector('i');
        if (icon) icon.className = newTheme === 'light' ? 'bi bi-moon' : 'bi bi-sun';
    });

    // ================== Send Message ==================
    async function sendMessage(text) {
        console.log("Chat History:")
        console.log(chatHistory)
        console.log("Summary:")
        console.log(currentSummary)
        const message = text || messageInput?.value.trim();
        if (!message) return;

        // Hide Welcome Hero on first message
        const hero = document.getElementById('welcome-hero');
        if (hero) hero.remove();

        appendMessage('user', message);
        chatHistory.push({ role: 'user', content: message });

        if (messageInput) messageInput.value = '';
        if (messageInput) messageInput.disabled = true;
        if (sendBtn) sendBtn.disabled = true;

        aiLoading?.classList.remove('d-none');
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    history: chatHistory.slice(0, -1).slice(-10), // Send only last 10 as context
                    summary: currentSummary // Send existing summary
                })
            });

            const data = await response.json();
            aiLoading?.classList.add('d-none');

            if (response.ok) {
                appendMessage('ai', data.response);
                chatHistory.push({ role: 'ai', content: data.response });

                // If history gets long, summarize the older parts
                if (chatHistory.length >= 16) {
                    summarizeHistory();
                }

                extractCodeToEditor(data.response);
                if (data.response.includes('```')) sidebar?.classList.remove('collapsed');
            } else {
                appendMessage('ai', `Error: ${data.detail || 'Failed to get response'}`);
            }
        } catch (error) {
            aiLoading?.classList.add('d-none');
            appendMessage('ai', `Network Error: ${error.message}`);
        } finally {
            if (messageInput) messageInput.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
            messageInput?.focus();
        }
    }

    async function summarizeHistory() {
        console.log("History threshold met. Summarizing older context...");

        // Take first 10 messages to summarize
        const toSummarize = chatHistory.slice(0, 10);

        try {
            const response = await fetch('/api/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ history: toSummarize })
            });

            const data = await response.json();
            if (response.ok && data.summary) {
                // Combine with existing summary if any
                currentSummary = currentSummary
                    ? `Previously: ${currentSummary}\nThen: ${data.summary}`
                    : data.summary;

                // Remove those 10 messages from active history
                chatHistory = chatHistory.slice(10);
                console.log("Summary updated and history compressed.");
            }
        } catch (error) {
            console.error("Summarization failed:", error);
        }
    }



    sendBtn?.addEventListener('click', sendMessage);
    messageInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // ================== Run Code ==================
    runBtn?.addEventListener('click', async () => {
        if (!monacoEditor) return;

        const code = monacoEditor.getValue();
        if (!code.trim()) return;

        if (outputPanel) outputPanel.innerHTML = '<span class="text-muted">Running...</span>';

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });

            const result = await response.json();

            if (!outputPanel) return;

            if (result.error) {
                outputPanel.textContent = `Error:\n${result.stderr || 'Unknown execution error'}`;
                outputPanel.style.color = '#ff6b6b';
            } else {
                const output = result.stdout || result.stderr || '[No output received]';
                outputPanel.textContent = output;
                outputPanel.style.color = 'var(--text-color)';
            }

        } catch (error) {
            if (outputPanel) {
                outputPanel.textContent = `Execution Error: ${error.message}`;
                outputPanel.style.color = '#ff6b6b';
            }
        }
    });

    // ================== Marked Config ==================
    marked.setOptions({
        highlight: (code, lang) => {
            const language = hljs.getLanguage(lang) ? lang : 'python';
            return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-',
        breaks: true,
        gfm: true
    });

    // ================== Helpers ==================
    function appendMessage(role, text) {
        if (!chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const icon = document.createElement('i');
        icon.className = role === 'ai' ? 'bi bi-robot' : 'bi bi-person-fill';
        avatarDiv.appendChild(icon);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (role === 'ai') {
            contentDiv.innerHTML = marked.parse(text);

            contentDiv.querySelectorAll('pre').forEach((pre) => {
                const container = document.createElement('div');
                container.className = 'code-container position-relative';

                const btnGroup = document.createElement('div');
                btnGroup.className = 'code-actions position-absolute top-0 end-0 p-2 d-flex gap-2';

                const copyBtn = document.createElement('button');
                copyBtn.className = 'btn btn-sm btn-dark opacity-75';
                copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
                copyBtn.title = 'Copy code';
                copyBtn.onclick = () => {
                    const code = pre.querySelector('code')?.innerText || '';
                    navigator.clipboard.writeText(code);
                    copyBtn.innerHTML = '<i class="bi bi-check2"></i>';
                    setTimeout(() => copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>', 2000);
                };

                const editRunBtn = document.createElement('button');
                editRunBtn.className = 'btn btn-sm btn-dark opacity-75';
                editRunBtn.innerHTML = '<i class="bi bi-pencil-square"></i> Edit & Run';
                editRunBtn.title = 'Edit and run in editor';
                editRunBtn.onclick = () => {
                    const code = pre.querySelector('code')?.innerText || '';
                    if (monacoEditor) monacoEditor.setValue(code);
                    sidebar?.classList.remove('collapsed');
                    runBtn?.click();
                };

                btnGroup.appendChild(copyBtn);
                btnGroup.appendChild(editRunBtn);

                pre.parentNode.insertBefore(container, pre);
                container.appendChild(btnGroup);
                container.appendChild(pre);

                const codeBlock = pre.querySelector('code');
                if (codeBlock) hljs.highlightElement(codeBlock);
            });
        } else {
            const p = document.createElement('p');
            p.textContent = text;
            contentDiv.appendChild(p);
        }

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function extractCodeToEditor(text) {
        // Try Python specific block first
        let match = text.match(/```python\s([\s\S]*?)```/);

        // Fallback to generic block if no python block found
        if (!match) {
            match = text.match(/```\s?([\s\S]*?)```/);
        }

        if (match?.[1] && monacoEditor) {
            const code = match[1].trim();
            monacoEditor.setValue(code);
            // Ensure sidebar is visible when code is extracted
            sidebar?.classList.remove('collapsed');
        }
    }


    // Handle Suggestion Chips
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('suggestion-chip')) {
            const text = e.target.innerText.replace(/"/g, '');
            sendMessage(text);
        }
    });

});
