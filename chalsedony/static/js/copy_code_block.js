/*
This will copy a code block to the clipboard when the middle mouse button is clicked on it.
It requires the user to click near text though, so it's not perfect.

Note that this corresponds to the highlight code block which comes from pymdownx.superfences
If using codehilite (the default in python's markdown library), adjust the selector accordingly.

I forget what comrak uses, checkout the draftsmith-rs source code.
*/

// Handle middle-click to copy code blocks
document.addEventListener("mousedown", (event) => {
  if (event.button === 1) {
    // Middle mouse button
    const codeBlock = event.target.closest(".highlight code");
    if (codeBlock) {
      const filename = codeBlock
        .closest(".highlight")
        .querySelector(".filename")?.textContent;
      const codeContent = codeBlock.textContent;

      // Copy to clipboard with fallback
      const copyText = () => {
        try {
          if (navigator.clipboard) {
            return navigator.clipboard.writeText(codeContent);
          }
          // Fallback for browsers without clipboard API
          const textarea = document.createElement("textarea");
          textarea.value = codeContent;
          document.body.appendChild(textarea);
          textarea.select();
          const result = document.execCommand("copy");
          document.body.removeChild(textarea);
          return result ? Promise.resolve() : Promise.reject("Copy failed");
        } catch (err) {
          return Promise.reject(err);
        }
      };

      copyText()
        .then(() => {
          // Visual feedback
          const originalBg = codeBlock.style.backgroundColor;
          codeBlock.style.backgroundColor = "#00ff0033";
          setTimeout(() => {
            codeBlock.style.backgroundColor = originalBg;
          }, 200);

          if (filename) {
            console.log(`Copied ${filename} content to clipboard`);
          }
        })
        .catch((err) => {
          console.error("Failed to copy code:", err);
          alert("Copy failed - please use Ctrl+C instead");
        });
    }
  }
});
