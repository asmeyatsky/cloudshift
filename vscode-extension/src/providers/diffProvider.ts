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
    // The URI path contains the original file path
    // Refactored content is stored in workspace state keyed by the file path
    const filePath = uri.path;
    const content = this.workspaceState.get<string>(
      `cloudshift.refactored.${filePath}`,
    );

    if (content === undefined) {
      return "// No refactored content available. Run a refactor command first.";
    }

    return content;
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
