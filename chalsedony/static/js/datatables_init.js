$(document).ready(function() {
    // Check if table is already initialized
    if (!$.fn.DataTable.isDataTable('.dataTablesContainer table')) {
        $('.dataTablesContainer table').DataTable({
            pageLength: 50, // Number of rows
            ordering: false // Disable default sorting
        });
    }
});
