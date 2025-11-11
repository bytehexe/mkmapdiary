window.addEventListener("DOMContentLoaded", () => {

    // Justified Gallery

    var parameters = {
        margins: 3,
        border: 0,
        rowHeight: 120,
        maxRowHeight: 240,
        cssAnimation: false,
        imagesAnimationDuration: 50,
    };

    if (window.is_main_page === true) {
        parameters.maxRowsCount = window.gallery_max_rows;
        parameters.lastRow = 'hide';
    } else {
        parameters.lastRow = 'center';
    }

    window.theGallery = $("#photo_gallery p");
    window.theGallery.justifiedGallery(parameters);
    
});