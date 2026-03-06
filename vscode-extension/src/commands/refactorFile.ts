import * as vscode from "vscode";
import { ApiClient, CloudShiftApiError } from "../client/apiClient";

export function registerRefactorFileCommand(
  context: vscode.ExtensionContext,
  apiClient: ApiClient,
): vscode.Disposable {
  return vscode.commands.registerCommand(
    "cloudshift.refactorFile",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("No active editor found.");
        return;
      }

      const document = editor.document;
      const filePath = document.uri.fsPath;
      const content = document.getText();

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "CloudShift: Refactoring file...",
          cancellable: false,
        },
        async () => {
          try {
            const result = await apiClient.refactorFile(filePath, content);

            if (result.changes.length === 0) {
              vscode.window.showInformationMessage(
                "No refactoring changes suggested for this file.",
              );
              return;
            }

            const originalUri = document.uri;
            const refactoredUri = vscode.Uri.parse(
              `cloudshift-diff:${filePath}?refactored`,
            );

            // Store refactored content for the diff provider
            context.workspaceState.update(
              `cloudshift.refactored.${filePath}`,
              result.refactoredContent,
            );

            await vscode.commands.executeCommand(
              "vscode.diff",
              originalUri,
              refactoredUri,
              `CloudShift: ${vscode.workspace.asRelativePath(filePath)} (Refactored)`,
            );

            const applyAction = "Apply Changes";
            const choice = await vscode.window.showInformationMessage(
              `CloudShift found ${result.changes.length} change(s).`,
              applyAction,
              "Dismiss",
            );

            if (choice === applyAction) {
              const edit = new vscode.WorkspaceEdit();
              edit.replace(
                document.uri,
                new vscode.Range(
                  document.positionAt(0),
                  document.positionAt(content.length),
                ),
                result.refactoredContent,
              );
              await vscode.workspace.applyEdit(edit);
              vscode.window.showInformationMessage(
                "CloudShift: Refactoring applied.",
              );
            }
          } catch (err) {
            if (err instanceof CloudShiftApiError) {
              vscode.window.showErrorMessage(`CloudShift: ${err.message}`);
            } else {
              vscode.window.showErrorMessage(
                "CloudShift: An unexpected error occurred during refactoring.",
              );
            }
          }
        },
      );
    },
  );
}
