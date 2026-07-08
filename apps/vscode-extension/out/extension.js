"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const WebSocket = require("ws");
let latestTicket;
let socket;
let connectionStatus = 'disconnected';
let currentPanel;
let isAutoConnect = false;
let reconnectAttempts = 0;
const reconnectDelays = [
    2000,
    5000,
    10000,
    30000,
    30000
];
let reconnectTimer;
let recentTickets = [];
function activate(context) {
    let clientId = context.globalState.get('clientId');
    if (!clientId) {
        clientId =
            `vscode-client-${Date.now()}`;
        context.globalState.update('clientId', clientId);
    }
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command =
        'jira-assistant.statusBarMenu';
    statusBarItem.show();
    function updateStatusBar() {
        switch (connectionStatus) {
            case 'connected':
                statusBarItem.text =
                    '$(plug) Jira Assistant: Connected';
                break;
            case 'connecting':
                statusBarItem.text =
                    '$(sync~spin) Jira Assistant: Connecting';
                break;
            case 'disconnected':
                statusBarItem.text =
                    '$(circle-slash) Jira Assistant: Disconnected';
                break;
            default:
                statusBarItem.text =
                    '$(warning) Jira Assistant: Error';
        }
    }
    const outputChannel = vscode.window.createOutputChannel('Jira Assistant');
    outputChannel.show(true);
    outputChannel.appendLine('Extension activated');
    const hello = vscode.commands.registerCommand('jira-assistant.hello', () => {
        vscode.window.showInformationMessage('Hello from Jira Assistant!');
    });
    const openPanel = vscode.commands.registerCommand('jira-assistant.openPanel', async () => {
        currentPanel = vscode.window.createWebviewPanel('jiraAssistant', 'Jira Assistant - Ticket', vscode.ViewColumn.One, {
            enableScripts: true
        });
        currentPanel.webview.onDidReceiveMessage((message) => {
            if (message.type ===
                'webviewReady') {
                currentPanel?.webview.postMessage({
                    type: 'focusContext'
                });
            }
        });
        currentPanel.webview.onDidReceiveMessage(async (message) => {
            if (message.type ===
                'submitContext') {
                try {
                    const response = await fetch(`${backendUrl}/tickets/${latestTicket?.ticket_key}/developer-context`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            userEmail: userEmail,
                            additionalContext: message.additionalContext,
                            repoPath: vscode.workspace.workspaceFolders?.[0]
                                ?.uri.fsPath
                        })
                    });
                    if (response.ok) {
                        outputChannel.appendLine(`Context submitted: ${latestTicket?.ticket_key}`);
                        vscode.window.showInformationMessage('Context submitted successfully');
                    }
                    else {
                        vscode.window.showErrorMessage('Backend rejected context');
                    }
                }
                catch {
                    vscode.window.showErrorMessage('Failed to submit context');
                }
            }
        });
        currentPanel.webview.html = `
<!DOCTYPE html>
<html>

<body>

<h2>Jira Ticket Details</h2>

<p><b>Ticket Key:</b>
${latestTicket?.ticket_key ?? 'No Ticket'}
</p>

<p><b>Title:</b>
${latestTicket?.title ?? 'No Title'}
</p>

<p><b>Status:</b>
${latestTicket?.status ?? 'Not Available'}
</p>

<p><b>Priority:</b>
${latestTicket?.priority ?? 'Medium'}
</p>

<p><b>Description:</b>
${latestTicket?.description ?? 'No Description'}
</p>

<p><b>Comments:</b>
${latestTicket?.comments ?? 'No Comments'}
</p>

<p><b>Assignee Email:</b>
${latestTicket?.assignee_email ?? 'Unassigned'}
</p>

<p>
<b>Jira Link:</b>

<a
href="${latestTicket?.jira_link ?? 'https://jira.atlassian.com'}"
>
Open Jira Ticket
</a>

</p>

<br>

<textarea
id="contextBox"
placeholder="Additional context"
style="width:100%;height:120px;"
></textarea>

<br><br>

<button id="submitBtn">
Submit Context
</button>

<button id="runBtn">
Run AI
</button>

<div id="result"></div>
<script>

const vscode =
acquireVsCodeApi();

/* Tell extension webview finished loading */

window.onload =
()=>{

vscode.postMessage({

type:
'webviewReady'

});

};

document
.getElementById("runBtn")
.addEventListener(
"click",
function(){

document
.getElementById("result")
.innerText =
"AI integration will be added in a later phase.";

}
);
document
.getElementById(
"submitBtn"
)
.addEventListener(
"click",
function(){

const text =
document
.getElementById(
"contextBox"
).value;
vscode.postMessage({
type:'submitContext',
ticketKey:
"${latestTicket?.ticket_key}",
additionalContext:text
});
}		
);



/* Receive messages */

window.addEventListener(
'message',
(event)=>{

if(
event.data.type===
'focusContext'
){

const box =
document.getElementById(
'contextBox'
);

if(box){

box.focus();

}

}

}
);

</script>
</body>
</html>
`;
        return currentPanel;
    });
    const openLatestTicket = vscode.commands.registerCommand('jira-assistant.openLatestTicket', async () => {
        if (!latestTicket) {
            vscode.window.showInformationMessage('No Jira ticket received yet.');
            return;
        }
        await vscode.commands.executeCommand('jira-assistant.openPanel');
    });
    const mockTicket = vscode.commands.registerCommand('jira-assistant.mockTicket', async () => {
        const action = await vscode.window.showInformationMessage('New Jira ticket assigned: PROJ-123 - Fix login redirect issue', 'Open Ticket', 'Add Context', 'Ignore');
        if (action === 'Open Ticket') {
            await vscode.commands.executeCommand('jira-assistant.openPanel');
        }
        else if (action === 'Add Context') {
            await vscode.commands.executeCommand('jira-assistant.openPanel');
            setTimeout(() => {
                currentPanel.webview.postMessage({
                    type: 'focusContext'
                });
            }, 500);
        }
        else {
            return;
        }
    });
    const config = vscode.workspace.getConfiguration('jiraAssistant');
    const backendUrl = config.get('backendUrl');
    const websocketUrl = config.get('websocketUrl');
    const autoConnect = config.get('autoConnect');
    const showNotifications = config.get('showNotifications');
    const userEmail = config.get('userEmail');
    function scheduleReconnect() {
        if (reconnectTimer) {
            return;
        }
        const delay = reconnectDelays[Math.min(reconnectAttempts, reconnectDelays.length - 1)];
        outputChannel.appendLine(`Reconnect scheduled in ${delay / 1000} seconds`);
        reconnectTimer = setTimeout(() => {
            reconnectTimer = undefined;
            reconnectAttempts++;
            vscode.commands.executeCommand('jira-assistant.connectBackend');
        }, delay);
    }
    const connectBackend = vscode.commands.registerCommand('jira-assistant.connectBackend', () => {
        reconnectAttempts = 0;
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
        connectionStatus =
            'connecting';
        updateStatusBar();
        if (!backendUrl) {
            vscode.window.showErrorMessage('Please configure jiraAssistant.backendUrl before connecting.');
            return;
        }
        if (!websocketUrl) {
            vscode.window.showErrorMessage('Please configure jiraAssistant.websocketUrl before connecting.');
            return;
        }
        if (!userEmail || userEmail.trim() === '') {
            vscode.window.showErrorMessage('Please configure jiraAssistant.userEmail before connecting.');
            return;
        }
        if (!websocketUrl ||
            (!websocketUrl.startsWith('ws://') &&
                !websocketUrl.startsWith('wss://'))) {
            connectionStatus = 'disconnected';
            updateStatusBar();
            vscode.window.showErrorMessage('Invalid WebSocket URL.');
            return;
        }
        outputChannel.appendLine('Connection attempt');
        socket = new WebSocket(websocketUrl);
        socket.on('open', () => {
            connectionStatus =
                'connected';
            updateStatusBar();
            isAutoConnect = false;
            /* Reset reconnect state */
            reconnectAttempts = 0;
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = undefined;
            }
            outputChannel.appendLine('Connection success');
            vscode.window.showInformationMessage(connectionStatus);
            /* Register client */
            socket.send(JSON.stringify({
                type: 'client_register',
                userEmail: userEmail,
                clientId: clientId
            }));
        });
        socket.on('message', async (data) => {
            try {
                const message = JSON.parse(data.toString());
                /* Registration */
                if (message.type ===
                    'client_registered') {
                    if (message.status ===
                        'success') {
                        connectionStatus =
                            'connected';
                        updateStatusBar();
                        outputChannel.appendLine(`Registration success: ${message.userEmail}`);
                        vscode.window.showInformationMessage(`Registered successfully as ${message.userEmail}`);
                    }
                    else {
                        connectionStatus =
                            'disconnected';
                        updateStatusBar();
                        outputChannel.appendLine('Registration failed');
                        vscode.window.showErrorMessage(connectionStatus);
                    }
                    return;
                }
                if (message.type ===
                    'heartbeat') {
                    outputChannel.appendLine('Heartbeat received');
                    /* Reply to backend */
                    socket?.send(JSON.stringify({
                        type: 'heartbeat_ack'
                    }));
                    return;
                }
                if (message.type ===
                    'error') {
                    outputChannel.appendLine(`Backend error:
${message.message}`);
                    vscode.window.showWarningMessage(message.message);
                    return;
                }
                /* Ticket */
                if (message.event_type ===
                    'ticket_assigned') {
                    if (!message.ticket_key ||
                        !message.ticket_title) {
                        outputChannel.appendLine('Invalid ticket_assigned event');
                        vscode.window.showWarningMessage('Invalid ticket received from backend.');
                        return;
                    }
                    latestTicket = {
                        ticket_key: message.ticket_key,
                        title: message.ticket_title,
                        status: message.ticket_status,
                        priority: message.ticket_priority,
                        description: message.ticket_description,
                        comments: message.comments,
                        jira_link: message.jira_link,
                        assignee_email: message.assignee_email
                    };
                    recentTickets.unshift(latestTicket);
                    if (recentTickets.length > 10) {
                        recentTickets.pop();
                    }
                    if (currentPanel) {
                        await vscode.commands.executeCommand('jira-assistant.openPanel');
                    }
                    outputChannel.appendLine(`Ticket received: ${latestTicket.ticket_key}`);
                    const action = await vscode.window.showInformationMessage(`New Jira ticket assigned:
${latestTicket.ticket_key}

${latestTicket.title}`, 'Open Ticket', 'Add Context', 'Ignore');
                    if (action === 'Open Ticket') {
                        await vscode.commands.executeCommand('jira-assistant.openPanel');
                    }
                    else if (action === 'Add Context') {
                        await vscode.commands.executeCommand('jira-assistant.openPanel');
                        await vscode.window.showInformationMessage('Enter additional context below');
                    }
                    return;
                }
                outputChannel.appendLine(`Unknown backend event: ${message.type ?? message.event_type ?? 'unknown'}`);
                /* Unknown */
                vscode.window.showWarningMessage('Unknown backend event');
            }
            catch {
                outputChannel.appendLine('Invalid message received');
                vscode.window.showErrorMessage('Invalid backend JSON');
            }
        });
        socket.on('close', () => {
            connectionStatus = 'disconnected';
            socket = undefined;
            updateStatusBar();
            outputChannel.appendLine('Disconnection');
            scheduleReconnect();
        });
        socket.on('error', () => {
            connectionStatus = 'disconnected';
            updateStatusBar();
            outputChannel.appendLine('Backend error');
            if (!isAutoConnect) {
                vscode.window.showWarningMessage('Backend unavailable');
            }
            isAutoConnect = false;
        });
    });
    const showConnectionStatus = vscode.commands.registerCommand('jira-assistant.showConnectionStatus', () => {
        vscode.window.showInformationMessage(connectionStatus);
    });
    const statusBarMenu = vscode.commands.registerCommand('jira-assistant.statusBarMenu', async () => {
        const action = await vscode.window.showQuickPick([
            'Connect',
            'Disconnect',
            'Reconnect',
            'Show Connection Status',
            'Open Latest Ticket',
            'Open Settings'
        ], {
            placeHolder: 'Jira Assistant'
        });
        switch (action) {
            case 'Connect':
                await vscode.commands.executeCommand('jira-assistant.connectBackend');
                break;
            case 'Disconnect':
                socket?.close();
                break;
            case 'Reconnect':
                socket?.close();
                await vscode.commands.executeCommand('jira-assistant.connectBackend');
                break;
            case 'Show Connection Status':
                await vscode.commands.executeCommand('jira-assistant.showConnectionStatus');
                break;
            case 'Open Latest Ticket':
                await vscode.commands.executeCommand('jira-assistant.openLatestTicket');
                break;
            case 'Open Settings':
                await vscode.commands.executeCommand('workbench.action.openSettings', 'jiraAssistant');
                break;
        }
    });
    context.subscriptions.push(hello, openPanel, mockTicket, connectBackend, showConnectionStatus, statusBarMenu, statusBarItem, outputChannel);
    if (autoConnect &&
        userEmail &&
        userEmail.trim() !== '') {
        isAutoConnect = true;
        setTimeout(() => {
            vscode.commands.executeCommand('jira-assistant.connectBackend');
        });
    }
    updateStatusBar();
}
function deactivate() { }
//# sourceMappingURL=extension.js.map