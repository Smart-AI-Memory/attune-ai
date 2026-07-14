/**
 * Attune AI Dashboard — extension entry point.
 *
 * Minimal, cross-platform scaffold (see README). Feature growth
 * beyond telemetry viewing should go through a spec
 * (specs/vscode-extension/) per the workspace SDD discipline.
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under the Apache License, Version 2.0
 */

import * as vscode from "vscode";
import { DataProvider, telemetryDir } from "./DataProvider";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new DataProvider();

  context.subscriptions.push(
    provider,
    vscode.window.registerTreeDataProvider("attuneTelemetry", provider),
    vscode.commands.registerCommand("attune.refreshTelemetry", () =>
      provider.refresh()
    ),
    vscode.commands.registerCommand("attune.showDashboard", async () => {
      await vscode.commands.executeCommand("attuneTelemetry.focus");
      vscode.window.setStatusBarMessage(
        `Attune: reading telemetry from ${telemetryDir()}`,
        5000
      );
    })
  );
}

export function deactivate(): void {
  // Disposables are handled via context.subscriptions.
}
