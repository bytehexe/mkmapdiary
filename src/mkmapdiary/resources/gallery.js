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
    window.theGallery.justifiedGallery(parameters).on('jg.complete', function () {
        addQualityMarkers();
    });
});


function addQualityMarkers() {
    var $gallery_images = $("#photo_gallery img");
    $gallery_images.each(function() {
        var $this = $(this);
        $gallery_images.find(".quality_marker").remove();
        var markers = $this.data("markers").split(" ");
        var $qm = $("<span class='quality_marker'></span>");
        for (var marker of markers) {
            var $marker_span = $("<i></i>")
            if (marker === "good") {
                $marker_span.addClass("iconoir-star").attr("title", "Good quality");
                $qm.append($marker_span);
            } else if (marker === "bad") {
                $marker_span.addClass("iconoir-priority-down").attr("title", "Bad quality");
                $qm.append($marker_span);
            } else if (marker === "excellent") {
                $marker_span.addClass("iconoir-flower").attr("title", "Excellent quality");
                $qm.append($marker_span);
            } else if (marker === "low_entropy") {
                $marker_span.addClass("iconoir-priority-medium").attr("title", "Low entropy");
                $qm.append($marker_span);
            } else if (marker === "duplicate") {
                $marker_span.addClass("iconoir-minus-square").attr("title", "Duplicate image");
                $qm.append($marker_span);
            } else if (marker === "canonical") {
                $marker_span.addClass("iconoir-plus-circle").attr("title", "Canonical image");
                $qm.append($marker_span);
            }
        }
        $this.after($qm);
    });
}