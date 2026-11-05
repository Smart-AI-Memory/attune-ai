// Follow the goals guide's clipboard and manual-selection fallback pattern.
for (const target of document.querySelectorAll('.help-prose pre > code, .help-prose [data-copy-prompt]')) {
    const prompt = target.hasAttribute('data-copy-prompt');
    const block = prompt ? target : target.parentElement;
    const controls = document.createElement('div');
    controls.className = 'help-code-controls';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Copy';
    button.setAttribute('aria-label', prompt ? 'Copy starter prompt' : 'Copy code block');
    const status = document.createElement('span');
    status.className = 'help-code-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    controls.append(button, status);
    block.before(controls);
    block.tabIndex = 0;
    let reset;
    let copying = false;
    button.addEventListener('click', async () => {
        if (copying) return;
        copying = true;
        clearTimeout(reset);
        button.setAttribute('aria-busy', 'true');
        button.textContent = 'Copying…';
        status.textContent = '';
        try {
            await navigator.clipboard.writeText(target.textContent);
            button.textContent = 'Copied';
            status.textContent = prompt ? 'Prompt copied to clipboard.' : 'Code copied to clipboard.';
            reset = setTimeout(() => { button.textContent = 'Copy'; }, 2000);
        } catch {
            button.textContent = 'Copy';
            block.focus();
            const range = document.createRange();
            range.selectNodeContents(target);
            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(range);
            status.textContent = 'Text selected. Press Command+C on Mac or Control+C to copy.';
        } finally {
            copying = false;
            button.removeAttribute('aria-busy');
        }
    });
}
