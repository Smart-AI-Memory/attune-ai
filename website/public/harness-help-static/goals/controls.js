// Ported from attune-ai 569b15d2d1a49c6c5d465032ec365c0e0527e59a; local worksheet only.
const choiceIds = ['p1', 'p2'];
const labels = {
    include: 'include the clarification as proposed wording',
    keep: 'keep the original wording',
    defer: 'leave the wording decision open',
};
/** Bind only local guide controls; no model, acceptance or network operations. */
export function mountGuide(root, data) {
    const controller = new AbortController();
    const { signal } = controller;
    function element(id) {
        const node = root.querySelector(`#${id}`);
        if (!node)
            throw new Error(`Missing guide element: ${id}`);
        return node;
    }
    const choices = element('wording-choices');
    const output = element('spec-output');
    const outputDetails = element('output-details');
    const draftStatus = element('draft-status');
    const index = root.querySelector('.goal-index');
    if (index)
        index.open = window.matchMedia('(min-width: 901px)').matches;
    function renderDraft(announce = false) {
        let spec = data.initial.replace('# Local activity reporting app — initial spec v0.1', '# Local activity reporting app — review draft');
        spec = spec.replace('Status: host-authored initial draft for review. No roundtable has reviewed it; no implementation is approved.', 'Status: unapproved illustrative review draft. No successful live consultation is demonstrated. The optional wording is an example for human review. This worksheet records no Harness acceptance or implementation authority.');
        const selected = choiceIds.map(id => {
            const value = choices.querySelector(`input[name="${id}"]:checked`)?.value;
            const choice = value === 'include' || value === 'keep' ? value : 'defer';
            if (choice === 'include')
                spec = spec.replace(data.proposals[id].before, data.proposals[id].after);
            return { id, choice };
        });
        spec += '\n## Wording choices for human review\n\n';
        for (const { id, choice } of selected)
            spec += `- ${id.toUpperCase()}: ${labels[choice]}.\n`;
        spec += '\nThese worksheet choices are proposed wording, not approval of the spec. Review the evidence and unresolved decisions in the real project before accepting work. No consultation or implementation is started by this page.\n';
        output.value = spec;
        element('decision-summary').textContent = selected.map(({ id, choice }) => `${id.toUpperCase()}: ${labels[choice]}.`).join(' ');
        element('choice-progress').textContent = `${selected.filter(x => x.choice !== 'defer').length} of 2 wording choices made. The draft remains unapproved.`;
        if (announce)
            draftStatus.textContent = 'Review draft prepared below. No approval was recorded and no model was called.';
    }
    function openAncestors(target) {
        let detail = target?.closest('details');
        while (detail) {
            detail.open = true;
            detail = detail.parentElement?.closest('details') ?? null;
        }
    }
    function openHash() {
        let id;
        try {
            id = decodeURIComponent(window.location.hash.slice(1));
        }
        catch {
            return;
        }
        if (!id)
            return;
        const target = document.getElementById(id);
        if (target && root.contains(target))
            openAncestors(target);
    }
    async function copy(button) {
        const target = document.getElementById(button.dataset.copy ?? '');
        const status = document.getElementById(button.dataset.status ?? '');
        if (!target || !status || !root.contains(target) || !root.contains(status))
            return;
        const text = target instanceof HTMLTextAreaElement ? target.value : target.textContent ?? '';
        try {
            await navigator.clipboard.writeText(text);
            status.textContent = 'Copied. Paste it into your assistant or a document.';
        }
        catch {
            if (target instanceof HTMLTextAreaElement) {
                outputDetails.open = true;
                target.focus();
                target.select();
            }
            else {
                const range = document.createRange();
                range.selectNodeContents(target);
                const selection = window.getSelection();
                selection?.removeAllRanges();
                selection?.addRange(range);
                target.focus();
            }
            status.textContent = 'Text selected. Press Command+C on Mac or Control+C to copy.';
        }
    }
    root.addEventListener('click', event => {
        if (!(event.target instanceof Element))
            return;
        const button = event.target.closest('button');
        if (button?.dataset.copy) {
            void copy(button);
            return;
        }
        if (button?.id === 'open-topics' || button?.id === 'close-topics') {
            const open = button.id === 'open-topics';
            const goals = root.querySelectorAll('.goal-item');
            goals.forEach(goal => { goal.open = open; });
            element('topic-status').textContent = `All ${goals.length} topics are ${open ? 'open' : 'closed'}.`;
        }
        else if (button?.id === 'prepare-draft') {
            renderDraft(true);
            outputDetails.open = true;
            element('result-heading').focus();
        }
        else if (button?.id === 'reset-choices') {
            for (const id of choiceIds) {
                const input = choices.querySelector(`input[name="${id}"][value="defer"]`);
                if (input)
                    input.checked = true;
            }
            renderDraft();
            draftStatus.textContent = 'Wording choices reset. Both decisions are open.';
        }
        else if (button?.id === 'download-draft') {
            const blob = new Blob([output.value], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'activity-app-spec-review-draft.md';
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
            draftStatus.textContent = 'Review draft download requested. It remains unapproved.';
        }
        const anchor = event.target.closest('a[href^="#"]');
        if (anchor)
            openAncestors(document.getElementById(anchor.hash.slice(1)));
    }, { signal });
    choices.addEventListener('change', () => {
        renderDraft();
        draftStatus.textContent = 'Draft updated. Review it before making any acceptance decision.';
    }, { signal });
    root.addEventListener('submit', event => event.preventDefault(), { signal });
    window.addEventListener('hashchange', openHash, { signal });
    renderDraft();
    openHash();
    return () => controller.abort();
}

const root = document.querySelector(".goal-guide");
const data = document.getElementById("goal-guide-data");
if (root && data) mountGuide(root, JSON.parse(data.textContent));
