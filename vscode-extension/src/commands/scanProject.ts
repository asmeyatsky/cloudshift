import * as vscode from "vscode";
import {
  ApiClient,
  CloudShiftApiError,
  ScanResult,
} from "../client/apiClient";
import { GutterAnnotationProvider } from "../providers/gutterAnnotation";
import { CloudShiftDiagnosticsProvider } from "../providers/diagnostics";
import { StatusBarProvider } from "../providers/statusBar";
import { ManifestTreeProvider } from "../views/manifestTreeView";

export function registerScanProjectCommand(
  apiClient: ApiClient,
  gutterProvider: GutterAnnotationProvider,
  diagnosticsProvider: CloudShiftDiagnosticsProvider,
  statusBarProvider: StatusBarProvider,
  manifestTreeProvider: ManifestTreeProvider,
): vscode.Disposable {
  return vscode.commands.registerCommand(
    "cloudshift.scanProject",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showWarningMessage(
          "No workspace folder open. Open a folder to scan.",
        );
        return;
      }

      const rootPath = workspaceFolders[0].uri.fsPath;

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "CloudShift: Scanning project...",
          cancellable: true,
        },
        async (progress, token) => {
          try {
            progress.report({ message: "Connecting to server..." });

            const isHealthy = await apiClient.healthCheck();
            if (!isHealthy) {
              vscode.window.showErrorMessage(
                "CloudShift: Cannot connect to the backend server. Please ensure it is running.",
              );
              statusBarProvider.setServerStatus(false);
              return;
            }

            statusBarProvider.setServerStatus(true);

            if (token.isCancellationRequested) {
              return;
            }

            progress.report({ message: "Scanning files..." });

            const results: ScanResult[] =
              await apiClient.scanProject(rootPath);

            if (token.isCancellationRequested) {
              return;
            }

            progress.report({ message: "Processing results..." });

            // Update gutter annotations
            gutterProvider.clearAll();
            for (const result of results) {
              if (result.patterns.length > 0) {
                gutterProvider.setAnnotations(result.file, result.patterns);
              }
            }

            // Update diagnostics
            diagnosticsProvider.clearAll();
            for (const result of results) {
              diagnosticsProvider.setDiagnosticsFromScan(
                result.file,
                result.patterns,
              );
            }

            // Update manifest tree
            manifestTreeProvider.updateFromScanResults(results);

            // Update status bar
            const totalPatterns = results.reduce(
              (sum, r) => sum + r.patterns.length,
              0,
            );
            const totalFiles = results.filter(
              (r) => r.patterns.length > 0,
            ).length;
            statusBarProvider.setPatternCount(totalPatterns, totalFiles);

            vscode.window.showInformationMessage(
              `CloudShift: Scan complete. Found ${totalPatterns} pattern(s) in ${totalFiles} file(s).`,
            );
          } catch (err) {
            if (err instanceof CloudShiftApiError) {
              vscode.window.showErrorMessage(`CloudShift: ${err.message}`);
              if (
                err.message.includes("Cannot connect") ||
                err.message.includes("ECONNREFUSED")
              ) {
                statusBarProvider.setServerStatus(false);
              }
            } else {
              vscode.window.showErrorMessage(
                "CloudShift: An unexpected error occurred during scanning.",
              );
            }
          }
        },
      );
    },
  );
}
