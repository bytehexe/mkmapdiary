window.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("map") === null) {
      return; // No map element found
  }

  // Initialize map
  const map = L.map('map').setView([48.1372, 11.5756], 13); // Example: Munich

  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
  }).addTo(map);

  const photoLayer = L.photo.cluster().on('click', function(evt) {
    //evt.layer.bindPopup(L.Util.template(template, evt.layer.photo)).openPopup();
    GLightbox().openAt(evt.layer.photo.index);
  });

  photoLayer.add(photo_data).addTo(map);

  var combinedBounds = L.latLngBounds([]);

  if (gpx_data) {
    parser = new DOMParser();
    xmlDoc = parser.parseFromString(gpx_data, "text/xml");
    
    const gpx = new L.GPX(gpx_data, {
      max_point_interval: 15000,
      markers: {
        startIcon: new L.AwesomeMarkers.icon({
          icon: 'play-solid',
          prefix: 'iconoir',
        }),
        endIcon: new L.AwesomeMarkers.icon({
          icon: 'pause-solid',
          prefix: 'iconoir',

        }),
        wptIcons: {
          '': new L.AwesomeMarkers.icon({
            icon: 'star-solid',
            markerColor: 'red',
            iconColor: 'white',
            prefix: 'iconoir',
          })
        }
      }
    });
    gpx.addTo(map);

    function addLayerBounds(obj) {
      for (const layer_id in obj._layers) {
        layer = obj._layers[layer_id]
        if (layer._bounds) {
          console.log("Layer bounds", layer._bounds);
          combinedBounds.extend(layer._bounds);
        }
        if (layer._layers) {
          addLayerBounds(layer)
        }
        if (!layer._bounds && layer._latlng) {
          console.log("No bounds, but latlng", layer);
          var bounds = new L.LatLngBounds(layer._latlng, layer._latlng);
          if(!bounds.isValid()) {
            console.error("Generated bounds should be valid");
          }
          combinedBounds.extend(bounds);
        }
      }
    }

    console.log("GPX",gpx);
    addLayerBounds(gpx)
    

  }

  combinedBounds.extend(photoLayer.getBounds());
  console.log("Combined Bounds", combinedBounds);
  map.fitBounds(combinedBounds);

});