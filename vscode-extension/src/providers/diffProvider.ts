import * as vscode from "vscode";

/**
 * Content provider for the cloudshift-diff URI scheme.
 * Serves refactored file content to the VS Code diff editor.
 */
export class CloudShiftDiffProvider implements vscode.TextDocumentContentProvider {
  private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
  readonly onDidChange = this._onDidChange.event;

  constructor(private readonly workspaceState: vscode.Memento) {}

  provideTextDocumentContent(uri: vscode.Uri): string {
    // Refactored content is stored in workspace state keyed by the file path.
    // Try uri.path and uri.fsPath so we find it on all platforms.
    const pathKeys = [uri.path, uri.fsPath].filter((p) => p && p.length > 0);
    for (const filePath of pathKeys) {
      const content = this.workspaceState.get<string>(
        `cloudshift.refactored.${filePath}`,
      );
      if (content !== undefined) return content;
    }
    return "// No refactored content available. Run a refactor command first.";
  }

  /**
   * Notify listeners that the content for a URI has changed,
   * causing VS Code to re-fetch via provideTextDocumentContent.
   */
  refresh(uri: vscode.Uri): void {
    this._onDidChange.fire(uri);
  }

  dispose(): void {
    this._onDidChange.dispose();
  }
}
