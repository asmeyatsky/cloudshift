import * as vscode from "vscode";
import { PatternMatch } from "../client/apiClient";

export class GutterAnnotationProvider implements vscode.Disposable {
  private decorationType: vscode.TextEditorDecorationType;
  private annotations: Map<string, PatternMatch[]> = new Map();
  private disposables: vscode.Disposable[] = [];

  constructor() {
    this.decorationType = vscode.window.createTextEditorDecorationType({
      gutterIconPath: new vscode.ThemeIcon("cloud").id,
      gutterIconSize: "contain",
      backgroundColor: new vscode.ThemeColor(
        "editorInfo.background",
      ),
      overviewRulerColor: new vscode.ThemeColor(
        "editorInfo.foreground",
      ),
      overviewRulerLane: vscode.OverviewRulerLane.Right,
      isWholeLine: true,
      after: {
        margin: "0 0 0 1em",
        color: new vscode.ThemeColor("editorCodeLens.foreground"),
      },
    });

    // Re-apply decorations when the active editor changes
    this.disposables.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
          this.applyDecorations(editor);
        }
      }),
    );

    // Re-apply decorations when a document changes
    this.disposables.push(
      vscode.workspace.onDidChangeTextDocument((event) => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document === event.document) {
          this.applyDecorations(editor);
        }
      }),
    );
  }

  setAnnotations(filePath: string, patterns: PatternMatch[]): void {
    this.annotations.set(filePath, patterns);

    // Apply to active editor if it matches
    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.uri.fsPath === filePath) {
      this.applyDecorations(editor);
    }
  }

  clearAnnotations(filePath: string): void {
    this.annotations.delete(filePath);

    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.uri.fsPath === filePath) {
      editor.setDecorations(this.decorationType, []);
    }
  }

  clearAll(): void {
    this.annotations.clear();

    // Clear decorations on all visible editors
    for (const editor of vscode.window.visibleTextEditors) {
      editor.setDecorations(this.decorationType, []);
    }
  }

  private applyDecorations(editor: vscode.TextEditor): void {
    const filePath = editor.document.uri.fsPath;
    const patterns = this.annotations.get(filePath);

    if (!patterns || patterns.length === 0) {
      editor.setDecorations(this.decorationType, []);
      return;
    }

    const decorations: vscode.DecorationOptions[] = patterns.map((pattern) => {
      const startLine = Math.max(0, pattern.line - 1);
      const endLine = Math.max(0, (pattern.endLine || pattern.line) - 1);
      const range = new vscode.Range(
        startLine,
        0,
        endLine,
        editor.document.lineAt(Math.min(endLine, editor.document.lineCount - 1))
          .text.length,
      );

      return {
        range,
        hoverMessage: new vscode.MarkdownString(
          `**CloudShift** - ${pattern.patternName}\n\n` +
            `${pattern.message}\n\n` +
            `Source: \`${pattern.sourceProvider}\` -> Target: \`${pattern.targetProvider}\`\n\n` +
            `Severity: ${pattern.severity}`,
        ),
        renderOptions: {
          after: {
            contentText: ` // ${pattern.patternName}`,
          },
        },
      };
    });

    editor.setDecorations(this.decorationType, decorations);
  }

  dispose(): void {
    this.decorationType.dispose();
    for (const disposable of this.disposables) {
      disposable.dispose();
    }
  }
}
