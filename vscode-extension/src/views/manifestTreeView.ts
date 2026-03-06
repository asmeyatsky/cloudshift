import * as path from "path";
import * as vscode from "vscode";
import { PatternMatch, ScanResult } from "../client/apiClient";

type ManifestTreeItem = FileGroupItem | PatternItem;

export class ManifestTreeProvider
  implements vscode.TreeDataProvider<ManifestTreeItem>
{
  private _onDidChangeTreeData =
    new vscode.EventEmitter<ManifestTreeItem | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private fileGroups: Map<string, PatternMatch[]> = new Map();

  updateFromScanResults(results: ScanResult[]): void {
    this.fileGroups.clear();
    for (const result of results) {
      if (result.patterns.length > 0) {
        this.fileGroups.set(result.file, result.patterns);
      }
    }
    this._onDidChangeTreeData.fire();
  }

  clear(): void {
    this.fileGroups.clear();
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ManifestTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ManifestTreeItem): ManifestTreeItem[] {
    if (!element) {
      // Root level: return file groups
      const items: FileGroupItem[] = [];
      for (const [filePath, patterns] of this.fileGroups) {
        items.push(new FileGroupItem(filePath, patterns));
      }
      return items.sort((a, b) => a.filePath.localeCompare(b.filePath));
    }

    if (element instanceof FileGroupItem) {
      // File level: return individual patterns
      return element.patterns.map(
        (pattern) => new PatternItem(pattern, element.filePath),
      );
    }

    return [];
  }
}

class FileGroupItem extends vscode.TreeItem {
  constructor(
    public readonly filePath: string,
    public readonly patterns: PatternMatch[],
  ) {
    const relativePath = vscode.workspace.asRelativePath(filePath);
    super(relativePath, vscode.TreeItemCollapsibleState.Collapsed);

    this.description = `${patterns.length} pattern(s)`;
    this.tooltip = `${filePath}\n${patterns.length} cloud construct pattern(s) found`;
    this.iconPath = new vscode.ThemeIcon("file-code");
    this.contextValue = "cloudshiftFileGroup";

    this.command = {
      command: "vscode.open",
      title: "Open File",
      arguments: [vscode.Uri.file(filePath)],
    };
  }
}

class PatternItem extends vscode.TreeItem {
  constructor(
    public readonly pattern: PatternMatch,
    public readonly filePath: string,
  ) {
    super(pattern.patternName, vscode.TreeItemCollapsibleState.None);

    this.description = `Line ${pattern.line}`;
    this.tooltip = new vscode.MarkdownString(
      `**${pattern.patternName}**\n\n` +
        `${pattern.message}\n\n` +
        `- Source: \`${pattern.sourceProvider}\`\n` +
        `- Target: \`${pattern.targetProvider}\`\n` +
        `- Line: ${pattern.line}\n` +
        `- Severity: ${pattern.severity}`,
    );

    this.iconPath = this.getSeverityIcon(pattern.severity);
    this.contextValue = "cloudshiftPattern";

    // Click navigates to the pattern location
    const line = Math.max(0, pattern.line - 1);
    const col = Math.max(0, (pattern.column || 1) - 1);
    this.command = {
      command: "vscode.open",
      title: "Go to Pattern",
      arguments: [
        vscode.Uri.file(filePath),
        {
          selection: new vscode.Range(line, col, line, col),
        } as vscode.TextDocumentShowOptions,
      ],
    };
  }

  private getSeverityIcon(severity: string): vscode.ThemeIcon {
    switch (severity) {
      case "error":
        return new vscode.ThemeIcon(
          "error",
          new vscode.ThemeColor("errorForeground"),
        );
      case "warning":
        return new vscode.ThemeIcon(
          "warning",
          new vscode.ThemeColor("list.warningForeground"),
        );
      case "info":
      default:
        return new vscode.ThemeIcon(
          "info",
          new vscode.ThemeColor("notificationsInfoIcon.foreground"),
        );
    }
  }
}
