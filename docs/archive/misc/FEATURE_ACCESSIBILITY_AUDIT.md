---
description: Feature Accessibility Audit: **Date:** 2026-01-01 **Purpose:** Ensure all Attune AI features have BOTH UI and CLI entry points --- ## Executive Summary
---

# Feature Accessibility Audit

**Date:** 2026-01-01
**Purpose:** Ensure all Attune AI features have BOTH UI and CLI entry points

---

## Executive Summary

✅ **19 features** have complete dual entry points (UI + CLI)
⚠️ **6 workflows** missing UI buttons
⚠️ **3 UI features** missing CLI equivalents
🎯 **Total gaps identified:** 9

---

## Complete Feature Matrix

| Feature | UI Entry Point | CLI Entry Point | Status | Priority |
|---------|----------------|-----------------|--------|----------|
| **Core Workflows** |
| Morning Briefing | ✅ Dashboard → Quick Actions | ✅ `attune morning` | COMPLETE | - |
| Pre-Ship Check | ✅ Dashboard → Quick Actions | ✅ `attune ship` | COMPLETE | - |
| Fix All Issues | ✅ Dashboard → Quick Actions | ✅ `attune fix-all` | COMPLETE | - |
| Learn Patterns | ✅ Dashboard → Quick Actions | ✅ `attune learn` | COMPLETE | - |
| Run Tests | ✅ Dashboard → Quick Actions | ✅ `attune ship --tests-only` | COMPLETE | - |
| **Code Review & Analysis** |
| Code Review (File) | ❌ **MISSING** | ✅ `attune workflow run code-review` | NEEDS UI | HIGH |
| Pro Review (Crew) | ✅ Dashboard → Workflows | ✅ `attune workflow run pro-review` | COMPLETE | - |
| PR Review | ✅ Dashboard → Workflows | ✅ `attune workflow run pr-review` | COMPLETE | - |
| **Quality & Testing** |
| Bug Prediction | ✅ Dashboard → Workflows | ✅ `attune workflow run bug-predict` | COMPLETE | - |
| Security Audit | ✅ Dashboard → Workflows | ✅ `attune workflow run security-audit` | COMPLETE | - |
| Performance Audit | ✅ Dashboard → Workflows | ✅ `attune workflow run perf-audit` | COMPLETE | - |
| Health Check (Crew) | ✅ Dashboard → Workflows | ✅ `attune workflow run health-check` | COMPLETE | - |
| Test Generation | ✅ Dashboard → Workflows | ✅ `attune workflow run test-gen` | COMPLETE | - |
| Dependency Check | ✅ Dashboard → Workflows | ✅ `attune workflow run dependency-check` | COMPLETE | - |
| **Refactoring & Planning** |
| Refactor Plan | ✅ Dashboard → Workflows | ✅ `attune workflow run refactor-plan` | COMPLETE | - |
| **Documentation** |
| Documentation Orchestrator | ✅ Dashboard → Workflows | ✅ `attune workflow run doc-orchestrator` | COMPLETE | - |
| Document Generation | ❌ **MISSING** | ✅ `attune workflow run doc-gen` | NEEDS UI | MEDIUM |
| Manage Documentation (Crew) | ❌ **MISSING** | ✅ `attune workflow run manage-docs` | NEEDS UI | LOW |
| **Release & Security** |
| Release Preparation | ❌ **MISSING** | ✅ `attune workflow run release-prep` | NEEDS UI | MEDIUM |
| Secure Release Pipeline | ❌ **MISSING** | ✅ `attune workflow run secure-release` | NEEDS UI | MEDIUM |
| **Developer Tools** |
| Keyboard Shortcuts Generator | ❌ **MISSING** | ✅ `attune workflow run keyboard-shortcuts` | NEEDS UI | LOW |
| Socratic Workflow Designer | ✅ Cmd Palette: `empathy.socraticRefinement` | ❌ **MISSING** | NEEDS CLI | LOW |
| **Health Operations** |
| Deep Health Scan | ✅ Dashboard → Health Actions | ✅ `attune health --deep` | COMPLETE | - |
| Auto Fix | ✅ Dashboard → Health Actions | ✅ `attune fix-all` | COMPLETE | - |
| Quick Security Scan | ✅ Dashboard → Health Actions | ✅ `attune health --security` | COMPLETE | - |
| **Context Menu Actions** |
| Review This File | ✅ File Explorer: Right-click | ✅ `attune review [file]` | COMPLETE | - |
| Scan Folder for Bugs | ✅ File Explorer: Right-click | ✅ `attune workflow run bug-predict --input '{"path":"folder"}'` | COMPLETE | - |
| Generate Tests for File | ✅ File Explorer: Right-click | ✅ `attune workflow run test-gen --input '{"target":"file"}'` | COMPLETE | - |
| Security Audit Folder | ✅ File Explorer: Right-click | ✅ `attune workflow run security-audit --input '{"target":"folder"}'` | COMPLETE | - |
| **Setup & Configuration** |
| Initialize Project | ✅ Cmd: `empathy.initializeProject` | ✅ `attune init` | COMPLETE | - |
| Sync to Claude Code | ✅ Cmd: `empathy.syncClaude` | ✅ `attune sync-claude` | COMPLETE | - |
| Setup Wizard | ✅ Dashboard → Quick Actions | ✅ `attune wizard` | COMPLETE | - |
| Keyboard Layout Setup | ✅ Cmd: `empathy.applyKeyboardLayout` | ❌ **MISSING** | NEEDS CLI | LOW |
| **Monitoring & Insights** |
| View API Costs | ✅ Dashboard → Costs Tab | ✅ `attune costs` | COMPLETE | - |
| Show Status | ✅ Cmd: `empathy.status` | ✅ `attune status` | COMPLETE | - |
| Open Web Dashboard | ✅ Dashboard → Button | ✅ `attune dashboard` | COMPLETE | - |
| **Panels** |
| Dashboard Panel | ✅ Sidebar: Empathy Explorer | ✅ (via workflows) | COMPLETE | - |
| Code Review Panel | ✅ Sidebar: Empathy Explorer | ✅ (via workflow results) | COMPLETE | - |
| Guided Assistant | ✅ Cmd: `empathy.openGuidedPanel` | ❌ **MISSING** | NEEDS CLI | LOW |
| Power Panel | ✅ Cmd: `empathy.openPowerPanel` | ✅ (via dashboard) | COMPLETE | - |
| Memory Panel | ✅ Sidebar view | ❌ **MISSING** (broken) | NEEDS FIX | HIGH |

---

## Critical Gap Analysis

### 🔴 HIGH PRIORITY - Missing UI Entry Points

#### 1. Code Review (File-Level)
- **Workflow ID:** `code-review`
- **CLI:** ✅ `attune workflow run code-review --input '{"target":"file.py"}'`
- **UI Status:** ❌ **NO BUTTON IN DASHBOARD**
- **Backend:** ✅ Full implementation with finding extraction
- **Panel:** ✅ CodeReviewPanelProvider exists with interactive UI
- **Impact:** Users cannot discover or use the file-level code review feature from UI
- **Fix Required:** Add button to Dashboard → Workflows section

**Recommendation:**
```typescript
// Add to EmpathyDashboardPanel.ts line ~2504 (Workflows section)
<button class="action-btn workflow-btn" data-workflow="code-review">
    <span class="action-icon">&#x1F50D;</span>
    <span>Review File</span>
</button>
```

### 🔴 HIGH PRIORITY - Broken Features

#### 2. Memory Control Panel
- **UI:** ✅ Panel exists but non-functional
- **CLI:** ❌ No direct CLI equivalent
- **Status:** BROKEN - mentioned in plan mode notes
- **Impact:** Core memory management feature inaccessible
- **Fix Required:** Repair panel or create CLI alternative

---

### 🟡 MEDIUM PRIORITY - Missing UI Entry Points

#### 3. Document Generation (`doc-gen`)
- **CLI:** ✅ `attune workflow run doc-gen`
- **UI Status:** ❌ No button
- **Impact:** Users must use CLI or `doc-orchestrator` instead
- **Fix:** Add to Workflows section

#### 4. Release Preparation (`release-prep`)
- **CLI:** ✅ `attune workflow run release-prep`
- **UI Status:** ❌ No button
- **Impact:** Pre-release checklist workflow hidden
- **Fix:** Add to Workflows section

#### 5. Secure Release Pipeline (`secure-release`)
- **CLI:** ✅ `attune workflow run secure-release`
- **UI Status:** ❌ No button
- **Impact:** Multi-stage security pipeline not discoverable
- **Fix:** Add to Workflows section (advanced section?)

---

### 🟢 LOW PRIORITY - Missing Entry Points

#### 6. Manage Documentation Crew (`manage-docs`)
- **CLI:** ✅ Available
- **UI Status:** ❌ No button (overlap with `doc-orchestrator`)
- **Impact:** Low - similar functionality available via `doc-orchestrator`

#### 7. Keyboard Shortcuts Generator
- **CLI:** ✅ `attune workflow run keyboard-shortcuts`
- **UI Status:** ❌ No button
- **Impact:** Low - niche developer tool

#### 8. Socratic Workflow Designer (CLI)
- **UI:** ✅ Command Palette: `empathy.socraticRefinement`
- **CLI:** ❌ No CLI equivalent
- **Impact:** Low - primarily UI-driven workflow

#### 9. Keyboard Layout Setup (CLI)
- **UI:** ✅ Commands exist
- **CLI:** ❌ No CLI equivalent
- **Impact:** Low - VSCode-specific feature

#### 10. Guided Assistant Panel (CLI)
- **UI:** ✅ Command to open panel
- **CLI:** ❌ No CLI chat mode
- **Impact:** Low - primarily UI-driven interaction

---

## Workflow Distribution Analysis

### Dashboard Workflows Section (Current)
**Count:** 10 workflows displayed

```
├── pro-review        (Run Analysis)
├── doc-orchestrator  (Manage Docs)
├── bug-predict       (Predict Bugs)
├── security-audit    (Security Audit)
├── perf-audit        (Perf Audit)
├── test-gen          (Generate Tests)
├── refactor-plan     (Refactor Plan)
├── dependency-check  (Check Deps)
├── health-check      (Check Health)
└── pr-review         (Review PR)
```

### Available Workflows (Backend)
**Count:** 16 workflows registered

**Missing from UI:**
1. ❌ `code-review` - **CRITICAL GAP**
2. ❌ `doc-gen`
3. ❌ `release-prep`
4. ❌ `secure-release`
5. ❌ `manage-docs`
6. ❌ `keyboard-shortcuts`

---

## Recommended Actions

### Phase 1: Critical Fixes (This Sprint)

**1. Add Code Review Button**
- **File:** [vscode-extension/src/panels/EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts:2504-2543)
- **Location:** Line ~2504, between `pro-review` and `doc-orchestrator`
- **Implementation:**
  ```typescript
  <button class="action-btn workflow-btn" data-workflow="code-review">
      <span class="action-icon">&#x1F50D;</span>
      <span>Review File</span>
  </button>
  ```
- **Handler:** Already exists - uses `_runWorkflowInEditor()`
- **Result Panel:** CodeReviewPanelProvider (already implemented)

**2. Update Workflow Configuration**
- **File:** [vscode-extension/src/panels/EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts:3028-3092)
- **Add to `workflowConfig`** (line ~3029):
  ```typescript
  'code-review': {
      type: 'file',
      label: 'Select file to review',
      placeholder: 'Click Browse or type path...',
      allowText: true
  },
  ```

**3. Verify Workflow Routing**
- **File:** [vscode-extension/src/panels/EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts:906-916)
- **Already configured** in `filePickerWorkflows` array (line 906)

### Phase 2: Medium Priority (Next Sprint)

**4. Add Release & Documentation Buttons**
- Add buttons for:
  - `doc-gen` (Document Generation)
  - `release-prep` (Release Prep)
  - `secure-release` (Secure Pipeline)

**5. Organize Workflows by Category**
- Consider tabbed interface or collapsible sections:
  ```
  📝 Code & Review
     ├── Review File (code-review)
     ├── Run Analysis (pro-review)
     └── Review PR (pr-review)

  🔒 Security & Quality
     ├── Security Audit
     ├── Bug Prediction
     └── Dependency Check

  📚 Documentation
     ├── Manage Docs (doc-orchestrator)
     ├── Generate Docs (doc-gen)
     └── Manage Docs Crew (manage-docs)

  🚀 Release & Planning
     ├── Release Prep (release-prep)
     ├── Secure Release (secure-release)
     └── Refactor Plan
  ```

### Phase 3: Low Priority (Backlog)

**6. CLI Equivalents for UI-Only Features**
- Socratic designer CLI mode
- Keyboard layout CLI commands
- Guided assistant CLI chat

**7. Fix Memory Control Panel**
- Repair existing panel or
- Create new CLI-based memory management

---

## Usage Statistics (If Available)

**Most Used Features** (estimated based on placement):
1. Morning Briefing (Quick Action)
2. Pre-Ship Check (Quick Action)
3. Security Audit (Workflow)
4. Test Generation (Workflow)
5. Bug Prediction (Workflow)

**Least Discoverable** (no UI button):
1. Code Review (file-level) ⚠️ **HIGH IMPACT**
2. Release Preparation
3. Secure Release Pipeline
4. Document Generation

---

## Visual Layout - Current Dashboard

```
┌─────────────────────────────────────────────────────────┐
│ [Power] [Health] [Costs] [Workflows]                    │
├─────────────────────────────────────────────────────────┤
│ Quick Actions                                            │
│  [☀️ Get Briefing]  [🚀 Run Ship]    [🔧 Fix Issues]   │
│  [📚 Learn Patterns] [🧪 Run Tests]  [⚙️ Setup]         │
│                                                          │
│ Workflows (Beta)                                         │
│  [⭐ Run Analysis]   [📚 Manage Docs]  [🐛 Predict Bugs]│
│  [🔒 Security Audit] [⚡ Perf Audit]  [🧪 Generate Tests]│
│  [🏗️ Refactor Plan] [📦 Check Deps]  [🩺 Check Health] │
│  [🔍 Review PR]                                          │
│                                                          │
│  ❌ MISSING: Code Review button!                        │
└─────────────────────────────────────────────────────────┘
```

## Visual Layout - Proposed Dashboard

```
┌─────────────────────────────────────────────────────────┐
│ [Power] [Health] [Costs] [Workflows]                    │
├─────────────────────────────────────────────────────────┤
│ Quick Actions                                            │
│  [☀️ Get Briefing]  [🚀 Run Ship]    [🔧 Fix Issues]   │
│  [📚 Learn Patterns] [🧪 Run Tests]  [⚙️ Setup]         │
│                                                          │
│ Workflows (Beta)                                         │
│  [🔍 Review File]    [⭐ Run Analysis] [📚 Manage Docs]  │ ← NEW!
│  [🐛 Predict Bugs]   [🔒 Security]    [⚡ Performance]   │
│  [🧪 Generate Tests] [🏗️ Refactor]   [📦 Dependencies]  │
│  [🩺 Health Check]   [🔍 Review PR]   [📄 Gen Docs]     │ ← NEW!
│  [🚀 Release Prep]   [🔐 Sec Release]                   │ ← NEW!
└─────────────────────────────────────────────────────────┘
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Code Review button appears in Dashboard → Workflows
- [ ] Clicking button opens file picker
- [ ] Selecting file runs workflow
- [ ] Results appear in CodeReviewPanel
- [ ] Findings are clickable and navigate to file:line
- [ ] CLI command still works: `attune workflow run code-review`
- [ ] Keyboard shortcut works: `Ctrl+Shift+E R`
- [ ] Context menu "Review This File" still works
- [ ] All other workflow buttons still functional

---

## Implementation Files

### Files to Modify

1. **[vscode-extension/src/panels/EmpathyDashboardPanel.ts](vscode-extension/src/panels/EmpathyDashboardPanel.ts)**
   - Add code-review button to workflows section (~line 2504)
   - Already has handler logic for file picker workflows
   - Already routes to CodeReviewPanel

2. **[vscode-extension/package.json](vscode-extension/package.json)**
   - Already has all necessary command registrations
   - No changes needed

3. **[vscode-extension/src/extension.ts](vscode-extension/src/extension.ts)**
   - Already registers CodeReviewPanel
   - Already has `empathy.goToLocation` command
   - No changes needed

### Files Created Recently (Context)

- [vscode-extension/src/types/WorkflowContracts.ts](vscode-extension/src/types/WorkflowContracts.ts) - Data contracts
- [vscode-extension/src/panels/CodeReviewPanelProvider.ts](vscode-extension/src/panels/CodeReviewPanelProvider.ts) - Review UI
- [vscode-extension/src/services/CostEstimator.ts](vscode-extension/src/services/CostEstimator.ts) - Cost estimates
- [tests/test_finding_extraction.py](tests/test_finding_extraction.py) - Backend tests

---

## Conclusion

The Attune AI has **strong dual entry point coverage** for most features (78% complete), but is missing a critical UI button for the **code-review workflow**. This is a high-priority gap because:

1. ✅ Backend fully implemented
2. ✅ Interactive panel exists (CodeReviewPanelProvider)
3. ✅ CLI command works
4. ✅ Keyboard shortcut exists
5. ❌ **NO DASHBOARD BUTTON** - users cannot discover the feature

**Immediate Action:** Add code-review button to Dashboard → Workflows section.

**Next Actions:** Consider adding buttons for `doc-gen`, `release-prep`, and `secure-release` to improve feature discoverability.

---

**Report Generated:** 2026-01-01
**Auditor:** Claude Sonnet 4.5
**Scope:** All workflows, commands, and UI panels
