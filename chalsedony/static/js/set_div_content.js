function set_div_content(div_class, content) {
    // First ensure KaTeX is loaded
    if (typeof renderMathInElement === 'undefined') {
        /*
        If KaTeX is not loaded, The content hasn't been set,
        So don't worry for now
        */
    } else {
        const container = document.querySelector(`div.${div_class}`);
        if (!container) return;
        
        // Parse content while preserving script tags
        const parser = new DOMParser();
        const doc = parser.parseFromString(content, 'text/html');
        // Save open/closed state of all details elements using their summary text as key
        const detailsStates = new Map();
        container.querySelectorAll('details').forEach(details => {
            const summary = details.querySelector('summary');
            if (summary) {
                detailsStates.set(summary.textContent.trim(), details.open);
            }
        });

        // Clear container and append new nodes
        container.innerHTML = '';
        Array.from(doc.body.childNodes).forEach(node => {
            container.appendChild(node);
        });

        // Execute any script tags
        container.querySelectorAll('script').forEach(oldScript => {
            const newScript = document.createElement('script');
            Array.from(oldScript.attributes).forEach(attr => {
                newScript.setAttribute(attr.name, attr.value);
            });
            newScript.appendChild(document.createTextNode(oldScript.innerHTML));
            oldScript.parentNode.replaceChild(newScript, oldScript);
        });

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


// Handle tab clicks to switch between tabbed content
document.addEventListener('click', function(event) {
    const tab = event.target.closest('[id^="__tabbed_"]');
    if (tab) {
        // Get tab set number from ID
        const tabId = tab.id;
        const [_, tabSetNumber, tabNumber] = tabId.split('_');
        
        // Get all tabs in this set
        const allTabs = document.querySelectorAll(`[id^="__tabbed_${tabSetNumber}_"]`);
        const allContents = document.querySelectorAll(`[id^="__tabbed_content_${tabSetNumber}_"]`);
        
        // Update tabs and contents
        allTabs.forEach(t => t.classList.remove('active'));
        allContents.forEach(c => c.classList.remove('active'));
        
        // Activate clicked tab and its content
        tab.classList.add('active');
        const content = document.getElementById(`__tabbed_content_${tabSetNumber}_${tabNumber}`);
        if (content) {
            content.classList.add('active');
        }
    }
});
