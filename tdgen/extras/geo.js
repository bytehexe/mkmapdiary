window.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("map") === null) {
      return; // No map element found
  }

  // Initialize map
  const map = L.map('map');
  window.theMap = map;
  var deferred = [];

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

    const invisibleIcon = new L.divIcon({
      html: '',          // No HTML content
      className: 'invisible-marker', 
      iconSize: [0, 0]
    })

    const clusterIcon = new L.icon({
      iconUrl: 'cross-orange.svg',
      iconSize: [17, 17],
      iconAnchor: [9, 9],
      className: 'map-cluster-icon',
    });

    const startIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-play-solid"></i>',
      className: 'map-simple-icon map-simple-icon-blue',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    })

    const endIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-pause-solid"></i>',
      className: 'map-simple-icon map-simple-icon-blue',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    })

    const starIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-star-solid"></i>',
      className: 'map-simple-icon map-simple-icon-green',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    })

    parser = new DOMParser();
    xmlDoc = parser.parseFromString(gpx_data, "text/xml");
    
    const gpx = new L.GPX(gpx_data, {
      async: true,
      max_point_interval: 15000,
      markers: {
        startIcon: invisibleIcon,
        endIcon: invisibleIcon,
        wptIcons: {
          '': starIcon,
          'cluster-mass': clusterIcon,
          'cluster-center': invisibleIcon,
        }
      }
    }).on('addpoint', function(e) {
      if (e.point_type == "waypoint" && e.element.querySelector("sym") && e.element.querySelector("sym").innerHTML == "cluster-center") {
        console.log('Added cluster ' + e.point_type + ' point:', e);
        var pdop = parseFloat(e.element.querySelector("pdop").innerHTML);
        deferred.push(new L.circle(e.point._latlng, {
          radius: pdop,
          color: 'orange',
        }));
      }
    }).on('loaded', function(e) {
      combinedBounds.extend(e.target.getBounds());
      map.fitBounds(combinedBounds);
      for (const layer of deferred) {
        layer.addTo(map);
      }

      map.on('zoomend', function() {
        const currentZoom = map.getZoom();
        elements = document.querySelectorAll('.map-cluster-icon');
        console.log(`Current zoom level: ${currentZoom}, found ${elements.length} cluster icons.`);
        elements.forEach((el) => {
          if (currentZoom < 15) {
            el.style.display = 'none';
          } else {
            el.style.display = 'block';
          }
        });
      });
      map.fire('zoomend');

    }).addTo(map);
  }

});