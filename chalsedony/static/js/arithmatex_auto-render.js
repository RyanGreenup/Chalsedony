(function () {
  'use strict';

  var katexMath = function() {
    var maths = document.querySelectorAll('.arithmatex'),
        tex;

    for (var i = 0; i < maths.length; i++) {
      tex = maths[i].textContent || maths[i].innerText;
      if (tex.startsWith('\\(') && tex.endsWith('\\)')) {
        katex.render(tex.slice(2, -2), maths[i], {'displayMode': false});
      } else if (tex.startsWith('\\[') && tex.endsWith('\\]')) {
        katex.render(tex.slice(2, -2), maths[i], {'displayMode': true});
      }
    }
  };

  var observeDOMChanges = function(callback) {
    const targetNode = document.body;
    const config = { childList: true, subtree: true, characterData: true };

    const observer = new MutationObserver(function(mutationsList) {
      mutationsList.forEach(function(mutation) {
        if (mutation.type === 'childList' || mutation.type === 'characterData') {
          callback();
        }
      });
    });

    observer.observe(targetNode, config);
  };

  var onReady = function(fn) {
    if (document.addEventListener) {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      document.attachEvent("onreadystatechange", function () {
        if (document.readyState === "interactive") {
          fn();
        }
      });
    }
  };

  onReady(function () {
    if (typeof katex !== "undefined") {
      // Run the initial katex math rendering
      katexMath();

      // Set up the observer to watch for changes and re-render katex math
      observeDOMChanges(katexMath);
    }
  });
}());

