window.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("map") === null) {
      return; // No map element found
  }

  // Initialize map
  const map = L.map('map');

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
  combinedBounds.extend(photoLayer.getBounds());
  if (combinedBounds.isValid()) {
    map.fitBounds(combinedBounds);
  }

  if (gpx_data) {
    parser = new DOMParser();
    xmlDoc = parser.parseFromString(gpx_data, "text/xml");
    
    const gpx = new L.GPX(gpx_data, {
      async: true,
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
    }).on('addpoint', function(e) {
      console.log('Added ' + e.point_type + ' point:', e);
    }).on('loaded', function(e) {
      combinedBounds.extend(e.target.getBounds());
      map.fitBounds(combinedBounds);
    }).addTo(map);
  }

});