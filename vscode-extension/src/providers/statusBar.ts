import * as vscode from "vscode";
import { ApiClient } from "../client/apiClient";

export class StatusBarProvider implements vscode.Disposable {
  private statusBarItem: vscode.StatusBarItem;
  private patternCount: number = 0;
  private fileCount: number = 0;
  private serverOnline: boolean = false;
  private healthInterval?: NodeJS.Timeout;

  constructor(private apiClient: ApiClient) {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100,
    );
    this.statusBarItem.command = "cloudshift.scanProject";
    this.updateDisplay();
    this.statusBarItem.show();
    this.startHealthCheck();
  }

  private startHealthCheck(): void {
    const check = async () => {
      try {
        const online = await this.apiClient.healthCheck();
        this.setServerStatus(online);
      } catch {
        this.setServerStatus(false);
      }
    };
    
    // Initial check
    check();
    // Poll every 30 seconds
    this.healthInterval = setInterval(check, 30000);
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
        "statusBarItem.errorBackground",
      );
    } else {
      this.statusBarItem.backgroundColor = undefined;
    }
  }

  dispose(): void {
    if (this.healthInterval) {
      clearInterval(this.healthInterval);
    }
    this.statusBarItem.dispose();
  }
}
