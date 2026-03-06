import * as vscode from "vscode";
import { ApiClient, CloudShiftApiError } from "../client/apiClient";
import { CloudShiftDiagnosticsProvider } from "../providers/diagnostics";
import { ValidationPanel } from "../views/validationPanel";

export function registerValidateCommand(
  context: vscode.ExtensionContext,
  apiClient: ApiClient,
  diagnosticsProvider: CloudShiftDiagnosticsProvider,
): vscode.Disposable {
  return vscode.commands.registerCommand("cloudshift.validate", async () => {
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
        title: "CloudShift: Validating transformations...",
        cancellable: false,
      },
      async () => {
        try {
          const result = await apiClient.validate(filePath, content);

          // Update diagnostics from validation
          diagnosticsProvider.setDiagnosticsFromValidation(
            filePath,
            result.errors,
            result.warnings,
          );

          // Show validation panel
          ValidationPanel.createOrShow(context.extensionUri, result);

          if (result.valid) {
            vscode.window.showInformationMessage(
              "CloudShift: Validation passed with no errors.",
            );
          } else {
            vscode.window.showWarningMessage(
              `CloudShift: Validation found ${result.errors.length} error(s) and ${result.warnings.length} warning(s).`,
            );
          }
        } catch (err) {
          if (err instanceof CloudShiftApiError) {
            vscode.window.showErrorMessage(`CloudShift: ${err.message}`);
          } else {
            vscode.window.showErrorMessage(
              "CloudShift: An unexpected error occurred during validation.",
            );
          }
        }
      },
    );
  });
}
