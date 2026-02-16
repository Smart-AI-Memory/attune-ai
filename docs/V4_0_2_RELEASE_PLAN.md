---
description: v4.0.2 Release Plan - Stabilize & Iterate: **Release Date:** January 26, 2026 (2 weeks from now) **Strategy:** Option 1 - Stabilize & Iterate **Status:** 🟡 Plan
---

# v4.0.2 Release Plan - Stabilize & Iterate

**Release Date:** January 26, 2026 (2 weeks from now)
**Strategy:** Option 1 - Stabilize & Iterate
**Status:** 🟡 Planning

---

## Goals

1. ✅ **Restore user trust** after v4.0.0 rollback
2. ✅ **Zero breaking changes** - 100% backward compatible with v4.0.1
3. ✅ **Small, proven improvements** - no risky experiments
4. ✅ **Solid foundation** for future v4.0.x releases

---

## Week 1: Assessment & Bug Fixes (Jan 13-17)

### Day 1-2: Experimental Branch Assessment ⏰ TIME-BOXED: 2 days max

**Task:** Determine if any CrewAI workflows from v4.0.0 can be salvaged

**Test Plan:**
```bash
# Switch to experimental branch
git checkout experimental/v4.0-meta-orchestration

# Test individual crews (WITHOUT meta-orchestration)
# 1. Does HealthCheckCrew work standalone?
python -m pytest tests/ -k health_check_crew -v

# 2. Does ReleasePreparationCrew work standalone?
python -m pytest tests/ -k release_prep_crew -v

# 3. Does TestCoverageBoostCrew work standalone via CLI?
attune workflow run test-coverage-boost --input '{"path":"./src"}'
```

**Decision Criteria:**
- ✅ **YES to cherry-pick:** Tests pass + CLI works + produces useful output
- ❌ **NO - skip it:** Tests fail OR CLI broken OR output is mock data

**Outcome:** Document findings in `experimental_assessment.md`

---

### Day 3-4: Bug Fixes & Quality Improvements

**Priority 1: Critical Bugs** (if any reported on GitHub)
- Check GitHub issues for anything marked "critical" or "blocker"
- Fix any data loss bugs, crashes, or security issues

**Priority 2: Known Issues from v3.11.0**
- Review CHANGELOG for any "Known Issues" or "TODO" items
- Pick 1-2 small, safe fixes

**Examples of Safe Fixes:**
- Better error messages
- Documentation improvements
- Type hint additions
- Test coverage improvements
- Performance micro-optimizations (if low-risk)

---

### Day 5: Testing & Documentation

**Testing Checklist:**
- [ ] All existing tests pass: `pytest tests/ -v`
- [ ] No regressions in performance: `pytest benchmarks/ --benchmark-only`
- [ ] Manual smoke test: `attune morning`, `attune workflow run health-check`
- [ ] VS Code extension still works (basic functionality only)

**Documentation Updates:**
- [ ] Update CHANGELOG.md with v4.0.2 changes
- [ ] Update README.md if any features added
- [ ] Review docs/ folder for outdated info

---

## Week 2: Polish & Release (Jan 20-24)

### Day 1-2: Cherry-Pick from Experimental (Optional)

**Only do this if Week 1 assessment found salvageable code**

**Safe Cherry-Pick Process:**
```bash
# 1. Identify working commit(s) from experimental branch
git log experimental/v4.0-meta-orchestration --oneline

# 2. Cherry-pick ONLY commits that:
#    - Add a single, self-contained feature
#    - Have passing tests
#    - Don't depend on meta-orchestration

# 3. Example: If HealthCheckCrew works standalone
git cherry-pick <commit-hash-for-health-check-crew>

# 4. Test immediately after cherry-pick
pytest tests/ -v
attune workflow run health-check --input '{"path":"."}'
```

**If Nothing Works:** Skip this entirely. v4.0.2 will be bug fixes only. That's fine!

---

### Day 3: Pre-Release Testing

**Full Test Suite:**
```bash
# 1. Run all tests
pytest tests/ --cov=src --cov-report=term-missing

# 2. Run benchmarks
pytest benchmarks/ --benchmark-only

# 3. Test on fresh Python environment
python -m venv /tmp/test_venv
source /tmp/test_venv/bin/activate
pip install .
attune --help
attune workflow list
deactivate
```

**Manual Testing:**
- [ ] Test 3-5 key workflows via CLI
- [ ] Test VS Code extension (basic open/close)
- [ ] Test on macOS, Linux, Windows (if possible)

---

### Day 4: Release Day

**Release Checklist:**

1. **Update Version**
   ```bash
   # Update pyproject.toml
   version = "4.0.2"

   # Update CHANGELOG.md
   ## [4.0.2] - 2026-01-26
   ```

2. **Commit & Tag**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Release v4.0.2: [Brief description]"
   git tag v4.0.2
   git push origin main --tags
   ```

3. **Build & Publish**
   ```bash
   rm -rf dist/ build/ *.egg-info
   python -m build
   python -m twine upload dist/*
   ```

4. **Verify on PyPI**
   - Check https://pypi.org/project/attune-ai/4.0.2/
   - Test install: `pip install attune-ai==4.0.2`

5. **Announce**
   - GitHub Release with CHANGELOG excerpt
   - Update README.md badge if needed

---

## What's NOT in v4.0.2

❌ **No Meta-Orchestration** - Too complex, postponed to v4.1+
❌ **No Major VS Code Changes** - Extension works as-is from v3.11.0
❌ **No Breaking Changes** - 100% compatible with v4.0.1
❌ **No Risky Experiments** - Only proven, tested code

---

## Success Criteria

**v4.0.2 is successful if:**
1. ✅ Zero bug reports in first 48 hours after release
2. ✅ Users can upgrade without issues: `pip install --upgrade attune-ai`
3. ✅ All workflows from v4.0.1 still work
4. ✅ PyPI listing shows v4.0.2 as latest (not v4.0.0)
5. ✅ GitHub issues trend down (not up)

**Metrics to Track:**
- PyPI download count (expect stable or slight increase)
- GitHub stars/forks (expect slow, steady growth)
- Issue close rate (target: >50% of new issues closed within 7 days)

---

## What Comes After v4.0.2?

**v4.0.3 (4-6 weeks later):** Pick ONE focused improvement:
- Option A: Better documentation/onboarding
- Option B: One new workflow (if valuable use case emerges)
- Option C: Performance improvement (Phase 3 optimizations)
- Option D: Better error messages/logging

**v4.1.0 (3-4 months later):** Revisit multi-agent workflows
- By then, we'll have learned from v4.0.0 mistakes
- Start with ONE working CrewAI workflow
- CLI-first, VS Code integration later
- Extensive testing before release

---

## Risk Mitigation

**If v4.0.2 Release Gets Blocked:**
- Don't force it - delay by 1 week
- Better to release v4.0.2 late than release broken code

**If Cherry-Picks Fail:**
- Skip them - release v4.0.2 with just bug fixes
- Document findings for future reference

**If Tests Fail:**
- Fix tests OR remove problematic code
- Never release with failing tests

---

## Owner & Timeline

**Owner:** Patrick Roebuck
**Start Date:** January 13, 2026
**Release Date:** January 26, 2026 (target)
**Slack:** Can delay to Feb 2 if needed

**Review Checkpoints:**
- End of Week 1: Assessment complete, decision on cherry-picks
- Day 3 of Week 2: Pre-release testing done, ready to release
- Release Day: v4.0.2 live on PyPI

---

## Notes

- This is a **low-risk, high-confidence** release
- Focus on **stability over features**
- Build **user trust** after v4.0.0 incident
- Set up **sustainable release cadence** (every 4-6 weeks)

**Remember:** A boring, stable release is better than an exciting, broken release.
