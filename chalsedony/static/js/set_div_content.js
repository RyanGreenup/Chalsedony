function set_div_content(div_class, content) {
    // First ensure KaTeX is loaded
    if (typeof renderMathInElement === 'undefined') {
        /*
        If KaTeX is not loaded, The content hasn't been set,
        So don't worry for now
        */
    } else {
        const container = document.querySelector(`div.${div_class}`);
        // Save open/closed state of all details elements using their summary text as key
        const detailsStates = new Map();
        container.querySelectorAll('details').forEach(details => {
            const summary = details.querySelector('summary');
            if (summary) {
                detailsStates.set(summary.textContent.trim(), details.open);
            }
        });

        // Update content
        container.innerHTML = content;

        // Restore open/closed state using summary text as key
        container.querySelectorAll('details').forEach(newDetails => {
            const summary = newDetails.querySelector('summary');
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
                {left: '$$', right: '$$', display: true},  // Block math
                {left: '$', right: '$', display: false},   // Inline math
                {left: '\\\\(', right: '\\\\)', display: false},  // Inline math
                {left: '\\\\[', right: '\\\\]', display: true}    // Block math
            ],
            throwOnError: true,
            strict: true
        });
    }
}


// I have implemnted that have the following ids: __tabbed_<tab_set_number>_<tab_number>, Write javascript to ensure when one tab is clicked, all tabs change AI!
