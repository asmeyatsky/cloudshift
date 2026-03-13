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

          const hasContent =
            typeof result.refactoredContent === "string" &&
            result.refactoredContent.trim().length > 0;
          if (!hasContent) {
            vscode.window.showInformationMessage(
              "No refactoring changes suggested for this file.",
            );
            return;
          }

          const changeCount = result.changes?.length ?? 0;
          console.log("[CloudShift] refactor result", {
            changeCount,
            contentLen: result.refactoredContent.length,
          });
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
          await vscode.window.showTextDocument(doc, {
            viewColumn: vscode.ViewColumn.Active,
            preview: false,
            preserveFocus: false,
          });

          await vscode.commands.executeCommand(
            "vscode.diff",
            originalUri,
            refactoredUri,
            `CloudShift: ${vscode.workspace.asRelativePath(filePath)} (${label})`,
          );

          const applyAction = "Apply Changes";
          const showOutputAction = "Show Output panel";
          const choice = await vscode.window.showInformationMessage(
            `CloudShift: ${changeCount} change(s). Refactored code is in the new tab.`,
            applyAction,
            showOutputAction,
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
          } else if (choice === showOutputAction) {
            const out = vscode.window.createOutputChannel("CloudShift");
            out.show(true);
          }
        } catch (err) {
          console.error("[CloudShift] refactor error", err);
          if (err instanceof CloudShiftApiError) {
            vscode.window.showErrorMessage(`CloudShift: ${err.message}`);
          } else {
            vscode.window.showErrorMessage(
              "CloudShift: An unexpected error occurred during refactoring. Check Developer Console (Help > Toggle Developer Tools).",
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
