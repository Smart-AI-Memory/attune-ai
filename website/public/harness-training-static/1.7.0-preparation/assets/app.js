"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const sectionHost = byId("lesson-sections");
  const navHost = byId("section-nav");
  const status = byId("lesson-status");
  const mobile = window.matchMedia("(max-width: 760px)");
  let lesson;
  let currentId;
  let visited = new Set();
  let notes = Object.create(null);
  let storageAvailable = true;
  let presenterVisible = false;
  let copyPending = false;
  const articles = new Map();
  const links = new Map();

  function announce(message) {
    status.textContent = "";
    window.setTimeout(() => { status.textContent = message; }, 20);
  }

  function storageNotice(message) {
    byId("storage-notice").textContent = message;
    byId("storage-notice").hidden = false;
  }

  function storageFailure() {
    storageAvailable = false;
    storageNotice("Browser storage is unavailable. Progress and practice notes will last for this page session only.");
  }

  function readProgress() {
    let saved;
    try {
      const raw = window.localStorage.getItem(lesson.storageKey);
      if (!raw) return;
      saved = JSON.parse(raw);
    } catch (error) {
      if (error instanceof SyntaxError) {
        storageNotice("Saved lesson progress could not be read. This lesson is starting fresh.");
      } else {
        storageFailure();
      }
      return;
    }
    if (!saved || typeof saved !== "object") return;
    const validIds = new Set(lesson.sections.map((section) => section.id));
    if (validIds.has(saved.currentId)) currentId = saved.currentId;
    if (Array.isArray(saved.visited)) visited = new Set(saved.visited.filter((id) => validIds.has(id)));
    if (saved.notes && typeof saved.notes === "object" && !Array.isArray(saved.notes)) {
      for (const [key, value] of Object.entries(saved.notes)) {
        if (typeof value === "string") notes[key] = value;
      }
    }
  }

  function saveProgress() {
    if (!storageAvailable) return;
    try {
      window.localStorage.setItem(lesson.storageKey, JSON.stringify({ currentId, visited: [...visited], notes }));
    } catch {
      storageFailure();
    }
  }

  function closeNavigation() {
    byId("navigation-panel").classList.remove("is-open");
    byId("nav-toggle").setAttribute("aria-expanded", "false");
    byId("nav-toggle").textContent = "Show lesson navigation";
  }

  function activateSection(id, { focus = false, persist = true } = {}) {
    if (!articles.has(id)) id = lesson.sections[0].id;
    currentId = id;
    visited.add(id);
    const index = lesson.sections.findIndex((section) => section.id === id);
    for (const [sectionId, article] of articles) article.hidden = sectionId !== id;
    for (const [sectionId, link] of links) {
      if (sectionId === id) link.setAttribute("aria-current", "step");
      else link.removeAttribute("aria-current");
      link.querySelector(".visit-indicator").textContent = visited.has(sectionId) ? "●" : "";
      link.querySelector(".visit-indicator").setAttribute("aria-label", visited.has(sectionId) ? "Visited" : "");
      link.querySelector(".visit-indicator").setAttribute("aria-hidden", String(!visited.has(sectionId)));
    }
    byId("previous-section").disabled = index === 0;
    byId("next-section").disabled = index === lesson.sections.length - 1;
    byId("section-position").textContent = `Section ${index + 1} of ${lesson.sections.length}`;
    byId("lesson-progress").value = visited.size;
    byId("progress-label").textContent = `${visited.size} of ${lesson.sections.length} sections visited`;
    if (persist) saveProgress();
    if (focus) articles.get(id).querySelector("h2").focus();
  }

  function navigateTo(id) {
    if (!articles.has(id)) return;
    if (window.location.hash === `#${id}`) activateSection(id, { focus: true });
    else window.location.hash = id;
    if (mobile.matches) closeNavigation();
  }

  function buildCopy(copy, sectionIndex, copyIndex) {
    const group = document.createElement("section");
    group.className = "copy-block";
    const heading = document.createElement("div");
    heading.className = "copy-heading";
    const title = document.createElement("h3");
    title.id = `copy-title-${sectionIndex}-${copyIndex}`;
    title.textContent = copy.label;
    group.setAttribute("aria-labelledby", title.id);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `Copy ${copy.label}`;
    const manualButton = document.createElement("button");
    manualButton.type = "button";
    manualButton.textContent = "Select text";
    manualButton.setAttribute("aria-label", `Select text for ${copy.label}`);
    const actions = document.createElement("div");
    actions.className = "copy-actions";
    actions.append(button, manualButton);
    heading.append(title, actions);
    const pre = document.createElement("pre");
    const code = document.createElement("code");
    code.textContent = copy.text;
    pre.append(code);
    const fallback = document.createElement("div");
    fallback.className = "manual-copy";
    fallback.hidden = true;
    const hint = document.createElement("p");
    hint.id = `copy-hint-${sectionIndex}-${copyIndex}`;
    hint.textContent = "Use Select text to select the exact text below, then use your keyboard’s copy shortcut.";
    const label = document.createElement("label");
    const field = document.createElement("textarea");
    field.id = `manual-copy-${sectionIndex}-${copyIndex}`;
    field.readOnly = true;
    field.rows = Math.min(12, Math.max(4, copy.text.split("\n").length + 1));
    field.value = copy.text;
    field.setAttribute("aria-describedby", hint.id);
    label.htmlFor = field.id;
    label.textContent = `${copy.label} — manual copy`;
    fallback.append(hint, label, field);
    const feedback = document.createElement("p");
    feedback.className = "copy-status";
    feedback.setAttribute("role", "status");
    feedback.setAttribute("aria-live", "polite");
    feedback.setAttribute("aria-atomic", "true");
    group.append(heading, pre, feedback, fallback);
    function selectManually() {
      fallback.hidden = false;
      field.value = copy.text;
      field.focus();
      field.select();
      field.setSelectionRange(0, field.value.length);
      feedback.textContent = "Text selected. Press Command+C on Mac or Ctrl+C on Windows/Linux, then paste where needed.";
    }
    manualButton.addEventListener("click", () => {
      if (!copyPending) selectManually();
    });
    button.addEventListener("click", async () => {
      if (copyPending) return;
      if (!navigator.clipboard || typeof navigator.clipboard.write !== "function" || typeof ClipboardItem !== "function") {
        selectManually();
        return;
      }
      copyPending = true;
      const controls = [...sectionHost.querySelectorAll(".copy-actions button")];
      for (const control of controls) control.setAttribute("aria-disabled", "true");
      button.setAttribute("aria-busy", "true");
      feedback.textContent = "Copying… If it stalls, reload this page. Your saved notes will be kept.";
      try {
        // Start the write during the click gesture; do not await before this call.
        await navigator.clipboard.write([
          new ClipboardItem({ "text/plain": new Blob([copy.text], { type: "text/plain" }) })
        ]);
        fallback.hidden = true;
        feedback.textContent = `Copied ${copy.label}. Paste it where needed.`;
      } catch {
        fallback.hidden = false;
        feedback.textContent = "Copy was unavailable. Choose Select text, then use your keyboard’s copy shortcut.";
      } finally {
        copyPending = false;
        button.removeAttribute("aria-busy");
        for (const control of controls) control.removeAttribute("aria-disabled");
      }
    });
    return group;
  }

  function buildCheck(check, sectionIndex) {
    const group = document.createElement("section");
    group.className = "knowledge-check";
    const title = document.createElement("h3");
    title.textContent = "Check your understanding";
    const question = document.createElement("p");
    question.className = "check-question";
    question.id = `check-question-${sectionIndex}`;
    question.textContent = check.question;
    const options = document.createElement("div");
    options.className = "check-options";
    options.setAttribute("role", "group");
    options.setAttribute("aria-labelledby", question.id);
    const feedback = document.createElement("p");
    feedback.className = "check-feedback";
    feedback.id = `check-feedback-${sectionIndex}`;
    feedback.setAttribute("role", "status");
    feedback.setAttribute("aria-live", "polite");
    feedback.setAttribute("aria-atomic", "true");
    feedback.textContent = "Choose an answer to see feedback.";
    for (const option of check.options) {
      const button = document.createElement("button");
      button.className = "check-option";
      button.type = "button";
      button.textContent = option.text;
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-describedby", feedback.id);
      button.addEventListener("click", () => {
        for (const other of options.children) {
          other.setAttribute("aria-pressed", "false");
          delete other.dataset.result;
        }
        button.setAttribute("aria-pressed", "true");
        button.dataset.result = option.correct ? "correct" : "incorrect";
        feedback.textContent = `${option.correct ? "Correct." : "Not quite."} ${option.feedback}`;
      });
      options.append(button);
    }
    group.append(title, question, options, feedback);
    return group;
  }

  function renderSection(section, index) {
    const article = document.createElement("article");
    article.className = "lesson-section";
    article.id = section.id;
    article.hidden = true;
    const phase = document.createElement("p");
    phase.className = "phase";
    phase.textContent = section.phase;
    const title = document.createElement("h2");
    title.id = `${section.id}-title`;
    title.tabIndex = -1;
    title.textContent = section.title;
    article.setAttribute("aria-labelledby", title.id);
    const intro = document.createElement("p");
    intro.className = "section-intro";
    intro.textContent = section.intro;
    const content = document.createElement("div");
    content.className = "lesson-body";
    content.innerHTML = section.html;
    for (const [fieldIndex, field] of [...content.querySelectorAll("textarea[data-save]")].entries()) {
      const key = field.dataset.save || `${section.id}-note-${fieldIndex + 1}`;
      if (Object.prototype.hasOwnProperty.call(notes, key)) field.value = notes[key];
      field.addEventListener("input", () => {
        notes[key] = field.value;
        saveProgress();
      });
    }
    article.append(phase, title, intro, content);
    (section.copies || []).forEach((copy, copyIndex) => {
      const destination = copy.slot
        ? [...content.querySelectorAll("[data-copy-slot]")].find((node) => node.dataset.copySlot === copy.slot)
        : article;
      if (!destination) throw new Error("Copy destination missing");
      destination.append(buildCopy(copy, index, copyIndex));
    });
    if (section.check) article.append(buildCheck(section.check, index));
    const presenter = document.createElement("details");
    presenter.className = "presenter-notes";
    presenter.hidden = true;
    const summary = document.createElement("summary");
    summary.textContent = "Presenter notes";
    const list = document.createElement("ul");
    for (const note of section.presenterNotes || []) {
      const item = document.createElement("li");
      item.textContent = note;
      list.append(item);
    }
    presenter.append(summary, list);
    article.append(presenter);
    sectionHost.append(article);
    articles.set(section.id, article);

    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `#${section.id}`;
    const number = document.createElement("span");
    number.className = "nav-number";
    number.setAttribute("aria-hidden", "true");
    number.textContent = String(index + 1).padStart(2, "0");
    const label = document.createElement("span");
    label.textContent = section.navTitle;
    const indicator = document.createElement("span");
    indicator.className = "visit-indicator";
    indicator.setAttribute("role", "img");
    link.append(number, label, indicator);
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigateTo(section.id);
    });
    item.append(link);
    navHost.append(item);
    links.set(section.id, link);
  }

  function validateLesson(data) {
    if (!data || typeof data.title !== "string" || typeof data.storageKey !== "string" || !data.storageKey || !Array.isArray(data.sections) || !data.sections.length) throw new Error("Invalid lesson");
    const ids = new Set();
    for (const section of data.sections) {
      if (!section || typeof section.id !== "string" || !/^section-\d+$/.test(section.id) || ids.has(section.id)) throw new Error("Invalid section");
      ids.add(section.id);
      for (const key of ["navTitle", "phase", "title", "intro", "html"]) {
        if (typeof section[key] !== "string") throw new Error("Invalid section content");
      }
      if (section.copies && (!Array.isArray(section.copies) || section.copies.some((copy) => typeof copy.label !== "string" || typeof copy.text !== "string"))) throw new Error("Invalid copy content");
      if (section.presenterNotes && (!Array.isArray(section.presenterNotes) || section.presenterNotes.some((note) => typeof note !== "string"))) throw new Error("Invalid notes");
      if (section.check && (typeof section.check.question !== "string" || !Array.isArray(section.check.options) || section.check.options.some((option) => typeof option.text !== "string" || typeof option.feedback !== "string" || typeof option.correct !== "boolean"))) throw new Error("Invalid check");
    }
    return data;
  }

  function bindControls() {
    byId("previous-section").addEventListener("click", () => {
      const index = lesson.sections.findIndex((section) => section.id === currentId);
      if (index > 0) navigateTo(lesson.sections[index - 1].id);
    });
    byId("next-section").addEventListener("click", () => {
      const index = lesson.sections.findIndex((section) => section.id === currentId);
      if (index < lesson.sections.length - 1) navigateTo(lesson.sections[index + 1].id);
    });
    byId("presenter-toggle").addEventListener("click", () => {
      presenterVisible = !presenterVisible;
      byId("presenter-toggle").setAttribute("aria-pressed", String(presenterVisible));
      for (const presenter of sectionHost.querySelectorAll(".presenter-notes")) {
        presenter.hidden = !presenterVisible;
        presenter.open = presenterVisible;
      }
      announce(presenterVisible ? "Presenter notes are visible and will be included when printing." : "Presenter notes are hidden and will be omitted when printing.");
    });
    byId("print-lesson").addEventListener("click", () => window.print());
    byId("reset-progress").addEventListener("click", () => {
      if (!window.confirm("Reset progress and clear all practice notes for this lesson in this browser?")) return;
      visited = new Set();
      notes = Object.create(null);
      for (const field of sectionHost.querySelectorAll("textarea[data-save]")) field.value = "";
      try { window.localStorage.removeItem(lesson.storageKey); } catch { storageFailure(); }
      const first = lesson.sections[0].id;
      window.history.replaceState(null, "", `#${first}`);
      activateSection(first, { focus: true, persist: false });
      announce("Lesson progress and practice notes have been reset. You are at the first section.");
    });
    byId("nav-toggle").addEventListener("click", () => {
      const open = !byId("navigation-panel").classList.contains("is-open");
      byId("navigation-panel").classList.toggle("is-open", open);
      byId("nav-toggle").setAttribute("aria-expanded", String(open));
      byId("nav-toggle").textContent = open ? "Hide lesson navigation" : "Show lesson navigation";
    });
    mobile.addEventListener("change", closeNavigation);
    window.addEventListener("hashchange", () => {
      const id = window.location.hash.slice(1);
      if (articles.has(id)) activateSection(id, { focus: true });
      else {
        window.history.replaceState(null, "", `#${currentId}`);
        announce("That lesson section is unavailable. The current section remains open.");
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target;
      if (target instanceof Element && (target.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])") || target.isContentEditable)) return;
      const index = lesson.sections.findIndex((section) => section.id === currentId);
      const destinations = { ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: lesson.sections.length - 1 };
      if (!Object.prototype.hasOwnProperty.call(destinations, event.key)) return;
      event.preventDefault();
      const destination = destinations[event.key];
      if (destination >= 0 && destination < lesson.sections.length) navigateTo(lesson.sections[destination].id);
    });
  }

  async function start() {
    byId("reload-lesson").addEventListener("click", () => window.location.reload());
    try {
      const response = await fetch("lesson.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Lesson unavailable");
      lesson = validateLesson(await response.json());
      document.title = `${lesson.title} · Attune Harness`;
      byId("lesson-title").textContent = lesson.title;
      byId("sidebar-title").textContent = lesson.title;
      byId("lesson-subtitle").textContent = lesson.subtitle || "";
      byId("course-label").textContent = lesson.courseLabel || "Local lesson";
      byId("revision-label").textContent = lesson.revisionLabel || "Local unpublished draft";
      byId("lesson-progress").max = lesson.sections.length;
      readProgress();
      lesson.sections.forEach(renderSection);
      if (Array.isArray(lesson.coursePath) && lesson.coursePath.length) {
        lesson.coursePath.forEach((text, index) => {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.textContent = text;
          link.href = lesson.courseRoutes[index];
          if (index + 1 === lesson.coursePosition) {
            item.className = "current-course";
            link.setAttribute("aria-current", "page");
            link.textContent += " (this tutorial)";
          }
          item.append(link);
          byId("course-path-list").append(item);
        });
        byId("course-path").hidden = false;
      }
      bindControls();
      const hashId = window.location.hash.slice(1);
      const initialId = articles.has(hashId) ? hashId : currentId || lesson.sections[0].id;
      window.history.replaceState(null, "", `#${initialId}`);
      activateSection(initialId);
      byId("loading-message").hidden = true;
      byId("section-pagination").hidden = false;
      for (const id of ["nav-toggle", "presenter-toggle", "print-lesson", "reset-progress"]) byId(id).disabled = false;
    } catch {
      byId("loading-message").hidden = true;
      byId("load-error").hidden = false;
      byId("lesson-subtitle").textContent = "The lesson content is unavailable.";
      byId("progress-label").textContent = "Lesson unavailable";
      sectionHost.replaceChildren();
      navHost.replaceChildren();
    }
  }

  start();
})();
