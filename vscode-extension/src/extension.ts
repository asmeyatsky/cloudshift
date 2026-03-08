import * as vscode from "vscode";
import { ApiClient } from "./client/apiClient";
import { registerRefactorSelectionCommand } from "./commands/refactorSelection";
import { registerRefactorFileCommand } from "./commands/refactorFile";
import { registerScanProjectCommand } from "./commands/scanProject";
import { registerValidateCommand } from "./commands/validate";
import { GutterAnnotationProvider } from "./providers/gutterAnnotation";
import { CloudShiftDiffProvider } from "./providers/diffProvider";
import { CloudShiftDiagnosticsProvider } from "./providers/diagnostics";
import { StatusBarProvider } from "./providers/statusBar";
import { ManifestTreeProvider } from "./views/manifestTreeView";

export function activate(context: vscode.ExtensionContext): void {
  const apiClient = new ApiClient();

  // --- Providers ---
  const gutterProvider = new GutterAnnotationProvider();
  context.subscriptions.push(gutterProvider);

  const diffProvider = new CloudShiftDiffProvider(context.workspaceState);
  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(
      "cloudshift-diff",
      diffProvider,
    ),
  );

  const diagnosticsProvider = new CloudShiftDiagnosticsProvider();
  context.subscriptions.push(diagnosticsProvider);

  const statusBarProvider = new StatusBarProvider(apiClient);
  context.subscriptions.push(statusBarProvider);

  // --- Views ---
  const manifestTreeProvider = new ManifestTreeProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("manifestTree", manifestTreeProvider),
  );

  // --- Commands ---
  context.subscriptions.push(
    registerScanProjectCommand(
      apiClient,
      gutterProvider,
      diagnosticsProvider,
      statusBarProvider,
      manifestTreeProvider,
    ),
  );

  context.subscriptions.push(
    registerRefactorFileCommand(context, apiClient),
  );

  context.subscriptions.push(
    registerRefactorSelectionCommand(context, apiClient),
  );

  context.subscriptions.push(
    registerValidateCommand(context, apiClient, diagnosticsProvider),
  );

  // --- Auto-scan on file save (if enabled) ---
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      const config = vscode.workspace.getConfiguration("cloudshift");
      const autoScan = config.get<boolean>("autoScan", false);

      if (!autoScan) {
        return;
      }

      const supportedLanguages = ["python", "typescript", "terraform"];
      if (!supportedLanguages.includes(document.languageId)) {
        return;
      }

      try {
        const result = await apiClient.scanFile(
          document.uri.fsPath,
          document.getText(),
        );

        if (result.patterns.length > 0) {
          gutterProvider.setAnnotations(document.uri.fsPath, result.patterns);
          diagnosticsProvider.setDiagnosticsFromScan(
            document.uri.fsPath,
            result.patterns,
          );
        } else {
          gutterProvider.clearAnnotations(document.uri.fsPath);
          diagnosticsProvider.clearFile(document.uri.fsPath);
        }
      } catch {
        // Silently fail for auto-scan to avoid disrupting the user
      }
    }),
  );
}

export function deactivate(): void {
  // All disposables registered via context.subscriptions are cleaned up
  // automatically by VS Code. Nothing additional needed here.
}
