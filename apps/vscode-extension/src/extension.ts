import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {

	console.log("Jira Assistant Activated");

	const hello = vscode.commands.registerCommand(
		'jira-assistant.hello',
		() => {
			vscode.window.showInformationMessage(
				'Hello from Jira Assistant!'
			);
		}
	);

	const openPanel = vscode.commands.registerCommand(
		'jira-assistant.openPanel',
		() => {

			const panel = vscode.window.createWebviewPanel(
				'jiraAssistant',
				'Jira Assistant Panel',
				vscode.ViewColumn.One,
				{ enableScripts: true }
			);

			panel.webview.html = `
				<!DOCTYPE html>
				<html>
				<body>
					<h2>Jira Assistant</h2>
					<p>Welcome to Task 2 Panel 🚀</p>
				</body>
				</html>
			`;
		}
	);

	
	const mockTicket = vscode.commands.registerCommand(
		'jira-assistant.mockTicket',
		async () => {

			const action = await vscode.window.showInformationMessage(
				'New Jira ticket assigned: PROJ-123 - Fix login redirect issue',
				'Open Ticket',
				'Ignore'
			);

			if (action === 'Open Ticket') {
				vscode.window.showInformationMessage('Opening ticket PROJ-123...');
			}
		}
	);

	
	const connectBackend = vscode.commands.registerCommand(
		'jira-assistant.connectBackend',
		() => {

			vscode.window.showInformationMessage('Connecting to backend...');

			setTimeout(() => {
				vscode.window.showErrorMessage('Backend not running');
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