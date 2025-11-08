window.addEventListener("DOMContentLoaded", () => {

    // Justified Gallery

    function rem2px(rem) {    
        return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
    }

    var base_height_rem = 6;
    var gallery = document.getElementById("photo_gallery");
    if (gallery === null) {
        return; // No gallery element 
    }
    var aspectRatios = Array.from(gallery.querySelectorAll("img")).map((x) => (Math.max(1, x.offsetHeight / x.offsetWidth)))
    var avgAspectRatio = aspectRatios.reduce((a, b) => a + b, 0) / aspectRatios.length;
    var rowHeight = Math.min(avgAspectRatio * rem2px(base_height_rem), rem2px(2*base_height_rem));

    console.log("avgAspectRatio", avgAspectRatio, "rowHeight", rowHeight);

    var parameters = {
        rowHeight: rowHeight,
        margins: 3,
        lastRow: 'center',
        cssAnimation: false,
        imagesAnimationDuration: 50,
    };

    if (window.is_main_page === true) {
        parameters.maxRowsCount = window.gallery_max_rows;
        parameters.randomize = true;
    }

    $("#photo_gallery p").justifiedGallery(parameters);
});