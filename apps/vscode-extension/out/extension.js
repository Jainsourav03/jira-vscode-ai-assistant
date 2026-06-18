"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const WebSocket = require("ws");
let latestTicket;
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
    const connectBackend = vscode.commands.registerCommand('jira-assistant.connectBackend', () => {
        const socket = new WebSocket(websocketUrl);
        socket.on('open', () => {
            vscode.window.showInformationMessage(`Connected to backend as ${userEmail}`);
            ``;
        });
        socket.on('message', async (data) => {
            try {
                const ticket = JSON.parse(data.toString());
                if (ticket.ticket_key &&
                    ticket.title) {
                    latestTicket =
                        ticket;
                    const action = await vscode.window.showInformationMessage(`New Jira ticket assigned:
${ticket.ticket_key}
-
${ticket.title}`, 'Open Ticket');
                    if (action === 'Open Ticket') {
                        vscode.commands.executeCommand('jira-assistant.openPanel');
                    }
                }
                else {
                    vscode.window.showErrorMessage('Invalid message received');
                }
            }
            catch {
                vscode.window.showErrorMessage('Invalid backend data');
            }
        });
        socket.on('close', () => {
            vscode.window.showWarningMessage('Connection closed');
        });
        socket.on('error', () => {
            vscode.window.showErrorMessage('Backend unavailable');
        });
    });
    context.subscriptions.push(hello, openPanel, mockTicket, connectBackend);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map