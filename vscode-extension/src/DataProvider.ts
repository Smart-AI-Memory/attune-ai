/**
 * Tree data provider for Attune AI telemetry.
 *
 * Cross-platform rules baked in from day one:
 * - Every filesystem path is built with path.join() — never string
 *   concatenation with "/" (breaks on Windows).
 * - The telemetry directory honors ATTUNE_HOME, falling back to
 *   ~/.attune (os.homedir() is correct on all three OSes).
 * - File watching uses vscode.workspace.createFileSystemWatcher —
 *   fs.watch is unreliable on Windows (duplicate/missed events) and
 *   macOS (FSEvents coalescing); the VS Code watcher abstracts both.
 * - Files are read with an explicit utf-8 encoding.
 *
 * Redis is intentionally NOT contacted from the extension: the
 * telemetry files written by the Python hook layer are the contract.
 * When Redis-backed memory is active, the Python side still mirrors
 * events to the JSONL files this provider reads.
 *
 * Copyright 2026 Smart-AI-Memory
 * Licensed under the Apache License, Version 2.0
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

/** Resolve the Attune home directory (ATTUNE_HOME or ~/.attune). */
export function attuneHome(): string {
  const override = process.env.ATTUNE_HOME;
  if (override && override.trim().length > 0) {
    return override;
  }
  return path.join(os.homedir(), ".attune");
}

/** Directory containing telemetry JSONL files. */
export function telemetryDir(): string {
  return path.join(attuneHome(), "telemetry");
}

interface TelemetryEvent {
  ts?: string;
  event?: string;
  [key: string]: unknown;
}

export class TelemetryItem extends vscode.TreeItem {
  constructor(label: string, description?: string) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = description;
  }
}

export class DataProvider
  implements vscode.TreeDataProvider<TelemetryItem>, vscode.Disposable
{
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<
    TelemetryItem | undefined
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private watcher: vscode.FileSystemWatcher | undefined;
  private static readonly MAX_EVENTS = 50;

  constructor() {
    this.startWatching();
  }

  /**
   * Watch the telemetry directory with the VS Code watcher (not
   * fs.watch). RelativePattern accepts a base Uri, which handles
   * drive letters and UNC paths on Windows correctly.
   */
  private startWatching(): void {
    const dir = telemetryDir();
    const pattern = new vscode.RelativePattern(
      vscode.Uri.file(dir),
      "*.jsonl"
    );
    this.watcher = vscode.workspace.createFileSystemWatcher(pattern);
    this.watcher.onDidChange(() => this.refresh());
    this.watcher.onDidCreate(() => this.refresh());
    this.watcher.onDidDelete(() => this.refresh());
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: TelemetryItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: TelemetryItem): TelemetryItem[] {
    if (element) {
      return [];
    }
    return this.readRecentEvents();
  }

  /** Read the tail of every telemetry JSONL file, newest first. */
  private readRecentEvents(): TelemetryItem[] {
    const dir = telemetryDir();
    let files: string[];
    try {
      files = fs
        .readdirSync(dir)
        .filter((f) => f.endsWith(".jsonl"))
        .map((f) => path.join(dir, f));
    } catch {
      return [
        new TelemetryItem(
          "No telemetry yet",
          `waiting for ${dir} — file backend not written`
        ),
      ];
    }

    const events: TelemetryEvent[] = [];
    for (const file of files) {
      try {
        const lines = fs
          .readFileSync(file, { encoding: "utf-8" })
          .split("\n")
          .filter((l) => l.trim().length > 0)
          .slice(-DataProvider.MAX_EVENTS);
        for (const line of lines) {
          try {
            events.push(JSON.parse(line) as TelemetryEvent);
          } catch {
            // Skip malformed lines (partial writes are tolerated,
            // never fatal).
          }
        }
      } catch {
        // Unreadable file — skip; never surface an error tree.
      }
    }

    events.sort((a, b) => String(b.ts ?? "").localeCompare(String(a.ts ?? "")));
    if (events.length === 0) {
      return [new TelemetryItem("No events recorded", dir)];
    }
    return events
      .slice(0, DataProvider.MAX_EVENTS)
      .map(
        (e) =>
          new TelemetryItem(String(e.event ?? "event"), String(e.ts ?? ""))
      );
  }

  dispose(): void {
    this.watcher?.dispose();
    this._onDidChangeTreeData.dispose();
  }
}
