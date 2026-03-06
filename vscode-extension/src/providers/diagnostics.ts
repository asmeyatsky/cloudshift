import * as vscode from "vscode";
import {
  PatternMatch,
  ValidationError,
  ValidationWarning,
} from "../client/apiClient";

export class CloudShiftDiagnosticsProvider implements vscode.Disposable {
  private scanDiagnostics: vscode.DiagnosticCollection;
  private validationDiagnostics: vscode.DiagnosticCollection;

  constructor() {
    this.scanDiagnostics =
      vscode.languages.createDiagnosticCollection("cloudshift-scan");
    this.validationDiagnostics =
      vscode.languages.createDiagnosticCollection("cloudshift-validation");
  }

  /**
   * Set diagnostics from scan results (cloud construct detections).
   */
  setDiagnosticsFromScan(filePath: string, patterns: PatternMatch[]): void {
    const uri = vscode.Uri.file(filePath);

    const diagnostics: vscode.Diagnostic[] = patterns.map((pattern) => {
      const startLine = Math.max(0, pattern.line - 1);
      const endLine = Math.max(0, (pattern.endLine || pattern.line) - 1);
      const startCol = Math.max(0, (pattern.column || 1) - 1);
      const endCol = Math.max(0, (pattern.endColumn || 999) - 1);

      const range = new vscode.Range(startLine, startCol, endLine, endCol);

      const severity = this.mapSeverity(pattern.severity);

      const diagnostic = new vscode.Diagnostic(
        range,
        `${pattern.patternName}: ${pattern.message}`,
        severity,
      );
      diagnostic.source = "CloudShift";
      diagnostic.code = pattern.patternId;
      return diagnostic;
    });

    this.scanDiagnostics.set(uri, diagnostics);
  }

  /**
   * Set diagnostics from validation results.
   */
  setDiagnosticsFromValidation(
    filePath: string,
    errors: ValidationError[],
    warnings: ValidationWarning[],
  ): void {
    const uri = vscode.Uri.file(filePath);
    const diagnostics: vscode.Diagnostic[] = [];

    for (const error of errors) {
      const line = Math.max(0, error.line - 1);
      const col = Math.max(0, (error.column || 1) - 1);
      const range = new vscode.Range(line, col, line, col + 1);

      const diagnostic = new vscode.Diagnostic(
        range,
        error.message,
        vscode.DiagnosticSeverity.Error,
      );
      diagnostic.source = "CloudShift Validation";
      diagnostic.code = error.rule;
      diagnostics.push(diagnostic);
    }

    for (const warning of warnings) {
      const line = Math.max(0, warning.line - 1);
      const col = Math.max(0, (warning.column || 1) - 1);
      const range = new vscode.Range(line, col, line, col + 1);

      const diagnostic = new vscode.Diagnostic(
        range,
        warning.message,
        vscode.DiagnosticSeverity.Warning,
      );
      diagnostic.source = "CloudShift Validation";
      diagnostic.code = warning.rule;
      diagnostics.push(diagnostic);
    }

    this.validationDiagnostics.set(uri, diagnostics);
  }

  clearAll(): void {
    this.scanDiagnostics.clear();
    this.validationDiagnostics.clear();
  }

  clearFile(filePath: string): void {
    const uri = vscode.Uri.file(filePath);
    this.scanDiagnostics.delete(uri);
    this.validationDiagnostics.delete(uri);
  }

  private mapSeverity(severity: string): vscode.DiagnosticSeverity {
    switch (severity) {
      case "error":
        return vscode.DiagnosticSeverity.Error;
      case "warning":
        return vscode.DiagnosticSeverity.Warning;
      case "info":
      default:
        return vscode.DiagnosticSeverity.Information;
    }
  }

  dispose(): void {
    this.scanDiagnostics.dispose();
    this.validationDiagnostics.dispose();
  }
}
