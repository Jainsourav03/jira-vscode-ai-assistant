import * as vscode from 'vscode';
import WebSocket = require('ws');

let latestTicket: any;
let socket: WebSocket | undefined;
let connectionStatus:
'connected' |
'disconnected' |
'connecting' =
'disconnected';

let currentPanel: any;

export function activate(context: vscode.ExtensionContext) {

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
		async () => {

			currentPanel = vscode.window.createWebviewPanel(
				'jiraAssistant',
				'Jira Assistant - Ticket',
				vscode.ViewColumn.One,
				{
					enableScripts: true
				}
			);
			currentPanel.webview.onDidReceiveMessage(
(message:any)=>{

if(
message.type===
'webviewReady'
){

currentPanel?.webview.postMessage({

type:
'focusContext'

});

}

}
);

currentPanel.webview.onDidReceiveMessage(
async (message:any)=>{

if(
message.type===
'submitContext'
){

try{

const response =
await fetch(

`${backendUrl}/tickets/${latestTicket?.ticket_key}/developer-context`,

{

method:
'POST',

headers:{
'Content-Type':
'application/json'
},

body:
JSON.stringify({

userEmail:
userEmail,

additionalContext:
message.additionalContext,

repoPath:
vscode.workspace.workspaceFolders?.[0]
?.uri.fsPath

})

}

);

if(
response.ok
){

vscode.window.showInformationMessage(
'Context submitted successfully'
);

}

else{

vscode.window.showErrorMessage(
'Backend rejected context'
);

}

}

catch{

vscode.window.showErrorMessage(
'Failed to submit context'
);

}

}

}
);

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
		}
	);
	const openLatestTicket =
vscode.commands.registerCommand(
'jira-assistant.openLatestTicket',
async ()=>{

if(!latestTicket){

vscode.window.showInformationMessage(
'No Jira ticket received yet.'
);

return;

}

await vscode.commands.executeCommand(
'jira-assistant.openPanel'
);

}
);

	const mockTicket = vscode.commands.registerCommand(
		'jira-assistant.mockTicket',
		async () => {

			const action =
			await vscode.window.showInformationMessage(
				'New Jira ticket assigned: PROJ-123 - Fix login redirect issue',
				'Open Ticket',
				'Add Context',	
				'Ignore'
			);

			if(action==='Open Ticket'){

				await vscode.commands.executeCommand(
					'jira-assistant.openPanel'
				);

			}
			else if(
action==='Add Context'
){

await vscode.commands.executeCommand(
'jira-assistant.openPanel'
);

setTimeout(
()=>{

currentPanel.webview.postMessage({

type:
'focusContext'

});

},
500
);

}
			else{
				return;
			}

		}
	
	);

	const config =
	vscode.workspace.getConfiguration(
		'jiraAssistant'
	);

	const backendUrl =
	config.get<string>(
		'backendUrl'
	);

	const websocketUrl =
	config.get<string>(
		'websocketUrl'
	);

	const userEmail =
	config.get<string>(
		'userEmail'
	);

	const clientId =
`vscode-client-${Date.now()}`;

const connectBackend =
vscode.commands.registerCommand(
'jira-assistant.connectBackend',
() => {

if(socket){

socket.close();

}
connectionStatus =
'connecting';
socket =
new WebSocket(
websocketUrl!
);

socket.on(
'open',
() => {

connectionStatus =
`connected`;

vscode.window.showInformationMessage(
connectionStatus
);

/* Register client */

socket!.send(

JSON.stringify({

type:
'client_register',

userEmail:
userEmail,

clientId:
clientId

})

);

}
);


socket.on(
'message',
async (data)=>{

try{

const message =
JSON.parse(
data.toString()
);

/* Registration */

if(
message.type===
'client_registered'
){

if(
message.status===
'success'
){

vscode.window.showInformationMessage(
`Registered successfully as ${message.userEmail}`
);

}

else{

connectionStatus =
'disconnected';

vscode.window.showErrorMessage(
connectionStatus
);

}

return;

}


/* Ticket */

if(
message.ticket_key &&
message.ticket_title
){

latestTicket = {

ticket_key:
message.ticket_key,

title:
message.ticket_title,
 status:
 message.ticket_status,

priority:
message.ticket_priority,

description:
message.ticket_description,

comments:
message.comments,

jira_link:
message.jira_link,

assignee_email:
message.assignee_email

};

const action =
await vscode.window.showInformationMessage(

`New Jira ticket assigned:
${latestTicket.ticket_key}

${latestTicket.title}`,

'Open Ticket',
'Add Context',
'Ignore'

);

if(
action==='Open Ticket'
){

await vscode.commands.executeCommand(
'jira-assistant.openPanel'
);

}

else if(
action==='Add Context'
){

await vscode.commands.executeCommand(
'jira-assistant.openPanel'
);

await vscode.window.showInformationMessage(
'Enter additional context below'
);

}

return;

}


/* Unknown */

vscode.window.showWarningMessage(
'Unknown backend event'
);

}

catch{

vscode.window.showErrorMessage(
'Invalid backend JSON'
);

}

}
);



socket.on(
'close',
()=>{

connectionStatus =
'disconnected';



setTimeout(
()=>{

if(
socket?.readyState ===
WebSocket.CLOSED
){

socket =
undefined;

}

},
300
);

}
);

socket.on(
'error',
()=>{

connectionStatus =
'disconnected';

vscode.window.showWarningMessage(
'Backend unavailable'
);

}
);

}
);
const showConnectionStatus =
vscode.commands.registerCommand(

'jira-assistant.showConnectionStatus',

()=>{

vscode.window.showInformationMessage(
connectionStatus
);

}
);
	context.subscriptions.push(
		hello,
		openPanel,
		mockTicket,
		connectBackend,
		showConnectionStatus
	);
	

setTimeout(
()=>{

vscode.commands.executeCommand(
'jira-assistant.connectBackend'
);

},
1000
);

}

export function deactivate() {}