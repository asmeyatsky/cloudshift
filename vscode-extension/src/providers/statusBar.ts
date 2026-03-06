import * as vscode from "vscode";

export class StatusBarProvider implements vscode.Disposable {
  private statusBarItem: vscode.StatusBarItem;
  private patternCount: number = 0;
  private fileCount: number = 0;
  private serverOnline: boolean = false;

  constructor() {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100,
    );
    this.statusBarItem.command = "cloudshift.scanProject";
    this.updateDisplay();
    this.statusBarItem.show();
  }

  setPatternCount(patterns: number, files: number): void {
    this.patternCount = patterns;
    this.fileCount = files;
    this.updateDisplay();
  }

  setServerStatus(online: boolean): void {
    this.serverOnline = online;
    this.updateDisplay();
  }

  private updateDisplay(): void {
    const serverIcon = this.serverOnline ? "$(cloud)" : "$(cloud-offline)";
    const serverStatus = this.serverOnline ? "Connected" : "Disconnected";

    if (this.patternCount > 0) {
      this.statusBarItem.text = `${serverIcon} CloudShift: ${this.patternCount} pattern(s) in ${this.fileCount} file(s)`;
      this.statusBarItem.tooltip = `CloudShift - Server: ${serverStatus}\n${this.patternCount} cloud construct pattern(s) found in ${this.fileCount} file(s).\nClick to re-scan.`;
    } else {
      this.statusBarItem.text = `${serverIcon} CloudShift`;
      this.statusBarItem.tooltip = `CloudShift - Server: ${serverStatus}\nClick to scan project.`;
    }

    if (!this.serverOnline) {
      this.statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground",
      );
    } else {
      this.statusBarItem.backgroundColor = undefined;
    }
  }

  dispose(): void {
    this.statusBarItem.dispose();
  }
}
