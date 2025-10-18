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


  gpx_data = '<?xml version="1.0" encoding="UTF-8"?> <gpx version="1.1" creator="ChatGPT - GPT-5" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"> <wpt lat="48.8566" lon="2.3522"> <name>Paris</name> <desc>Capital city of France</desc> </wpt> <trk> <name>Seine Walk</name> <desc>Short track through central Paris</desc> <trkseg> <trkpt lat="48.8570" lon="2.3499"><ele>35.0</ele></trkpt> <trkpt lat="48.8578" lon="2.3525"><ele>34.5</ele></trkpt> <trkpt lat="48.8586" lon="2.3551"><ele>33.8</ele></trkpt> </trkseg> </trk> </gpx>';
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

  photoLayer.add(photo_data).addTo(map);

  var combinedBounds = L.latLngBounds([]);


  function addLayerBounds(obj) {
    for (const layer_id in obj._layers) {
      layer = obj._layers[layer_id]
      if (layer._bounds) {
        combinedBounds.extend(layer._bounds);
      }
      if (layer._layers) {
        addLayerBounds(layer)
      }
    }
  }

  addLayerBounds(gpx)

  combinedBounds.extend(photoLayer.getBounds());
  map.fitBounds(combinedBounds);

});