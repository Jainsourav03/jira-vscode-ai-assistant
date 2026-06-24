"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const WebSocket = require("ws");
let latestTicket;
let socket;
let connectionStatus = 'Disconnected';
function activate(context) {
    const hello = vscode.commands.registerCommand('jira-assistant.hello', () => {
        vscode.window.showInformationMessage('Hello from Jira Assistant!');
    });
    const openPanel = vscode.commands.registerCommand('jira-assistant.openPanel', () => {
        const panel = vscode.window.createWebviewPanel('jiraAssistant', 'Jira Assistant - Ticket', vscode.ViewColumn.One, {
            enableScripts: true
        });
        panel.webview.html = `
<!DOCTYPE html>
<html>

<body>

<h2>Jira Ticket Details</h2>

<p><b>Ticket Key:</b>
${latestTicket?.ticket_key ?? 'No Ticket'}
</p>

<p><b>Ticket Title:</b>
${latestTicket?.title ?? 'No Title'}
</p>

<p><b>Priority:</b>
${latestTicket?.priority ?? 'Medium'}
</p>

<p><b>Description:</b>
${latestTicket?.description ?? 'No Description'}
</p>

<a href="https://jira.atlassian.com">
Open Jira Ticket
</a>

<br><br>

<textarea
placeholder="Additional instructions"
style="width:100%;height:100px;"
></textarea>

<br><br>

<button id="runBtn">
Run AI
</button>

<div id="result"></div>

<script>

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

</script>

</body>
</html>
`;
    });
    const mockTicket = vscode.commands.registerCommand('jira-assistant.mockTicket', async () => {
        const action = await vscode.window.showInformationMessage('New Jira ticket assigned: PROJ-123 - Fix login redirect issue', 'Open Ticket', 'Ignore');
        if (action === 'Open Ticket') {
            vscode.window.showInformationMessage('Opening ticket...');
        }
    });
    const config = vscode.workspace.getConfiguration('jiraAssistant');
    const backendUrl = config.get('backendUrl');
    const websocketUrl = config.get('websocketUrl');
    const userEmail = config.get('userEmail');
    const clientId = `vscode-client-${Date.now()}`;
    const connectBackend = vscode.commands.registerCommand('jira-assistant.connectBackend', () => {
        if (socket) {
            socket.close();
        }
        connectionStatus =
            'Connecting...';
        socket =
            new WebSocket(websocketUrl);
        socket.on('open', () => {
            connectionStatus =
                `Connected as ${userEmail}`;
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
                /* Registration acknowledgement */
                if (message.type ===
                    'client_registered') {
                    if (message.status ===
                        'success') {
                        vscode.window.showInformationMessage(`Registered successfully as ${message.userEmail}`);
                    }
                    else {
                        connectionStatus =
                            'Registration failed';
                        vscode.window.showErrorMessage(connectionStatus);
                    }
                    return;
                }
                /* Ticket messages */
                if (message.ticket_key &&
                    message.ticket_title) {
                    latestTicket = {
                        ticket_key: message.ticket_key,
                        title: message.ticket_title,
                        priority: message.ticket_priority,
                        description: message.ticket_description
                    };
                    const action = await vscode.window.showInformationMessage(`New Jira ticket assigned:
${latestTicket.ticket_key}


${latestTicket.title}`, 'Open Ticket');
                    if (action === 'Open Ticket') {
                        await vscode.commands.executeCommand('jira-assistant.openPanel');
                    }
                }
                else {
                    vscode.window.showWarningMessage('Unknown backend event');
                }
            }
            catch {
                vscode.window.showErrorMessage('Invalid backend JSON');
            }
        });
        socket.on('close', () => {
            connectionStatus =
                'Disconnected';
            vscode.window.showWarningMessage('Connection closed');
        });
        socket.on('error', () => {
            connectionStatus = 'Backend unavailable';
            vscode.window.showErrorMessage(connectionStatus);
        });
    });
    const showConnectionStatus = vscode.commands.registerCommand('jira-assistant.showConnectionStatus', () => {
        vscode.window.showInformationMessage(connectionStatus);
    });
    context.subscriptions.push(hello, openPanel, mockTicket, connectBackend, showConnectionStatus);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map