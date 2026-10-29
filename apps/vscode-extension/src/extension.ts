import * as vscode from 'vscode';
import WebSocket = require('ws');
import {
    Ticket,
    TicketAssignedEvent,
    DeveloperContextSubmission,
    ConnectionStatus,
    SubmitContextMessage,
    RunAiMessage,
    FetchJiraMessage,
    WebviewReadyMessage,
    AiAnalysisResult
} from './types';

function escapeHtml(value: string | undefined | null): string {
    if (value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

let latestTicket: Ticket | undefined;
let latestAiAnalysis: AiAnalysisResult | undefined;
let socket: WebSocket | undefined;
let connectionStatus: ConnectionStatus = 'disconnected';
let currentPanel: vscode.WebviewPanel | undefined;
let isAutoConnect = false;
let isManualDisconnect = false;
let reconnectAttempts = 0;
const reconnectDelays = [2000, 5000, 10000, 30000, 30000];
let reconnectTimer: NodeJS.Timeout | undefined;
let recentTickets: Ticket[] = [];

export function activate(context: vscode.ExtensionContext) {
    let clientId = context.globalState.get<string>('clientId');
    if (!clientId) {
        clientId = `vscode-client-${Date.now()}`;
        context.globalState.update('clientId', clientId);
    }

    latestTicket = context.workspaceState.get<Ticket>('latestTicket');
    recentTickets = context.workspaceState.get<Ticket[]>('recentTickets') ?? [];

    const outputChannel = vscode.window.createOutputChannel('Jira Assistant');
    outputChannel.show(true);
    outputChannel.appendLine('Jira Assistant Extension activated.');

    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left,
        100
    );
    statusBarItem.command = 'jira-assistant.statusBarMenu';
    statusBarItem.show();

    function updateStatusBar() {
        switch (connectionStatus) {
            case 'connected':
                statusBarItem.text = '$(plug) Jira Assistant: Connected';
                statusBarItem.tooltip = 'Connected to Jira Assistant Backend';
                break;
            case 'connecting':
                statusBarItem.text = '$(sync~spin) Jira Assistant: Connecting';
                statusBarItem.tooltip = 'Connecting to Jira Assistant Backend...';
                break;
            case 'disconnected':
                statusBarItem.text = '$(circle-slash) Jira Assistant: Disconnected';
                statusBarItem.tooltip = 'Click to connect or view menu';
                break;
            default:
                statusBarItem.text = '$(warning) Jira Assistant: Error';
                statusBarItem.tooltip = 'Connection error';
        }
    }

    function getConfig() {
        const config = vscode.workspace.getConfiguration('jiraAssistant');
        return {
            backendUrl: config.get<string>('backendUrl') || 'http://localhost:8000',
            websocketUrl: config.get<string>('websocketUrl') || 'ws://localhost:8000/ws/client',
            autoConnect: config.get<boolean>('autoConnect') ?? true,
            showNotifications: config.get<boolean>('showNotifications') ?? true,
            userEmail: config.get<string>('userEmail') || 'developer@example.com'
        };
    }

    // Helper: Build Webview HTML
    function getWebviewHtml(ticket: Ticket | undefined, aiResult: AiAnalysisResult | undefined): string {
        const ticketKey = ticket?.key || 'NO-TICKET';
        const title = ticket?.title || 'No active Jira ticket';
        const description = ticket?.description || 'No description provided.';
        const status = ticket?.status || 'To Do';
        const priority = ticket?.priority || 'Medium';
        const url = ticket?.url || 'https://jira.atlassian.com';
        const assigneeEmail = ticket?.assigneeEmail || 'developer@example.com';
        const assigneeName = ticket?.assigneeDisplayName || assigneeEmail.split('@')[0];
        const comments = ticket?.comments || [];

        const priorityColor =
            priority.toLowerCase() === 'high' ? '#e53e3e' :
            priority.toLowerCase() === 'low' ? '#3182ce' : '#dd6b20';

        const statusColor =
            status.toLowerCase().includes('done') ? '#38a169' :
            status.toLowerCase().includes('progress') ? '#3182ce' : '#718096';

        const commentsHtml = comments.length > 0
            ? comments.map(c => `
                <div class="comment-item">
                    <span class="comment-author">${escapeHtml(c.author || 'Team Member')}</span>
                    <p class="comment-body">${escapeHtml(c.body)}</p>
                </div>
            `).join('')
            : '<p class="empty-text">No comments on this ticket.</p>';

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jira Assistant</title>
    <style>
        :root {
            --bg-color: var(--vscode-editor-background, #1e1e1e);
            --card-bg: var(--vscode-sideBar-background, #252526);
            --text-color: var(--vscode-editor-foreground, #cccccc);
            --border-color: var(--vscode-panel-border, #3c3c3c);
            --accent-color: var(--vscode-button-background, #0e639c);
            --accent-hover: var(--vscode-button-hoverBackground, #1177bb);
            --accent-text: var(--vscode-button-foreground, #ffffff);
            --input-bg: var(--vscode-input-background, #3c3c3c);
            --input-fg: var(--vscode-input-foreground, #cccccc);
            --input-border: var(--vscode-input-border, #454545);
            --code-bg: var(--vscode-textCodeBlock-background, #181818);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
            font-size: var(--vscode-font-size, 13px);
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 16px;
            line-height: 1.5;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 16px;
        }
        .header h1 {
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-badge {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 12px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #48bb78;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .ticket-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-color);
        }
        .badge {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: inline-block;
        }
        .badge-key {
            background: rgba(14, 99, 156, 0.25);
            color: #4fc1ff;
            border: 1px solid rgba(14, 99, 156, 0.5);
            text-decoration: none;
        }
        .badge-key:hover { text-decoration: underline; }
        .meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 12px;
            font-size: 12px;
            color: #888;
        }
        .meta-item strong { color: var(--text-color); font-weight: 500; }
        .description-box {
            background: rgba(0, 0, 0, 0.15);
            padding: 10px 12px;
            border-radius: 4px;
            margin-bottom: 12px;
            white-space: pre-wrap;
            font-size: 12.5px;
        }
        .section-title {
            font-size: 13px;
            font-weight: 600;
            margin: 12px 0 6px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #999;
        }
        .comment-item {
            border-left: 2px solid var(--accent-color);
            padding-left: 8px;
            margin-bottom: 8px;
        }
        .comment-author {
            font-size: 11px;
            font-weight: 600;
            color: #4fc1ff;
        }
        .comment-body {
            font-size: 12px;
            margin-top: 2px;
        }
        .fetch-bar {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }
        input[type="text"], textarea {
            width: 100%;
            background: var(--input-bg);
            color: var(--input-fg);
            border: 1px solid var(--input-border);
            border-radius: 4px;
            padding: 8px 10px;
            font-family: inherit;
            font-size: 13px;
        }
        input[type="text"]:focus, textarea:focus {
            outline: 1px solid var(--accent-color);
            border-color: var(--accent-color);
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        .btn-group {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        button {
            background: var(--accent-color);
            color: var(--accent-text);
            border: none;
            padding: 8px 14px;
            font-size: 12.5px;
            font-weight: 500;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: background 0.15s ease;
        }
        button:hover {
            background: var(--accent-hover);
        }
        button.secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-color);
        }
        button.secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        button.primary-ai {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: #ffffff;
            font-weight: 600;
            box-shadow: 0 2px 6px rgba(124, 58, 237, 0.3);
        }
        button.primary-ai:hover {
            background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ai-result-card {
            border: 1px solid rgba(124, 58, 237, 0.4);
            background: rgba(30, 27, 75, 0.25);
            border-radius: 6px;
            padding: 16px;
            margin-top: 16px;
        }
        .ai-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            border-bottom: 1px solid rgba(124, 58, 237, 0.2);
            padding-bottom: 8px;
        }
        .ai-title {
            font-size: 14px;
            font-weight: 600;
            color: #c4b5fd;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .ai-content {
            font-size: 13px;
            line-height: 1.6;
            color: #e2e8f0;
        }
        .ai-content pre {
            background: var(--code-bg);
            border: 1px solid var(--border-color);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 10px 0;
            font-family: var(--vscode-editor-font-family, monospace);
        }
        .ai-content code {
            font-family: var(--vscode-editor-font-family, monospace);
            background: rgba(255, 255, 255, 0.08);
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 12px;
        }
        .ai-content ul, .ai-content ol {
            padding-left: 20px;
            margin: 8px 0;
        }
        .ai-content h3 {
            margin: 12px 0 6px 0;
            color: #a78bfa;
            font-size: 14px;
        }
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .empty-text {
            color: #888;
            font-style: italic;
            font-size: 12px;
        }
        .alert-box {
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 12px;
            font-size: 12px;
        }
        .alert-success { background: rgba(56, 161, 105, 0.2); border: 1px solid #38a169; color: #68d391; }
        .alert-error { background: rgba(229, 62, 62, 0.2); border: 1px solid #e53e3e; color: #fc8181; }
        .alert-info { background: rgba(49, 130, 206, 0.2); border: 1px solid #3182ce; color: #63b3ed; }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span>⚡ Jira Assistant</span>
        </h1>
        <div class="status-badge" style="background: rgba(72, 187, 120, 0.15); color: #48bb78; border: 1px solid rgba(72, 187, 120, 0.3);">
            <div class="status-dot"></div>
            <span>Backend Connected</span>
        </div>
    </div>

    <!-- Real Jira Fetch Bar -->
    <div class="fetch-bar">
        <input type="text" id="jiraKeyInput" placeholder="Enter Jira Ticket Key (e.g. PROJ-101, DEV-42)..." value="${escapeHtml(ticketKey !== 'NO-TICKET' ? ticketKey : '')}" />
        <button id="fetchBtn" title="Fetch live ticket from Jira API or local database">
            <span>📥 Fetch Ticket</span>
        </button>
    </div>

    <div id="notificationArea"></div>

    <!-- Active Ticket Card -->
    <div class="card">
        <div class="card-header">
            <div>
                <a class="badge badge-key" href="${escapeHtml(url)}" target="_blank" title="Open in Jira">
                    ${escapeHtml(ticketKey)} ↗
                </a>
                <span class="badge" style="background: ${priorityColor}22; color: ${priorityColor}; border: 1px solid ${priorityColor}55; margin-left: 6px;">
                    ${escapeHtml(priority)}
                </span>
                <span class="badge" style="background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}55; margin-left: 6px;">
                    ${escapeHtml(status)}
                </span>
            </div>
            <span style="font-size: 11px; color: #888;">${escapeHtml(ticket?.receivedAt || 'Recent')}</span>
        </div>

        <div class="ticket-title">${escapeHtml(title)}</div>

        <div class="meta-row">
            <div class="meta-item">Assignee: <strong>${escapeHtml(assigneeName)}</strong> (${escapeHtml(assigneeEmail)})</div>
            <div class="meta-item">Project: <strong>${escapeHtml(ticket?.projectKey || 'N/A')}</strong></div>
        </div>

        <div class="section-title">Description</div>
        <div class="description-box">${escapeHtml(description)}</div>

        <div class="section-title">Comments & Activity (${comments.length})</div>
        <div class="comments-container">
            ${commentsHtml}
        </div>
    </div>

    <!-- Developer Workspace Context Submission -->
    <div class="card">
        <div class="section-title" style="margin-top:0;">Developer Context & Workspace Notes</div>
        <p style="font-size: 12px; color: #888; margin-bottom: 8px;">
            Add notes, error traces, or questions. These are saved to the database and included in the AI analysis prompt.
        </p>

        <textarea id="contextBox" placeholder="e.g., Encountered 401 error in auth_interceptor.ts. Need implementation steps and test cases..."></textarea>
        <p id="errorMsg" style="color: #fc8181; font-size: 12px; margin-top: 4px; display: none;"></p>

        <div class="btn-group">
            <button id="runAiBtn" class="primary-ai" title="Analyze with OpenAI">
                <span>✨ Run AI Analysis</span>
            </button>
            <button id="submitContextBtn" class="secondary" title="Save developer context to database">
                <span>💾 Save Context</span>
            </button>
            <button id="clearBtn" class="secondary" title="Clear text area">
                <span>Clear</span>
            </button>
        </div>
    </div>

    <!-- AI Analysis Card -->
    <div id="aiCard" class="ai-result-card" style="${aiResult ? 'display:block;' : 'display:none;'}">
        <div class="ai-header">
            <div class="ai-title">
                <span>🤖 AI Technical Implementation Plan</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span id="aiModelBadge" style="font-size: 11px; color: #a78bfa; background: rgba(167, 139, 250, 0.15); padding: 2px 6px; border-radius: 4px;">
                    ${escapeHtml(aiResult?.model || 'OpenAI')}
                </span>
                <button id="copyAiBtn" class="secondary" style="padding: 4px 8px; font-size: 11px;">Copy Plan</button>
            </div>
        </div>
        <div id="aiContentArea" class="ai-content">
            ${formatMarkdown(aiResult?.analysis || '')}
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        window.onload = () => {
            vscode.postMessage({ type: 'webviewReady' });
        };

        const contextBox = document.getElementById('contextBox');
        const errorMsg = document.getElementById('errorMsg');
        const runAiBtn = document.getElementById('runAiBtn');
        const submitBtn = document.getElementById('submitContextBtn');
        const clearBtn = document.getElementById('clearBtn');
        const fetchBtn = document.getElementById('fetchBtn');
        const jiraKeyInput = document.getElementById('jiraKeyInput');
        const aiCard = document.getElementById('aiCard');
        const aiContentArea = document.getElementById('aiContentArea');
        const aiModelBadge = document.getElementById('aiModelBadge');
        const copyAiBtn = document.getElementById('copyAiBtn');
        const notificationArea = document.getElementById('notificationArea');

        function showNotification(text, type = 'info') {
            notificationArea.innerHTML = '<div class="alert-box alert-' + type + '">' + text + '</div>';
            setTimeout(() => {
                notificationArea.innerHTML = '';
            }, 5000);
        }

        // Fetch Jira Ticket button
        fetchBtn.addEventListener('click', () => {
            const key = jiraKeyInput.value.trim();
            if (!key) {
                showNotification('Please enter a Jira ticket key to fetch.', 'error');
                return;
            }
            fetchBtn.disabled = true;
            fetchBtn.innerHTML = '<span class="spinner"></span> Fetching...';
            vscode.postMessage({
                type: 'fetch_jira',
                ticketKey: key
            });
        });

        // Run AI Analysis button
        runAiBtn.addEventListener('click', () => {
            const ticketKey = "${escapeHtml(ticketKey)}";
            if (!ticketKey || ticketKey === 'NO-TICKET') {
                showNotification('Please fetch or select an active ticket first.', 'error');
                return;
            }
            runAiBtn.disabled = true;
            runAiBtn.innerHTML = '<span class="spinner"></span> Analyzing with AI...';

            aiCard.style.display = 'block';
            aiContentArea.innerHTML = '<p style="color: #a78bfa;"><span class="spinner"></span> Consulting AI architecture model for implementation plan, root cause, and test strategy...</p>';

            vscode.postMessage({
                type: 'run_ai',
                ticketKey: ticketKey,
                additionalContext: contextBox.value.trim()
            });
        });

        // Submit Context button
        submitBtn.addEventListener('click', () => {
            const text = contextBox.value.trim();
            if (!text) {
                errorMsg.innerText = 'Cannot submit empty developer context.';
                errorMsg.style.display = 'block';
                return;
            }
            errorMsg.style.display = 'none';
            submitBtn.disabled = true;
            submitBtn.innerText = 'Saving...';

            vscode.postMessage({
                type: 'submit_context',
                ticketKey: "${escapeHtml(ticketKey)}",
                additionalContext: text
            });
        });

        // Clear Context
        clearBtn.addEventListener('click', () => {
            contextBox.value = '';
            errorMsg.style.display = 'none';
        });

        // Copy AI output
        copyAiBtn.addEventListener('click', () => {
            const text = aiContentArea.innerText;
            navigator.clipboard.writeText(text).then(() => {
                copyAiBtn.innerText = 'Copied!';
                setTimeout(() => { copyAiBtn.innerText = 'Copy Plan'; }, 2000);
            });
        });

        // Handle incoming messages from extension
        window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'focusContext') {
                contextBox.focus();
            } else if (msg.type === 'ai_result') {
                runAiBtn.disabled = false;
                runAiBtn.innerHTML = '<span>✨ Run AI Analysis</span>';
                aiCard.style.display = 'block';
                aiModelBadge.innerText = msg.result.model || 'OpenAI';
                aiContentArea.innerHTML = renderMarkdownInBrowser(msg.result.analysis);
                showNotification('AI analysis generated and saved to database!', 'success');
            } else if (msg.type === 'ai_error') {
                runAiBtn.disabled = false;
                runAiBtn.innerHTML = '<span>✨ Run AI Analysis</span>';
                aiContentArea.innerHTML = '<p style="color: #fc8181;">' + msg.error + '</p>';
                showNotification('AI analysis failed: ' + msg.error, 'error');
            } else if (msg.type === 'context_submitted') {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>💾 Save Context</span>';
                showNotification('Developer context saved to SQLite database.', 'success');
            } else if (msg.type === 'fetch_complete') {
                fetchBtn.disabled = false;
                fetchBtn.innerHTML = '<span>📥 Fetch Ticket</span>';
            }
        });

        function renderMarkdownInBrowser(md) {
            if (!md) return '';
            let html = md
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                .replace(/^## (.*$)/gim, '<h2 style="font-size:15px; margin: 12px 0 6px 0; color:#c4b5fd;">$1</h2>')
                .replace(/^# (.*$)/gim, '<h1 style="font-size:16px; margin: 14px 0 8px 0; color:#c4b5fd;">$1</h1>')
                .replace(new RegExp('\\x60\\x60\\x60([a-z]*)\\n([\\s\\S]*?)\\n\\x60\\x60\\x60', 'gm'), '<pre><code>$2</code></pre>')
                .replace(new RegExp('\\x60([^\\x60]+)\\x60', 'g'), '<code>$1</code>')
                .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/^- \\[ \\] (.*$)/gim, '<li style="list-style:none;">⬜ $1</li>')
                .replace(/^- \\[x\\] (.*$)/gim, '<li style="list-style:none;">✅ $1</li>')
                .replace(/^\\* (.*$)/gim, '<li>$1</li>')
                .replace(/^- (.*$)/gim, '<li>$1</li>')
                .replace(/\\n/g, '<br/>');
            return html;
        }
    </script>
</body>
</html>`;
    }

    function formatMarkdown(text: string): string {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2 style="font-size:15px; margin: 12px 0 6px 0; color:#c4b5fd;">$1</h2>')
            .replace(/^# (.*$)/gim, '<h1 style="font-size:16px; margin: 14px 0 8px 0; color:#c4b5fd;">$1</h1>')
            .replace(/```([a-z]*)\n([\s\S]*?)\n```/gm, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^- \[ \] (.*$)/gim, '<li style="list-style:none;">⬜ $1</li>')
            .replace(/^- \[x\] (.*$)/gim, '<li style="list-style:none;">✅ $1</li>')
            .replace(/^\* (.*$)/gim, '<li>$1</li>')
            .replace(/^- (.*$)/gim, '<li>$1</li>')
            .replace(/\n/g, '<br/>');
    }

    // Command: openPanel
    const openPanel = vscode.commands.registerCommand(
        'jira-assistant.openPanel',
        async () => {
            if (currentPanel) {
                currentPanel.reveal(vscode.ViewColumn.One);
                currentPanel.webview.html = getWebviewHtml(latestTicket, latestAiAnalysis);
                return;
            }

            currentPanel = vscode.window.createWebviewPanel(
                'jiraAssistant',
                `Jira Assistant - ${latestTicket?.key || 'Dashboard'}`,
                vscode.ViewColumn.One,
                { enableScripts: true }
            );

            currentPanel.webview.html = getWebviewHtml(latestTicket, latestAiAnalysis);

            currentPanel.onDidDispose(() => {
                currentPanel = undefined;
            });

            // Message router from Webview to VS Code Extension
            currentPanel.webview.onDidReceiveMessage(async (message: any) => {
                const { backendUrl, userEmail } = getConfig();

                if (message.type === 'webviewReady') {
                    currentPanel?.webview.postMessage({ type: 'focusContext' });
                    return;
                }

                if (message.type === 'submit_context') {
                    const activeFile = vscode.window.activeTextEditor?.document.uri.fsPath;
                    const repoPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

                    const requestPayload: DeveloperContextSubmission = {
                        userEmail: userEmail,
                        additionalContext: message.additionalContext,
                        repoPath: repoPath,
                        activeFile: activeFile,
                        notes: ''
                    };

                    try {
                        const targetKey = message.ticketKey || latestTicket?.key;
                        const resp = await fetch(`${backendUrl}/tickets/${targetKey}/developer-context`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(requestPayload)
                        });

                        if (resp.ok) {
                            outputChannel.appendLine(`Context submitted and saved to DB for ticket: ${targetKey}`);
                            vscode.window.showInformationMessage('Developer context saved to database!');
                            currentPanel?.webview.postMessage({ type: 'context_submitted' });
                        } else {
                            const errBody = await resp.text();
                            outputChannel.appendLine(`Backend error submitting context: ${errBody}`);
                            vscode.window.showErrorMessage('Failed to save context to backend.');
                        }
                    } catch (e) {
                        outputChannel.appendLine(`Error submitting context: ${e}`);
                        vscode.window.showErrorMessage('Network error submitting context.');
                    }
                    return;
                }

                if (message.type === 'run_ai') {
                    const activeFile = vscode.window.activeTextEditor?.document.uri.fsPath;
                    const repoPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
                    const targetKey = message.ticketKey || latestTicket?.key;

                    outputChannel.appendLine(`Executing AI analysis for ticket ${targetKey}...`);

                    try {
                        const aiPayload = {
                            ticketKey: targetKey,
                            prompt: message.prompt,
                            additionalContext: message.additionalContext,
                            activeFile: activeFile,
                            repoPath: repoPath
                        };

                        const resp = await fetch(`${backendUrl}/tickets/${targetKey}/ai-analyze`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(aiPayload)
                        });

                        if (resp.ok) {
                            const result = await resp.json() as AiAnalysisResult;
                            latestAiAnalysis = result;
                            outputChannel.appendLine(`AI Analysis complete via ${result.provider} (${result.model})`);
                            currentPanel?.webview.postMessage({
                                type: 'ai_result',
                                result: result
                            });
                            vscode.window.showInformationMessage(`AI Plan generated for ${targetKey}!`);
                        } else {
                            const errorText = await resp.text();
                            outputChannel.appendLine(`AI endpoint returned error: ${errorText}`);
                            currentPanel?.webview.postMessage({
                                type: 'ai_error',
                                error: `Backend AI error: ${errorText}`
                            });
                            vscode.window.showErrorMessage('AI analysis failed. Check Jira Assistant output logs.');
                        }
                    } catch (e) {
                        outputChannel.appendLine(`AI request exception: ${e}`);
                        currentPanel?.webview.postMessage({
                            type: 'ai_error',
                            error: `Request error: ${String(e)}`
                        });
                        vscode.window.showErrorMessage('Could not connect to AI backend endpoint.');
                    }
                    return;
                }

                if (message.type === 'fetch_jira') {
                    const key = message.ticketKey;
                    outputChannel.appendLine(`Fetching Jira ticket ${key}...`);
                    try {
                        const resp = await fetch(`${backendUrl}/api/jira/fetch`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ticketKey: key, userEmail: userEmail })
                        });

                        currentPanel?.webview.postMessage({ type: 'fetch_complete' });

                        if (resp.ok) {
                            const data = await resp.json() as { ticket: any };
                            const t = data.ticket;
                            latestTicket = {
                                key: t.key,
                                title: t.title,
                                description: t.description,
                                status: t.status,
                                priority: t.priority,
                                url: t.url,
                                assigneeEmail: t.assignee_email,
                                assigneeDisplayName: t.assignee_name,
                                projectKey: t.project_key,
                                receivedAt: new Date().toLocaleString(),
                                comments: (t.comments || []).map((c: string) => ({ body: c }))
                            };

                            await context.workspaceState.update('latestTicket', latestTicket);
                            recentTickets = recentTickets.filter(item => item.key !== latestTicket?.key);
                            recentTickets.unshift(latestTicket);
                            recentTickets = recentTickets.slice(0, 10);
                            await context.workspaceState.update('recentTickets', recentTickets);

                            if (currentPanel) {
                                currentPanel.title = `Jira - ${latestTicket.key}`;
                                currentPanel.webview.html = getWebviewHtml(latestTicket, latestAiAnalysis);
                            }
                            vscode.window.showInformationMessage(`Fetched Jira ticket ${latestTicket.key}: ${latestTicket.title}`);
                        } else {
                            const errBody = await resp.text();
                            outputChannel.appendLine(`Fetch failed: ${errBody}`);
                            vscode.window.showWarningMessage(`Could not fetch ticket ${key}: ${errBody}`);
                        }
                    } catch (e) {
                        outputChannel.appendLine(`Fetch exception: ${e}`);
                        vscode.window.showErrorMessage(`Failed to contact backend to fetch Jira ticket.`);
                        currentPanel?.webview.postMessage({ type: 'fetch_complete' });
                    }
                }
            });
        }
    );

    // Command: Run AI directly
    const runAi = vscode.commands.registerCommand(
        'jira-assistant.runAi',
        async () => {
            if (!latestTicket) {
                vscode.window.showInformationMessage('No active Jira ticket. Please fetch or select a ticket first.');
                return;
            }
            await vscode.commands.executeCommand('jira-assistant.openPanel');
            currentPanel?.webview.postMessage({
                type: 'run_ai',
                ticketKey: latestTicket.key
            });
        }
    );

    // Command: Fetch Jira Ticket
    const fetchJiraTicket = vscode.commands.registerCommand(
        'jira-assistant.fetchJiraTicket',
        async () => {
            const key = await vscode.window.showInputBox({
                prompt: 'Enter Jira Ticket Key to fetch (e.g., PROJ-101, PROJ-123)',
                placeHolder: 'PROJ-101'
            });

            if (!key || !key.trim()) return;

            const { backendUrl, userEmail } = getConfig();
            outputChannel.appendLine(`Fetching ticket ${key} from backend...`);

            try {
                const resp = await fetch(`${backendUrl}/api/jira/fetch`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticketKey: key.trim(), userEmail })
                });

                if (resp.ok) {
                    const data = await resp.json() as { ticket: any };
                    const t = data.ticket;
                    latestTicket = {
                        key: t.key,
                        title: t.title,
                        description: t.description,
                        status: t.status,
                        priority: t.priority,
                        url: t.url,
                        assigneeEmail: t.assignee_email,
                        assigneeDisplayName: t.assignee_name,
                        projectKey: t.project_key,
                        receivedAt: new Date().toLocaleString(),
                        comments: (t.comments || []).map((c: string) => ({ body: c }))
                    };

                    await context.workspaceState.update('latestTicket', latestTicket);
                    recentTickets = recentTickets.filter(item => item.key !== latestTicket?.key);
                    recentTickets.unshift(latestTicket);
                    recentTickets = recentTickets.slice(0, 10);
                    await context.workspaceState.update('recentTickets', recentTickets);

                    await vscode.commands.executeCommand('jira-assistant.openPanel');
                    vscode.window.showInformationMessage(`Loaded Jira ticket ${latestTicket.key}!`);
                } else {
                    const err = await resp.text();
                    vscode.window.showErrorMessage(`Jira fetch error: ${err}`);
                }
            } catch (e) {
                vscode.window.showErrorMessage(`Backend unreachable: ${e}`);
            }
        }
    );

    // Command: openLatestTicket
    const openLatestTicket = vscode.commands.registerCommand(
        'jira-assistant.openLatestTicket',
        async () => {
            if (!latestTicket) {
                vscode.window.showInformationMessage('No Jira ticket received yet.');
                return;
            }
            await vscode.commands.executeCommand('jira-assistant.openPanel');
        }
    );

    // Command: showRecentTickets
    const showRecentTickets = vscode.commands.registerCommand(
        'jira-assistant.showRecentTickets',
        async () => {
            if (recentTickets.length === 0) {
                vscode.window.showInformationMessage('No recent Jira tickets.');
                return;
            }

            const selected = await vscode.window.showQuickPick(
                recentTickets.map(t => ({
                    label: `${t.key} - ${t.title}`,
                    description: t.status,
                    detail: t.description ? t.description.slice(0, 80) : '',
                    ticket: t
                }))
            );

            if (!selected) return;

            latestTicket = selected.ticket;
            await vscode.commands.executeCommand('jira-assistant.openPanel');
        }
    );

    // Command: disconnectBackend
    const disconnectBackend = vscode.commands.registerCommand(
        'jira-assistant.disconnectBackend',
        () => {
            isManualDisconnect = true;
            socket?.close();
            connectionStatus = 'disconnected';
            updateStatusBar();
            vscode.window.showInformationMessage('Backend disconnected.');
        }
    );

    // Command: reconnectBackend
    const reconnectBackend = vscode.commands.registerCommand(
        'jira-assistant.reconnectBackend',
        async () => {
            socket?.close();
            connectionStatus = 'disconnected';
            await vscode.commands.executeCommand('jira-assistant.connectBackend');
        }
    );

    // Command: openSettings
    const openSettings = vscode.commands.registerCommand(
        'jira-assistant.openSettings',
        async () => {
            await vscode.commands.executeCommand(
                'workbench.action.openSettings',
                'jiraAssistant'
            );
        }
    );

    // Command: showConnectionStatus
    const showConnectionStatus = vscode.commands.registerCommand(
        'jira-assistant.showConnectionStatus',
        () => {
            vscode.window.showInformationMessage(`Jira Assistant connection status: ${connectionStatus}`);
        }
    );

    // Command: statusBarMenu
    const statusBarMenu = vscode.commands.registerCommand(
        'jira-assistant.statusBarMenu',
        async () => {
            const action = await vscode.window.showQuickPick([
                'Open Ticket & AI Panel',
                'Run AI Analysis',
                'Fetch Real Jira Ticket',
                'Show Recent Tickets',
                'Connect Backend',
                'Disconnect Backend',
                'Reconnect Backend',
                'Open Settings'
            ], { placeHolder: 'Jira Assistant Quick Actions' });

            switch (action) {
                case 'Open Ticket & AI Panel':
                    await vscode.commands.executeCommand('jira-assistant.openPanel');
                    break;
                case 'Run AI Analysis':
                    await vscode.commands.executeCommand('jira-assistant.runAi');
                    break;
                case 'Fetch Real Jira Ticket':
                    await vscode.commands.executeCommand('jira-assistant.fetchJiraTicket');
                    break;
                case 'Show Recent Tickets':
                    await vscode.commands.executeCommand('jira-assistant.showRecentTickets');
                    break;
                case 'Connect Backend':
                    await vscode.commands.executeCommand('jira-assistant.connectBackend');
                    break;
                case 'Disconnect Backend':
                    await vscode.commands.executeCommand('jira-assistant.disconnectBackend');
                    break;
                case 'Reconnect Backend':
                    await vscode.commands.executeCommand('jira-assistant.reconnectBackend');
                    break;
                case 'Open Settings':
                    await vscode.commands.executeCommand('jira-assistant.openSettings');
                    break;
            }
        }
    );

    // Command: mockTicket
    const mockTicket = vscode.commands.registerCommand(
        'jira-assistant.mockTicket',
        async () => {
            const { backendUrl, userEmail } = getConfig();
            try {
                await fetch(`${backendUrl}/dev/mock-ticket`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ticketKey: 'PROJ-123',
                        title: 'Fix login redirect issue',
                        assigneeEmail: userEmail
                    })
                });
            } catch (e) {
                outputChannel.appendLine(`Mock ticket error: ${e}`);
            }
        }
    );

    function scheduleReconnect() {
        if (reconnectTimer) return;
        const delay = reconnectDelays[Math.min(reconnectAttempts, reconnectDelays.length - 1)];
        outputChannel.appendLine(`Reconnect scheduled in ${delay / 1000} seconds`);
        reconnectTimer = setTimeout(() => {
            reconnectTimer = undefined;
            reconnectAttempts++;
            vscode.commands.executeCommand('jira-assistant.connectBackend');
        }, delay);
    }

    // Command: connectBackend
    const connectBackend = vscode.commands.registerCommand(
        'jira-assistant.connectBackend',
        () => {
            const { websocketUrl, userEmail } = getConfig();

            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = undefined;
            }

            if (socket) {
                if (socket.readyState === WebSocket.OPEN) {
                    vscode.window.showInformationMessage('Already connected to backend.');
                    return;
                }
                if (socket.readyState === WebSocket.CONNECTING) {
                    vscode.window.showInformationMessage('Connection is already in progress.');
                    return;
                }
            }

            connectionStatus = 'connecting';
            updateStatusBar();

            outputChannel.appendLine(`Connecting to WebSocket: ${websocketUrl}`);
            try {
                socket = new WebSocket(websocketUrl);
            } catch (err) {
                connectionStatus = 'disconnected';
                updateStatusBar();
                outputChannel.appendLine(`Socket creation failed: ${err}`);
                return;
            }

            socket.on('open', () => {
                connectionStatus = 'connected';
                updateStatusBar();
                isAutoConnect = false;
                reconnectAttempts = 0;
                outputChannel.appendLine('Connected to backend WebSocket successfully.');

                socket!.send(JSON.stringify({
                    type: 'client_register',
                    userEmail: userEmail,
                    clientId: clientId
                }));
            });

            socket.on('message', async (data) => {
                try {
                    const message = JSON.parse(data.toString());

                    if (message.type === 'client_registered') {
                        if (message.status === 'success') {
                            connectionStatus = 'connected';
                            updateStatusBar();
                            outputChannel.appendLine(`Client registered: ${message.userEmail}`);
                        }
                        return;
                    }

                    if (message.type === 'heartbeat') {
                        socket?.send(JSON.stringify({ type: 'heartbeat_ack' }));
                        return;
                    }

                    // Ticket Assigned Event from WebSocket (via Jira Webhook or direct broadcast)
                    if (message.event_type === 'ticket_assigned') {
                        latestTicket = {
                            key: message.ticket_key,
                            title: message.ticket_title,
                            description: message.ticket_description,
                            status: message.ticket_status,
                            priority: message.ticket_priority,
                            url: message.ticket_url,
                            assigneeEmail: message.assignee_email,
                            assigneeDisplayName: message.assignee_name,
                            projectKey: message.project_key,
                            receivedAt: new Date().toLocaleString(),
                            comments: message.comments?.map((b: string) => ({ body: b }))
                        };

                        await context.workspaceState.update('latestTicket', latestTicket);
                        recentTickets = recentTickets.filter(t => t.key !== latestTicket?.key);
                        recentTickets.unshift(latestTicket);
                        recentTickets = recentTickets.slice(0, 10);
                        await context.workspaceState.update('recentTickets', recentTickets);

                        if (currentPanel) {
                            currentPanel.title = `Jira - ${latestTicket.key}`;
                            currentPanel.webview.html = getWebviewHtml(latestTicket, latestAiAnalysis);
                        }

                        outputChannel.appendLine(`Ticket received: ${latestTicket.key} - ${latestTicket.title}`);

                        const action = await vscode.window.showInformationMessage(
                            `New Jira ticket: ${latestTicket.key} - ${latestTicket.title}`,
                            'Open Ticket & AI Plan',
                            'Run AI',
                            'Open in Jira',
                            'Dismiss'
                        );

                        if (action === 'Open Ticket & AI Plan') {
                            await vscode.commands.executeCommand('jira-assistant.openPanel');
                        } else if (action === 'Run AI') {
                            await vscode.commands.executeCommand('jira-assistant.runAi');
                        } else if (action === 'Open in Jira' && latestTicket.url) {
                            await vscode.env.openExternal(vscode.Uri.parse(latestTicket.url));
                        }
                    }
                } catch (e) {
                    outputChannel.appendLine(`Error processing message: ${e}`);
                }
            });

            socket.on('close', () => {
                connectionStatus = 'disconnected';
                socket = undefined;
                updateStatusBar();
                outputChannel.appendLine('Backend WebSocket connection closed.');
                if (!isManualDisconnect) {
                    scheduleReconnect();
                }
                isManualDisconnect = false;
            });

            socket.on('error', () => {
                connectionStatus = 'disconnected';
                updateStatusBar();
                outputChannel.appendLine('Backend connection error.');
                isAutoConnect = false;
            });
        }
    );

    const hello = vscode.commands.registerCommand('jira-assistant.hello', () => {
        vscode.window.showInformationMessage('Hello from Jira Assistant!');
    });

    context.subscriptions.push(
        hello,
        openPanel,
        runAi,
        fetchJiraTicket,
        openSettings,
        mockTicket,
        connectBackend,
        showConnectionStatus,
        statusBarMenu,
        statusBarItem,
        openLatestTicket,
        showRecentTickets,
        disconnectBackend,
        reconnectBackend,
        outputChannel
    );

    const { autoConnect, userEmail } = getConfig();
    if (autoConnect && userEmail && userEmail.trim() !== '') {
        isAutoConnect = true;
        setTimeout(() => {
            vscode.commands.executeCommand('jira-assistant.connectBackend');
        }, 1000);
    }

    updateStatusBar();
}

export function deactivate() {
    socket?.close();
}