"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
function activate(context) {
    const disposable = vscode.commands.registerCommand('jira-assistant.hello', () => {
        vscode.window.showInformationMessage('Hello from Jira Assistant!');
    });
    context.subscriptions.push(disposable);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map