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

  document.getElementById("showall_link").addEventListener("click", function(event) {
    event.preventDefault();
    if (combinedBounds.isValid()) {
      map.fitBounds(combinedBounds.pad(0.1));
    }
  });

  if (gpx_data) {

    const invisibleIcon = new L.divIcon({
      html: '',          // No HTML content
      className: 'invisible-marker', 
      iconSize: [0, 0]
    });

    const clusterIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-xmark"></i>',
      className: 'map-simple-icon map-simple-icon-orange map-cluster-icon',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const startIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-play-solid"></i>',
      className: 'map-simple-icon map-simple-icon-blue',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const endIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-pause-solid"></i>',
      className: 'map-simple-icon map-simple-icon-blue',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const starIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-star-solid"></i>',
      className: 'map-simple-icon map-simple-icon-green',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const markdownIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-book-solid"></i>',
      className: 'map-simple-icon map-simple-icon-purple',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const audioIcon = new L.divIcon({
      html: '<i class="iconoir iconoir-microphone-solid"></i>',
      className: 'map-simple-icon map-simple-icon-purple',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    parser = new DOMParser();
    xmlDoc = parser.parseFromString(gpx_data, "text/xml");
    
    const gpx = new L.GPX(gpx_data, {
      async: true,
      max_point_interval: 15000,
      polyline_options: {
        color: '#3F51B5',
        lineCap: 'round'
      },
      markers: {
        startIcon: invisibleIcon,
        endIcon: invisibleIcon,
        wptIcons: {
          '': starIcon,
          'cluster-mass': clusterIcon,
          'cluster-center': invisibleIcon,
          'markdown-journal-entry': markdownIcon,
          'audio-journal-entry': audioIcon,
        }
      }
    }).on('addpoint', function(e) {
      if (e.point_type != "waypoint") {
        return;
      }

      var get = function(key) {
        var el = e.element.querySelector(key);
        return el ? el.innerHTML : null;
      }

      // Extract waypoint data
      var wpt_data = {
        "sym": get("sym"),
        "pdop": get("pdop"),
      };

      // Unbind popup for journal waypoints
      if (wpt_data.sym == "markdown-journal-entry" || wpt_data.sym == "audio-journal-entry") {
        var comment = get("cmt");
        e.point.unbindPopup().on('click', function() {
          console.log("Clicked waypoint with comment: " + comment);
          if (comment) {
            var entry = document.getElementById("asset-" + comment);
            if (entry) {
              entry.scrollIntoView({behavior: "smooth"});
              entry.classList.add("active-highlight");
              setTimeout(() => {
                entry.classList.remove("active-highlight");
              }, 1000);
            }
          }
        });
      }

      // Add circle for cluster waypoints
      if (wpt_data.sym == "cluster-center") {
        var pdop = parseFloat(wpt_data.pdop);
        deferred.push(new L.circle(e.point._latlng, {
          radius: pdop,
          color: '#FF9800',
        }));
      }
    }).on('loaded', function(e) {
      combinedBounds.extend(e.target.getBounds());
      map.fitBounds(combinedBounds.pad(0.1));
      for (const layer of deferred) {
        layer.addTo(map);
      }

      map.on('zoomend', function() {
        const currentZoom = map.getZoom();
        elements = document.querySelectorAll('.map-cluster-icon');
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

  // Handle location links
  document.querySelectorAll('.location-link').forEach(link => {
    link.addEventListener('click', function(event) {
      event.preventDefault();
      document.getElementById('map').scrollIntoView({behavior: "smooth", block: "nearest"});
      const lat = parseFloat(this.getAttribute('data-lat'));
      const lng = parseFloat(this.getAttribute('data-lng'));
      if (!isNaN(lat) && !isNaN(lng)) {
        const zoom = Math.max(map.getZoom(), 13);
        map.setView([lat, lng], zoom);
      }
    });
  });

});