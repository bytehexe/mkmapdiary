window.addEventListener("DOMContentLoaded", () => {

    // Justified Gallery

    var parameters = {
        margins: 3,
        border: 0,
        rowHeight: 120,
        maxRowHeight: 240,
        cssAnimation: false,
        imagesAnimationDuration: 50,
        filter: computeFilter(),
    };

    if (window.is_main_page === true) {
        parameters.maxRowsCount = window.gallery_max_rows;
        parameters.lastRow = 'hide';
    } else {
        parameters.lastRow = 'center';
    }

    window.theGallery = $("#photo_gallery p");
    window.theGallery.justifiedGallery(parameters)

    $("#include_duplicates, #include_bad_quality").on("change", function() {
        var filter = computeFilter();
        window.theGallery.justifiedGallery({'filter': filter});
    });

    $("#show_quality_icons").on("change", function() {
        if ($(this).is(":checked")) {
            addQualityMarkers();
        } else {
            clearQualityMarkers();
        }
    });

});

function computeFilter() {
    var include_duplicates = $("#include_duplicates").is(":checked");
    var include_bad_quality = $("#include_bad_quality").is(":checked");

    filters = [];
    if (!include_duplicates) {
        filters.push(":not([data-markers~=duplicate])");
    }
    if (!include_bad_quality) {
        filters.push(":not([data-markers~=bad])");
    }
    return ":has(img" + filters.join("") + ")";
}

function clearQualityMarkers() {
    $("#photo_gallery .quality_marker").remove();
}

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