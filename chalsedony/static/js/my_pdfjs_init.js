function init_pdf_js() {
    // Get all elements with class 'pdfjs_preview'
    var pdfContainers = document.querySelectorAll('.pdfjs_preview');

    // Loop through each container
    pdfContainers.forEach(function(container) {
        var url = container.getAttribute('data-src');
        if (!url) {
            console.error('No data-src attribute found for PDF container:', container);
            return;
        }

        // Create controls dynamically
        var controls = document.createElement('div');
        controls.className = 'controls';

        var prevButton = document.createElement('button');
        prevButton.textContent = 'Previous Page';
        prevButton.id = 'prev-page';

        var pageNumberElement = document.createElement('span');
        pageNumberElement.id = 'page-number';

        var pageCountSeparator = document.createTextNode(' / ');

        var pageCountElement = document.createElement('span');
        pageCountElement.id = 'page-count';

        var nextButton = document.createElement('button');
        nextButton.textContent = 'Next Page';
        nextButton.id = 'next-page';

        var zoomLabel = document.createElement('label');
        zoomLabel.htmlFor = 'zoom';
        zoomLabel.textContent = 'Zoom: ';

        var zoomInput = document.createElement('input');
        zoomInput.type = 'range';
        zoomInput.id = 'zoom';
        zoomInput.min = 50;
        zoomInput.max = 200;
        zoomInput.value = 150;

        controls.appendChild(prevButton);
        controls.appendChild(pageNumberElement);
        controls.appendChild(pageCountSeparator);
        controls.appendChild(pageCountElement);
        controls.appendChild(nextButton);
        controls.appendChild(zoomLabel);
        controls.appendChild(zoomInput);

        container.insertBefore(controls, container.firstChild); // Insert controls before the placeholder

        // Create a scrollable container
        var scrollContainer = document.createElement('div');
        scrollContainer.className = 'scroll-container';
        container.appendChild(scrollContainer);

        // Create a canvas element inside the scrollable container
        var canvas = document.createElement('canvas');
        scrollContainer.appendChild(canvas);

        // Find the placeholder element and hide it
        var placeholder = container.querySelector('.placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        } else {
            console.error('Placeholder not found in PDF container:', container);
        }

        let pdfDoc = null;
        let currentPageNumber = 1;

        // Function to render a specific page
        function renderPage(pageNumber, scale) {
            if (pdfDoc === null) return;
            currentPageNumber = pageNumber;
            pdfDoc.getPage(pageNumber).then(function(page) {
                var viewport = page.getViewport({ scale: scale });

                // Prepare canvas using PDF page dimensions
                var context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;

                // Render PDF page into canvas context
                var renderContext = {
                    canvasContext: context,
                    viewport: viewport
                };
                page.render(renderContext);
            }).catch(function(error) {
                console.error('Error rendering the page:', error);
            });
        }

        // Function to update controls based on current page number and total pages
        function updateControls() {
            if (pdfDoc === null) return;
            pageNumberElement.textContent = currentPageNumber;
            pageCountElement.textContent = pdfDoc.numPages;
        }

        // Load the PDF document
        pdfjsLib.getDocument(url).promise.then(function(pdf) {
            pdfDoc = pdf;
            renderPage(currentPageNumber, zoomInput.value / 100);
            updateControls();

            // Event listeners for navigation buttons
            prevButton.addEventListener('click', function() {
                if (currentPageNumber > 1) {
                    renderPage(currentPageNumber - 1, zoomInput.value / 100);
                    updateControls();
                }
            });

            nextButton.addEventListener('click', function() {
                if (currentPageNumber < pdfDoc.numPages) {
                    renderPage(currentPageNumber + 1, zoomInput.value / 100);
                    updateControls();
                }
            });

            // Event listener for zoom input
            zoomInput.addEventListener('input', function() {
                renderPage(currentPageNumber, zoomInput.value / 100);
            });
        }).catch(function(error) {
            console.error('Error loading the PDF:', error);
            if (placeholder) {
                placeholder.style.display = 'block';
                placeholder.textContent = 'Failed to load PDF.';
            }
        });
    });
}
document.addEventListener("DOMContentLoaded", init_pdf_js);
