---
description: Implementation Plan: Attune AI UX Enhancements (Refined): This plan delivers interactive workflow experiences through three focused initiatives.
---

# Implementation Plan: Attune AI UX Enhancements (Refined)

This plan delivers interactive workflow experiences through three focused initiatives. Each builds on existing infrastructure (webview panels, XML prompts, Socratic refinement) to maximize velocity and minimize risk.

**Timeline:** 7-10 days total | **Risk Level:** Low-Medium | **User Impact:** High

---

## **Sprint 1: Interactive Code Review UI** (3-4 days) 🎯 **HIGH PRIORITY**

**Goal:** Transform code-review from terminal text to an interactive webview panel where findings are clickable, filterable, and actionable.

### Prerequisites (COMPLETED ✅)
- Data contracts defined: [WorkflowContracts.ts](vscode-extension/src/types/WorkflowContracts.ts)
- Webview patterns established: ResearchSynthesisPanel, GuidedPanelProvider
- XML-enhanced prompts ready for structured output

### Phase 1A: Backend - Structured Finding Extraction (6-8 hours)

**Files to Modify:**

1. **[code_review.py:421-530](src/attune/workflows/code_review.py)** - `_scan()` method
   ```python
   # After LLM call, extract structured findings
   findings = self._extract_findings_from_response(
       response=response,
       files_changed=files_changed,
       code_context=code_to_review
   )

   return {
       "scan_results": response,  # Keep for terminal display
       "findings": findings,      # NEW: structured data
       "security_findings": security_findings,
       # ... rest unchanged
   }
   ```

2. **[base.py](src/attune/workflows/base.py)** - Add helper method
   ```python
   def _extract_findings_from_response(
       self,
       response: str,
       files_changed: list[str],
       code_context: str
   ) -> list[dict]:
       """
       Extract structured findings from LLM response.

       Strategy:
       1. Try XML parsing first (if <finding> tags present)
       2. Fallback to regex for "file.py:line" patterns
       3. Map to WorkflowFinding schema
       """
       if '<finding>' in response:
           return self._parse_xml_findings(response)

       return self._parse_text_findings(response, files_changed)
   ```

**Starting Point:** Use existing `security_findings` from SecurityAuditCrew (already structured) to prove the UX pattern works before adding full LLM parsing.

**Success Criteria:**
- `attune workflow run code-review --target src/auth` returns JSON with `findings` array
- Each finding has: `file`, `line`, `severity`, `category`, `message`
- Workspace-relative paths resolve correctly

### Phase 1B: Frontend - CodeReviewPanelProvider (6-8 hours)

**Files to Create:**

1. **`vscode-extension/src/panels/CodeReviewPanelProvider.ts`** (new)
   - Template: Copy structure from ResearchSynthesisPanel
   - Implements `vscode.WebviewViewProvider`
   - Session state: `{ findings: WorkflowFinding[], filters: {...} }`
   - Message handlers:
     - `review:goToLocation` → opens file at line
     - `review:filter` → updates filtered findings
     - `review:groupBy` → toggles file/severity grouping

2. **`vscode-extension/src/panels/code-review.html`** (new)
   - Reuse CSS from [guided.css](vscode-extension/src/panels/guided.css)
   - UI components:
     - Findings table (grouped by file by default)
     - Severity badges: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
     - Filter controls (multi-select for severity/category)
     - Click handlers: `onclick="goToLocation('src/auth.py', 42)"`

**Key Implementation Details:**

```typescript
// In CodeReviewPanelProvider.ts
webviewView.webview.onDidReceiveMessage(async (message) => {
    switch (message.type) {
        case 'review:goToLocation':
            await vscode.commands.executeCommand('empathy.goToLocation', {
                file: message.file,
                line: message.line,
                column: message.column ?? 1
            });
            break;
    }
});
```

### Phase 1C: Navigation Command (1 hour)

**File to Modify:** [extension.ts](vscode-extension/src/extension.ts)

```typescript
// In activate()
context.subscriptions.push(
    vscode.commands.registerCommand('empathy.goToLocation',
        async (args: { file: string; line?: number; column?: number }) => {
            // Handle workspace-relative paths
            let uri: vscode.Uri;
            if (path.isAbsolute(args.file)) {
                uri = vscode.Uri.file(args.file);
            } else {
                const wsFolder = vscode.workspace.workspaceFolders?.[0];
                if (!wsFolder) {
                    vscode.window.showErrorMessage('No workspace open');
                    return;
                }
                uri = vscode.Uri.joinPath(wsFolder.uri, args.file);
            }

            const doc = await vscode.workspace.openTextDocument(uri);
            const line = (args.line ?? 1) - 1; // Convert to 0-indexed
            const col = (args.column ?? 1) - 1;

            await vscode.window.showTextDocument(doc, {
                selection: new vscode.Range(line, col, line, col),
                viewColumn: vscode.ViewColumn.One
            });
        }
    )
);
```

### Phase 1D: Integration (2-3 hours)

**File to Modify:** [EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts)

```typescript
// After workflow completion
if (workflowName === 'code-review' && result.findings) {
    const reviewPanel = CodeReviewPanelProvider.getInstance();
    reviewPanel.updateFindings(result);

    // Show the panel
    await vscode.commands.executeCommand('empathy-code-review.focus');

    // Notify user
    vscode.window.showInformationMessage(
        `Code review found ${result.findings.length} findings`,
        'View Findings'
    ).then(selection => {
        if (selection === 'View Findings') {
            vscode.commands.executeCommand('empathy-code-review.focus');
        }
    });
}
```

### Sprint 1 Success Metrics
- ✅ Clicking a finding opens correct file/line in <5 seconds
- ✅ Filtering by severity updates view instantly
- ✅ Works with multi-root workspaces
- ✅ 70%+ of code-review runs result in at least one finding clicked

**Outcome:** Users can run code reviews and instantly navigate to issues without manual searching, reducing remediation time by ~50%.

---

## **Sprint 2: Suggestive Workflow Actions** (2-3 days) 🟡 **MEDIUM PRIORITY**

**Goal:** Add intelligent workflow suggestions to reports WITHOUT automatic execution to avoid cost surprises and maintain user control.

**⚠️ DESIGN CHANGE from Original Plan:**

- **Original**: Automatic workflow chaining (high risk of cost explosion)
- **Refined**: Suggestive buttons with cost estimates (user confirmation required)

### Phase 2A: Cost Estimation Service (2-3 hours)

**File to Create:** `vscode-extension/src/services/CostEstimator.ts` (new)

```typescript
export class CostEstimator {
    private static readonly TOKEN_COST_PER_1K = {
        cheap: { input: 0.00025, output: 0.00125 },
        capable: { input: 0.003, output: 0.015 },
        premium: { input: 0.015, output: 0.075 }
    };

    /**
     * Estimate cost for a workflow based on file size
     */
    static estimateWorkflowCost(
        workflowName: string,
        fileSize: number,
        tier?: 'cheap' | 'capable' | 'premium'
    ): { estimatedCost: number; tokenEstimate: number } {
        // Rough heuristic: 1 char ≈ 0.25 tokens
        const inputTokens = (fileSize * 0.25);
        const outputTokens = inputTokens * 0.3; // Assume 30% output ratio

        const workflowTier = tier || this.getDefaultTier(workflowName);
        const costs = this.TOKEN_COST_PER_1K[workflowTier];

        const estimatedCost =
            (inputTokens / 1000 * costs.input) +
            (outputTokens / 1000 * costs.output);

        return {
            estimatedCost: Math.ceil(estimatedCost * 100) / 100, // Round to cents
            tokenEstimate: Math.ceil(inputTokens + outputTokens)
        };
    }

    private static getDefaultTier(workflowName: string): 'cheap' | 'capable' | 'premium' {
        const tierMap: Record<string, string> = {
            'code-review': 'premium',
            'refactor-plan': 'capable',
            'test-gen': 'capable',
            'debug': 'capable',
            'security-scan': 'capable'
        };
        return (tierMap[workflowName] || 'capable') as any;
    }
}
```

### Phase 2B: Add Action Buttons to CodeReviewPanel (3-4 hours)

**File to Modify:** `vscode-extension/src/panels/CodeReviewPanelProvider.ts`

Update webview HTML to include suggestive actions per file group:

```html
<div class="file-group">
    <h3>📄 ${file}</h3>
    <div class="findings-count">${findingCount} findings</div>

    <!-- Action buttons (only if relevant) -->
    <div class="suggested-actions">
        <button class="action-btn refactor-btn"
                data-file="${file}"
                onclick="suggestRefactor('${file}')">
            🔧 Plan Refactor
            <span class="cost-badge">~$${estimatedCost}</span>
        </button>

        <button class="action-btn test-btn"
                data-file="${file}"
                onclick="suggestTests('${file}')">
            🧪 Generate Tests
            <span class="cost-badge">~$${testCost}</span>
        </button>
    </div>

    <!-- Findings list -->
    <ul class="findings-list">
        ${findings.map(f => renderFinding(f)).join('')}
    </ul>
</div>
```

**Message Handler:**

```typescript
case 'workflow:suggest':
    const { workflowName, targetFile } = message;

    // Show confirmation with cost estimate
    const confirmed = await vscode.window.showInformationMessage(
        `Run ${workflowName} on ${targetFile}? Estimated cost: $${message.estimatedCost}`,
        { modal: true },
        'Run Workflow',
        'Cancel'
    );

    if (confirmed === 'Run Workflow') {
        await vscode.commands.executeCommand('empathy.runWorkflow', workflowName, {
            target: targetFile,
            source: 'code-review-suggestion'
        });
    }
    break;
```

### Phase 2C: Pattern Learning Integration (2-3 hours)

**File to Modify:** `vscode-extension/src/services/PatternLearner.ts`

Track which suggestions users accept:

```typescript
// After user confirms workflow suggestion
await this.patternLearner.recordSuggestionAccepted({
    sourceWorkflow: 'code-review',
    suggestedWorkflow: 'refactor-plan',
    context: {
        findingSeverity: 'high',
        findingCount: 5,
        fileType: '.py'
    }
});

// Next time, auto-suggest based on learned patterns
const suggestions = await this.patternLearner.getSuggestions({
    currentWorkflow: 'code-review',
    findings: currentFindings
});
// suggestions = ['refactor-plan', 'test-gen'] (ranked by past acceptance rate)
```

### Phase 2D: Conditional Button Rendering (2 hours)

Only show action buttons when contextually relevant:

**Rules:**

- **Plan Refactor** button appears when:
  - 3+ high/critical severity findings in file
  - OR file has complexity score >15 (if available)
- **Generate Tests** button appears when:
  - File has <60% test coverage (from test-gen data)
  - OR file modified recently but tests not updated

**Implementation:**

```typescript
function shouldShowRefactorButton(file: string, findings: WorkflowFinding[]): boolean {
    const highSevFindings = findings.filter(f =>
        f.file === file && ['critical', 'high'].includes(f.severity)
    );
    return highSevFindings.length >= 3;
}
```

### Sprint 2 Success Metrics

- ✅ 40%+ click-through rate on suggested actions
- ✅ Zero cost-related complaints (transparency working)
- ✅ Pattern learning achieves >60% accuracy after 10 workflow runs
- ✅ Users report feeling "guided" vs "automated"

**Outcome:** Users get intelligent next-step suggestions with full transparency and control, avoiding cost surprises while reducing workflow friction.

---

## **Sprint 3: Configuration Simplification** (DEFERRED) ⏸️ **LOWER PRIORITY**

**Status:** Deprioritized in favor of workflow UX improvements.

### Why Deferred

1. **Target audience** (developers) are comfortable with YAML
2. **Low complaint volume** - config editing hasn't been a pain point
3. **Better alternative exists** - VSCode JSON schema provides 90% of benefits

### Alternative: JSON Schema Validation (1-2 hours)

Instead of building a custom UI, add schema validation:

**File to Create:** `empathy-config.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Attune AI Configuration",
  "type": "object",
  "properties": {
    "model_tier_defaults": {
      "type": "object",
      "description": "Default model tiers for workflows",
      "properties": {
        "code-review": {
          "type": "string",
          "enum": ["cheap", "capable", "premium"],
          "default": "capable"
        }
      }
    },
    "beta_features": {
      "type": "object",
      "properties": {
        "show_memory_panel": {
          "type": "boolean",
          "default": false,
          "description": "Enable Memory Control Panel (beta)"
        }
      }
    }
  }
}
```

**File to Modify:** `vscode-extension/package.json`

```json
"contributes": {
    "yamlValidation": [
        {
            "fileMatch": "empathy.config.yml",
            "url": "./empathy-config.schema.json"
        }
    ]
}
```

**Benefits:**

- ✅ Auto-complete in VSCode
- ✅ Inline validation errors
- ✅ Hover documentation
- ✅ No UI maintenance burden

### If Custom UI Becomes Required (Future)

Use VSCode's native Settings Contribution instead of custom webview:

**File to Modify:** `package.json`

```json
"contributes": {
    "configuration": {
        "title": "Attune AI",
        "properties": {
            "empathy.defaultModelTier": {
                "type": "string",
                "enum": ["cheap", "capable", "premium"],
                "default": "capable",
                "markdownDescription": "Default model tier for workflows\n\n- **cheap**: GPT-4o-mini / Haiku (~$0.001/workflow)\n- **capable**: GPT-4o / Sonnet (~$0.05/workflow)\n- **premium**: o1 / Opus (~$0.15/workflow)"
            },
            "empathy.betaFeatures.memoryPanel": {
                "type": "boolean",
                "default": false,
                "description": "Enable Memory Control Panel (experimental)"
            }
        }
    }
}
```

**Effort:** 1-2 hours vs. 4-5 days for custom webview UI

**Outcome:** Config validation with minimal effort, deferring complex UI work until user demand proves it necessary.

---

## Testing & QA Strategy

### Unit Tests (TypeScript)

**Files to Test:**

1. **`empathy.goToLocation` command**
   - ✅ Resolves workspace-relative paths
   - ✅ Handles multi-root workspaces
   - ✅ Opens correct file at line number
   - ✅ Handles missing files gracefully

2. **CodeReviewPanelProvider message handlers**
   - ✅ `review:goToLocation` calls command correctly
   - ✅ `review:filter` updates session state
   - ✅ `workflow:suggest` shows cost confirmation

3. **CostEstimator**
   - ✅ Estimates scale linearly with file size
   - ✅ Different tiers have correct price ratios
   - ✅ Rounds to nearest cent

### Integration Tests (Manual QA)

**Scenario 1: End-to-End Code Review Flow**

1. Open workspace with Python files
2. Run `empathy.runWorkflow` → `code-review` → select file
3. Verify:
   - ✅ CodeReviewPanel opens with findings
   - ✅ Clicking finding navigates to correct line
   - ✅ Severity badges display correctly
   - ✅ Filters update view dynamically

**Scenario 2: Workflow Suggestion Flow**

1. Complete code review with 5+ high-severity findings in one file
2. Verify:
   - ✅ "Plan Refactor" button appears for that file
   - ✅ Cost estimate is displayed
   - ✅ Clicking shows confirmation dialog
   - ✅ Confirming triggers refactor-plan workflow
   - ✅ PatternLearner records the acceptance

**Scenario 3: Multi-Workspace Support**

1. Open multi-root workspace
2. Run code review on file in second workspace folder
3. Verify:
   - ✅ Findings resolve correct workspace paths
   - ✅ Navigation opens file in correct workspace

### Regression Testing

**Files to Monitor:**

- [EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts) - Ensure existing workflow execution still works
- [WorkflowHistoryService.ts](vscode-extension/src/services/WorkflowHistoryService.ts) - Verify history still records
- [WorkflowRefinementService.ts](vscode-extension/src/services/WorkflowRefinementService.ts) - Socratic refinement still triggers

---

## Implementation Checklist

### Sprint 1: Interactive Code Review (3-4 days)

- [ ] **Phase 1A: Backend** (6-8 hours)
  - [ ] Add `_extract_findings_from_response()` to base.py
  - [ ] Modify code_review.py `_scan()` to return structured findings
  - [ ] Test with: `attune workflow run code-review --target src/`

- [ ] **Phase 1B: Frontend** (6-8 hours)
  - [ ] Create CodeReviewPanelProvider.ts
  - [ ] Create code-review.html webview
  - [ ] Implement filtering and grouping logic
  - [ ] Add message handlers (goToLocation, filter, groupBy)

- [ ] **Phase 1C: Navigation** (1 hour)
  - [ ] Implement `empathy.goToLocation` command
  - [ ] Register in extension.ts
  - [ ] Test multi-workspace support

- [ ] **Phase 1D: Integration** (2-3 hours)
  - [ ] Wire CodeReviewPanel into workflow completion
  - [ ] Add notification on review complete
  - [ ] Test end-to-end flow

### Sprint 2: Workflow Suggestions (2-3 days)

- [ ] **Phase 2A: Cost Estimation** (2-3 hours)
  - [ ] Create CostEstimator.ts service
  - [ ] Add tier pricing configuration
  - [ ] Test estimation accuracy

- [ ] **Phase 2B: Action Buttons** (3-4 hours)
  - [ ] Add suggestive action buttons to webview
  - [ ] Implement conditional rendering logic
  - [ ] Add confirmation dialogs with cost display

- [ ] **Phase 2C: Pattern Learning** (2-3 hours)
  - [ ] Integrate PatternLearner tracking
  - [ ] Record suggestion acceptance/rejection
  - [ ] Implement suggestion ranking

### Sprint 3: Config Schema (DEFERRED)

- [ ] **Alternative Implementation** (1-2 hours)
  - [ ] Create empathy-config.schema.json
  - [ ] Add YAML validation to package.json
  - [ ] Test auto-complete and validation

---

## Success Criteria

**Ready to Ship When:**

1. ✅ Code review findings are clickable and navigate correctly (>95% success rate)
2. ✅ All unit tests pass for new components
3. ✅ Manual QA checklist completed without blockers
4. ✅ Cost estimates accurate within ±20%
5. ✅ Works in multi-root workspaces
6. ✅ No regressions in existing workflows
7. ✅ Documentation updated (CHANGELOG.md, QA_CHECKLIST.md)

**Post-Launch Monitoring:**

- User engagement: 70%+ of code reviews result in finding clicks
- Cost transparency: Zero cost-related support tickets
- Pattern learning: Suggestion accuracy >60% after 10 runs
- User feedback: NPS score increase >10 points

---

## Timeline Summary

| Phase | Duration | Dependencies | Risk |
|-------|----------|--------------|------|
| **Sprint 1: Interactive Code Review** | 3-4 days | None (ready to start) | LOW |
| **Sprint 2: Workflow Suggestions** | 2-3 days | Sprint 1 complete | MEDIUM |
| **Sprint 3: Config Schema** | 1-2 hours | None (can run parallel) | LOW |
| **Total Timeline** | **7-10 days** | Sequential execution | **LOW-MEDIUM** |

**Critical Path:** Sprint 1 → Sprint 2 (Sprint 3 can run anytime)

---

## Next Steps

**Immediate Action Items:**

1. ✅ **Data contracts defined** - WorkflowContracts.ts created
2. 🔄 **Backend finding extraction** - IN PROGRESS (next step)
   - Add `_extract_findings_from_response()` to base.py
   - Modify code_review.py to return structured findings
3. ⏸️ **CodeReviewPanelProvider** - BLOCKED on step 2
4. ⏸️ **Navigation command** - BLOCKED on step 2

**Starting Point:** Begin with Phase 1A, Step 2 - Backend finding extraction in [code_review.py](src/attune/workflows/code_review.py).
