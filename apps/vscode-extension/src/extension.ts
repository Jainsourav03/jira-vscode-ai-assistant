import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {

    const disposable = vscode.commands.registerCommand(
        'jira-assistant.hello',
        () => {
            vscode.window.showInformationMessage(
                'Hello from Jira Assistant!'
            );
        }
    );

    context.subscriptions.push(disposable);
}

export function deactivate() {}