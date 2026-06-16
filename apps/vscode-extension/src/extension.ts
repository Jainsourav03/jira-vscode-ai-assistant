import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {

	const hello = vscode.commands.registerCommand(
		'jira-assistant.hello',
		() => {
			vscode.window.showInformationMessage(
				'Hello from Jira Assistant!'
			);
		}
	);

	// OPEN PANEL
	const openPanel = vscode.commands.registerCommand(
		'jira-assistant.openPanel',
		() => {

			const panel = vscode.window.createWebviewPanel(
				'jiraAssistant',
				'Jira Assistant - Ticket',
				vscode.ViewColumn.One,
				{
					enableScripts: true
				}
			);

			panel.webview.html = `
<!DOCTYPE html>
<html>

<body>

<h2>Jira Ticket Details</h2>

<p><b>Ticket Key:</b> PROJ-123</p>
<p><b>Ticket Title:</b> Fix login redirect issue</p>
<p><b>Status:</b> In Progress</p>
<p><b>Priority:</b> High</p>

<p>
Users are not redirected properly after login.
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
		}
	);   


	// MOCK TICKET
	const mockTicket = vscode.commands.registerCommand(
		'jira-assistant.mockTicket',
		async () => {

			const action =
				await vscode.window.showInformationMessage(
					'New Jira ticket assigned: PROJ-123 - Fix login redirect issue',
					'Open Ticket',
					'Ignore'
				);

			if (action === 'Open Ticket') {
				vscode.window.showInformationMessage(
					'Opening ticket...'
				);
			}
		}
	);


	// CONNECT BACKEND
	const connectBackend = vscode.commands.registerCommand(
		'jira-assistant.connectBackend',
		() => {

			vscode.window.showInformationMessage(
				'Connecting to backend...'
			);

			setTimeout(() => {
				vscode.window.showErrorMessage(
					'Backend not running'
				);
			}, 1000);

		}
	);


	context.subscriptions.push(
		hello,
		openPanel,
		mockTicket,
		connectBackend
	);

}

export function deactivate() {}