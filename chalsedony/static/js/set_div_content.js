
/*
If using Raw KaTeX, use this script to update div content and render math
If using arithmatex, the  arithmatex_auto-render.js script will handle this
as it extenda the example from <https://facelessuser.github.io/pymdown-extensions/extensions/arithmatex/#options>
to also update on mutations
*/

function set_div_content_and_load_katex(div_class, content) {
  // First ensure KaTeX is loaded
  if (typeof renderMathInElement === "undefined") {
    /*
      If KaTeX is not loaded, The content hasn't been set,
      So don't worry for now
      */
  } else {
    const container = document.querySelector(`div.${div_class}`);
    // Save open/closed state of all details elements using their summary text as key
    const detailsStates = new Map();
    container.querySelectorAll("details").forEach((details) => {
      const summary = details.querySelector("summary");
      if (summary) {
        detailsStates.set(summary.textContent.trim(), details.open);
      }
    });

    // Update content
    container.innerHTML = content;

    // Restore open/closed state using summary text as key
    container.querySelectorAll("details").forEach((newDetails) => {
      const summary = newDetails.querySelector("summary");
      if (summary) {
        const summaryText = summary.textContent.trim();
        if (detailsStates.has(summaryText)) {
          newDetails.open = detailsStates.get(summaryText);
        }
      }
    });

    // Render math
    renderMathInElement(container, {
      delimiters: [
        { left: "$$", right: "$$", display: true }, // Block math
        { left: "$", right: "$", display: false }, // Inline math
        { left: "\\\\(", right: "\\\\)", display: false }, // Inline math
        { left: "\\\\[", right: "\\\\]", display: true }, // Block math
      ],
      throwOnError: true,
      strict: true,
    });
  }
}

function set_div_content(div_class, content) {
  const container = document.querySelector(`div.${div_class}`);
  // Save open/closed state of all details elements using their summary text as key
  const detailsStates = new Map();
  container.querySelectorAll("details").forEach((details) => {
    const summary = details.querySelector("summary");
    if (summary) {
      detailsStates.set(summary.textContent.trim(), details.open);
    }
  });

  // Update content
  container.innerHTML = content;

  // Restore open/closed state using summary text as key
  container.querySelectorAll("details").forEach((newDetails) => {
    const summary = newDetails.querySelector("summary");
    if (summary) {
      const summaryText = summary.textContent.trim();
      if (detailsStates.has(summaryText)) {
        newDetails.open = detailsStates.get(summaryText);
      }
    }
  });
}

function set_div_content_and_eval(div_class, content) {
  try {
    // Save current scroll position
    const scrollY = window.scrollY;
    const scrollHeight = document.documentElement.scrollHeight;
    const scrollFraction = scrollY / scrollHeight;

    // Wait for content to render
    setTimeout(() => {
      // Restore scroll position
      const newScrollHeight = document.documentElement.scrollHeight;
      window.scrollTo(0, newScrollHeight * scrollFraction);

      // Update content
      set_div_content(div_class, content);

      if (typeof mermaid !== "undefined") {
        mermaid.init();
      }
      init_pdf_js();
    }, 50);
  } catch (error) {
    console.error("Error updating content:", error);
  }
}

// Handle tab clicks to switch between tabbed content
document.addEventListener("click", function (event) {
  const tab = event.target.closest('[id^="__tabbed_"]');
  if (tab) {
    // Get tab set number from ID
    const tabId = tab.id;
    const [_, tabSetNumber, tabNumber] = tabId.split("_");

    // Get all tabs in this set
    const allTabs = document.querySelectorAll(
      `[id^="__tabbed_${tabSetNumber}_"]`,
    );
    const allContents = document.querySelectorAll(
      `[id^="__tabbed_content_${tabSetNumber}_"]`,
    );

    // Update tabs and contents
    allTabs.forEach((t) => t.classList.remove("active"));
    allContents.forEach((c) => c.classList.remove("active"));

    // Activate clicked tab and its content
    tab.classList.add("active");
    const content = document.getElementById(
      `__tabbed_content_${tabSetNumber}_${tabNumber}`,
    );
    if (content) {
      content.classList.add("active");
    }
  }
});
