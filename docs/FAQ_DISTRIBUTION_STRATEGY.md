---
description: FAQ Distribution Strategy: **Goal:** Make FAQ content available everywhere it's needed without duplication **Approach:** Single source of truth (docs/FAQ.md) wi
---

# FAQ Distribution Strategy

**Goal:** Make FAQ content available everywhere it's needed without duplication
**Approach:** Single source of truth (docs/FAQ.md) with references in multiple locations

---

## The Problem

We have great FAQ content that would be valuable in multiple places:
- Website FAQ page
- Book/documentation
- MkDocs
- README
- Marketing materials

**But we don't want:**
- Duplicate content (maintenance nightmare)
- Content drift (updates only in some places)
- Different answers to same question

---

## The Solution: Single Source of Truth

**Master FAQ:** `docs/FAQ.md` (comprehensive, 10,000+ words)

**Everywhere else:** Reference or excerpt sections, don't duplicate

---

## Distribution Map

### 1. MkDocs Documentation ✅ **PRIMARY**

**Location:** `docs/FAQ.md` (already there!)

**In mkdocs.yml:**
```yaml
nav:
  - Home: index.md
  - Getting Started: guides/getting-started.md
  - Guides:
      - Five Levels of Empathy: guides/five-levels-of-empathy.md
      - Teaching AI Your Standards: guides/teaching-ai-your-standards.md
  - FAQ: FAQ.md  # ← Add this
  - API Reference: api-reference/
```

**Advantage:** Full content, searchable, versioned with docs

---

### 2. Website FAQ Page

**Location:** `website/app/faq/page.tsx`

**Approach:** **Excerpt key sections**, link to full MkDocs FAQ

**What to include (short versions):**
- What is Attune AI? (3 sentences + link)
- What are the 5 Levels? (table + link)
- How do I get started? (code snippet + link)
- Does it work with [tool]? (yes/no + links)

**For each answer:**
```tsx
<Answer>
  <ShortAnswer>
    2-3 sentences covering the core point
  </ShortAnswer>
  <LearnMore href="https://docs.smartaimemory.com/FAQ#section">
    Full details in documentation →
  </LearnMore>
</Answer>
```

**Advantage:** Fast loading, mobile-friendly, comprehensive answers in docs

---

### 3. README.md

**Location:** `README.md`

**Approach:** **Link to FAQ**, show 2-3 most common questions

**Structure:**
```markdown
## Frequently Asked Questions

**Quick answers:**

- **What is this?** An open-source Python framework for AI memory and coordination
- **Quick start?** `pip install attune-ai && attune setup`
- **Does it work with [Copilot/Cursor/Claude]?** Yes! [See compatibility guide](docs/FAQ.md#tool-compatibility)

**More questions?** See the [comprehensive FAQ](docs/FAQ.md)
```

**Advantage:** Answers most common questions without leaving README

---

### 4. Book / Comprehensive Guides

**Location:** `docs/guides/*.md`

**Approach:** **Embed relevant FAQ sections inline**, cite FAQ for details

**Example in "Teaching AI Your Standards" guide:**

```markdown
## Common Questions

> **Q: Isn't this just fancy prompting?**
>
> No - the key difference is persistence. [See FAQ for detailed comparison](../FAQ.md#whats-the-difference-between-prompting-and-project-memory).

> **Q: How much time does this save?**
>
> We measured 80 hours/month. [See FAQ for breakdown by team size](../FAQ.md#what-results-can-i-expect).
```

**Advantage:** Questions answered in context, full details available without duplication

---

### 5. Marketing Materials

**Location:** `docs/marketing/*.md`

**Approach:** **Reference FAQ for objection handling**, don't duplicate

**In response templates:**
```markdown
## When Someone Asks "Isn't this overengineered?"

See: [FAQ - Isn't this overengineered?](../FAQ.md#isnt-this-overengineered)

Quick version for Reddit:
"Fair question! [2-3 sentence summary from FAQ]. Full breakdown: [link to FAQ]"
```

**Advantage:** Consistent answers, can update once and all marketing benefits

---

### 6. GitHub Issues/Discussions Templates

**Location:** `.github/ISSUE_TEMPLATE/` and `.github/DISCUSSION_TEMPLATE/`

**Approach:** **Link to relevant FAQ sections** before allowing submission

**In issue template:**
```markdown
## Before Opening an Issue

Please check if your question is answered in the FAQ:

**Common questions:**
- [Tool compatibility](https://docs.smartaimemory.com/FAQ#tool-compatibility)
- [Getting started](https://docs.smartaimemory.com/FAQ#getting-started)
- [Implementation](https://docs.smartaimemory.com/FAQ#implementation)

**Full FAQ:** https://docs.smartaimemory.com/FAQ
```

**Advantage:** Reduces duplicate issues, helps users find answers faster

---

## Content Organization

### Master FAQ Structure

The `docs/FAQ.md` has 7 sections:

1. **Getting Started** - What is it? Quick start? 5 Levels?
2. **Teaching AI Your Standards** - How to? Prompting vs memory? Examples?
3. **Tool Compatibility** - Copilot? Cursor? Claude? ChatGPT?
4. **Implementation** - Setup time? What to document? Keep updated?
5. **Results & ROI** - Expected results? How to measure?
6. **Common Concerns** - Overengineered? Replace code review? Hallucinations?
7. **Advanced Topics** - Multi-project? Language-specific? Data science?

### Reference Patterns

**For website/README (casual users):**
→ Sections 1-3 (Getting Started, Teaching AI, Tool Compatibility)

**For book/guides (learning users):**
→ Sections 2, 4, 5 (Teaching AI, Implementation, Results)

**For marketing (skeptical users):**
→ Sections 5, 6 (Results, Common Concerns)

**For support (power users):**
→ Sections 4, 7 (Implementation, Advanced Topics)

---

## Maintenance Workflow

### When FAQ Content Needs Updating

1. **Update master:** Edit `docs/FAQ.md`
2. **Check references:** Search for links to that section
3. **Update excerpts:** If website/README quotes it, update those too
4. **Commit together:** All changes in one commit

**Example commit:**
```bash
git add docs/FAQ.md website/app/faq/page.tsx README.md
git commit -m "docs: Update FAQ section on tool compatibility"
```

### When Adding New FAQ

1. **Add to master:** Write full answer in `docs/FAQ.md`
2. **Add to table of contents:** Update FAQ TOC
3. **Consider excerpts:** Does website need a short version?
4. **Add links:** Update guides that reference this topic

---

## Implementation Plan

### Phase 1: Core Infrastructure ✅

- [x] Create master FAQ (`docs/FAQ.md`)
- [ ] Add FAQ to mkdocs.yml
- [ ] Test MkDocs build
- [ ] Verify all internal links work

### Phase 2: Website Integration

- [ ] Design FAQ component for website
- [ ] Extract key sections (10-15 questions)
- [ ] Add "Learn more" links to full FAQ
- [ ] Test responsive design

### Phase 3: Documentation Integration

- [ ] Add FAQ references to key guides
- [ ] Update "Teaching AI Your Standards" with FAQ links
- [ ] Update "Five Levels" guide with FAQ links
- [ ] Add FAQ link to README

### Phase 4: Support Integration

- [ ] Update issue templates with FAQ links
- [ ] Update discussion templates with FAQ links
- [ ] Add FAQ to response templates
- [ ] Train on FAQ for common questions

---

## Quick Reference URLs

Once deployed to docs site:

**Full FAQ:** `https://docs.smartaimemory.com/FAQ`

**Section links:**
- Getting Started: `https://docs.smartaimemory.com/FAQ#getting-started`
- Teaching AI: `https://docs.smartaimemory.com/FAQ#teaching-ai-your-standards`
- Tool Compatibility: `https://docs.smartaimemory.com/FAQ#tool-compatibility`
- Implementation: `https://docs.smartaimemory.com/FAQ#implementation`
- Results: `https://docs.smartaimemory.com/FAQ#results--roi`
- Concerns: `https://docs.smartaimemory.com/FAQ#common-concerns`
- Advanced: `https://docs.smartaimemory.com/FAQ#advanced-topics`

---

## Benefits of This Approach

### ✅ Single Source of Truth
- One place to update
- No content drift
- Easy to maintain

### ✅ Context-Appropriate Depth
- Website: Short answers + links
- Docs: Full details
- README: Quick start questions only

### ✅ SEO-Friendly
- All FAQ content indexed together
- Internal links boost ranking
- Users find answers easily

### ✅ User-Friendly
- Quick answers for casual users
- Deep dives for power users
- Searchable in docs

### ✅ Maintainable
- Clear update process
- Easy to find references
- Version controlled

---

## Next Steps

1. **Add FAQ to mkdocs.yml** (5 min)
2. **Test MkDocs build** (2 min)
3. **Create website FAQ excerpt** (1 hour)
4. **Update README with FAQ links** (15 min)
5. **Add FAQ references to guides** (30 min)

**Total time:** ~2 hours
**Long-term savings:** Massive (no duplicate maintenance)

---

**Last Updated:** January 7, 2026
**Owner:** Patrick Roebuck
