import * as vscode from "vscode";
import { ApiClient, CloudShiftApiError } from "../client/apiClient";

function runRefactorFile(
  context: vscode.ExtensionContext,
  apiClient: ApiClient,
  sourceProvider: "AWS" | "Azure",
): () => Promise<void> {
  return async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("No active editor found.");
      return;
    }

    const document = editor.document;
    const filePath = document.uri.fsPath;
    const content = document.getText();

    const label = sourceProvider === "Azure" ? "Azure → GCP" : "AWS → GCP";
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `CloudShift: Refactoring file (${label})...`,
        cancellable: false,
      },
      async () => {
        try {
          const result = await apiClient.refactorFile(
            filePath,
            content,
            sourceProvider,
          );

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

          context.workspaceState.update(
            `cloudshift.refactored.${filePath}`,
            result.refactoredContent,
          );

          const output = vscode.window.createOutputChannel("CloudShift");
          output.appendLine(`--- Refactored file (${label}) ${vscode.workspace.asRelativePath(filePath)} ---`);
          output.appendLine(result.refactoredContent);
          output.appendLine("");
          output.show(true);

          const doc = await vscode.workspace.openTextDocument({
            content: result.refactoredContent,
            language: document.languageId,
          });
          await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: false });

          await vscode.commands.executeCommand(
            "vscode.diff",
            originalUri,
            refactoredUri,
            `CloudShift: ${vscode.workspace.asRelativePath(filePath)} (${label})`,
          );

          const applyAction = "Apply Changes";
          const openInEditorAction = "Open refactored in editor";
          const choice = await vscode.window.showInformationMessage(
            `CloudShift found ${result.changes.length} change(s). Refactored code is in the editor tab and CloudShift output panel.`,
            applyAction,
            openInEditorAction,
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
          } else if (choice === openInEditorAction) {
            const refactorDoc = await vscode.workspace.openTextDocument({
              content: result.refactoredContent,
              language: document.languageId,
            });
            await vscode.window.showTextDocument(refactorDoc, { viewColumn: vscode.ViewColumn.Beside });
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
  };
}

export function registerRefactorFileCommand(
  context: vscode.ExtensionContext,
  apiClient: ApiClient,
): vscode.Disposable[] {
  return [
    vscode.commands.registerCommand(
      "cloudshift.refactorFileAwsToGcp",
      runRefactorFile(context, apiClient, "AWS"),
    ),
    vscode.commands.registerCommand(
      "cloudshift.refactorFileAzureToGcp",
      runRefactorFile(context, apiClient, "Azure"),
    ),
  ];
}
