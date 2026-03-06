import * as vscode from "vscode";
import { ValidationResult } from "../client/apiClient";

export class ValidationPanel {
  public static currentPanel: ValidationPanel | undefined;
  private static readonly viewType = "cloudshiftValidation";

  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];

  public static createOrShow(
    extensionUri: vscode.Uri,
    result: ValidationResult,
  ): void {
    const column = vscode.ViewColumn.Beside;

    // If a panel already exists, update its content
    if (ValidationPanel.currentPanel) {
      ValidationPanel.currentPanel.panel.reveal(column);
      ValidationPanel.currentPanel.update(result);
      return;
    }

    // Create a new panel
    const panel = vscode.window.createWebviewPanel(
      ValidationPanel.viewType,
      "CloudShift Validation",
      column,
      {
        enableScripts: false,
        localResourceRoots: [],
      },
    );

    ValidationPanel.currentPanel = new ValidationPanel(panel, result);
  }

  private constructor(panel: vscode.WebviewPanel, result: ValidationResult) {
    this.panel = panel;

    this.update(result);

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  public update(result: ValidationResult): void {
    this.panel.title = `Validation: ${vscode.workspace.asRelativePath(result.file)}`;
    this.panel.webview.html = this.getHtml(result);
  }

  private getHtml(result: ValidationResult): string {
    const statusIcon = result.valid ? "&#10003;" : "&#10007;";
    const statusColor = result.valid ? "#4ec9b0" : "#f44747";
    const statusText = result.valid ? "PASSED" : "FAILED";

    const errorsHtml =
      result.errors.length > 0
        ? result.errors
            .map(
              (e) => `
          <tr>
            <td class="severity error">ERROR</td>
            <td>Line ${e.line}, Col ${e.column}</td>
            <td>${this.escapeHtml(e.message)}</td>
            <td><code>${this.escapeHtml(e.rule)}</code></td>
          </tr>`,
            )
            .join("\n")
        : "";

    const warningsHtml =
      result.warnings.length > 0
        ? result.warnings
            .map(
              (w) => `
          <tr>
            <td class="severity warning">WARN</td>
            <td>Line ${w.line}, Col ${w.column}</td>
            <td>${this.escapeHtml(w.message)}</td>
            <td><code>${this.escapeHtml(w.rule)}</code></td>
          </tr>`,
            )
            .join("\n")
        : "";

    const hasIssues = result.errors.length > 0 || result.warnings.length > 0;

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CloudShift Validation</title>
  <style>
    body {
      font-family: var(--vscode-font-family, sans-serif);
      color: var(--vscode-foreground, #cccccc);
      background-color: var(--vscode-editor-background, #1e1e1e);
      padding: 16px;
      margin: 0;
    }

    h1 {
      font-size: 1.4em;
      margin-bottom: 8px;
    }

    .status {
      font-size: 1.2em;
      font-weight: bold;
      margin-bottom: 16px;
      padding: 8px 12px;
      border-radius: 4px;
      display: inline-block;
    }

    .file-path {
      color: var(--vscode-textLink-foreground, #3794ff);
      margin-bottom: 16px;
      font-size: 0.9em;
    }

    .summary {
      margin-bottom: 16px;
      font-size: 0.95em;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
    }

    th {
      text-align: left;
      padding: 6px 10px;
      border-bottom: 1px solid var(--vscode-panel-border, #444);
      font-size: 0.85em;
      color: var(--vscode-descriptionForeground, #999);
    }

    td {
      padding: 6px 10px;
      border-bottom: 1px solid var(--vscode-panel-border, #333);
      font-size: 0.9em;
    }

    .severity {
      font-weight: bold;
      font-size: 0.8em;
    }

    .severity.error {
      color: #f44747;
    }

    .severity.warning {
      color: #cca700;
    }

    .no-issues {
      color: #4ec9b0;
      font-style: italic;
      margin-top: 16px;
    }

    code {
      background: var(--vscode-textCodeBlock-background, #2d2d2d);
      padding: 1px 4px;
      border-radius: 3px;
      font-size: 0.85em;
    }
  </style>
</head>
<body>
  <h1>CloudShift Validation Results</h1>
  <div class="file-path">${this.escapeHtml(result.file)}</div>
  <div class="status" style="color: ${statusColor}; border: 1px solid ${statusColor};">
    ${statusIcon} ${statusText}
  </div>
  <div class="summary">
    ${result.errors.length} error(s), ${result.warnings.length} warning(s)
  </div>

  ${
    hasIssues
      ? `
  <table>
    <thead>
      <tr>
        <th>Severity</th>
        <th>Location</th>
        <th>Message</th>
        <th>Rule</th>
      </tr>
    </thead>
    <tbody>
      ${errorsHtml}
      ${warningsHtml}
    </tbody>
  </table>`
      : '<div class="no-issues">No issues found. The transformation is valid.</div>'
  }
</body>
</html>`;
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  private dispose(): void {
    ValidationPanel.currentPanel = undefined;
    this.panel.dispose();
    for (const disposable of this.disposables) {
      disposable.dispose();
    }
    this.disposables = [];
  }
}
