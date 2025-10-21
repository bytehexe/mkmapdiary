window.addEventListener("DOMContentLoaded", () => {

    // Justified Gallery

    function rem2px(rem) {    
        return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
    }

    var base_height_rem = 6;
    var gallery = document.getElementById("photo_gallery");
    if (gallery === null) {
        return; // No gallery element found
    }
    var aspectRatios = Array.from(gallery.querySelectorAll("img")).map((x) => (Math.max(1, x.offsetHeight / x.offsetWidth)))
    var avgAspectRatio = aspectRatios.reduce((a, b) => a + b, 0) / aspectRatios.length;
    var rowHeight = Math.min(avgAspectRatio * rem2px(base_height_rem), rem2px(2*base_height_rem));

    console.log("avgAspectRatio", avgAspectRatio, "rowHeight", rowHeight);

    $("#photo_gallery p").justifiedGallery({
        rowHeight: rowHeight,
        margins: 3,
        lastRow: 'center',
        cssAnimation: false,
        imagesAnimationDuration: 50,
    });
});