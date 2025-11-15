window.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("map_box") === null) {
      return; // No map element found
  }

  // Adjust sizes of the photo cluster icons on the main page
  var iconSize = 60;
  if (window.is_main_page === true) {
    iconSize = 100;
  }
  L.Photo.mergeOptions({
    icon: {
      iconSize: [iconSize, iconSize],
    }
  });

  L.Photo.Cluster.mergeOptions({
    icon: {
      iconSize: [iconSize, iconSize],
    },
    maxClusterRadius: iconSize * 1.5,
  });


  // Initialize map
  const map = L.map('map_box', {
    gestureHandling: true,
  	fullscreenControl: true,
  });
  window.theMap = map;
  var deferred = [];

  // Add OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
  }).addTo(map);

  L.control.scale().addTo(map);

  const photoLayer = L.photo.cluster().on('click', function(evt) {
    //evt.layer.bindPopup(L.Util.template(template, evt.layer.photo)).openPopup();
    GLightbox().openAt(evt.layer.photo.index);
  });

  window.ensure_photos_on_top = function() {
    // Ensure photo markers are on top
    for(var i in photoLayer._featureGroup._layers) {
      photoLayer._featureGroup._layers[i].setZIndexOffset(1000);
    }
  };

  // Ensure photos are on top on relevant events
  map.on('load', ensure_photos_on_top);
  map.on('zoomend', ensure_photos_on_top);
  map.on('moveend', ensure_photos_on_top);

  photoLayer.add(photo_data).addTo(map);

  var combinedBounds = L.latLngBounds([]);
  combinedBounds.extend(photoLayer.getBounds());
  if (combinedBounds.isValid()) {
    map.fitBounds(combinedBounds);
  }

  var showAllLink = document.getElementById("showall_link");
  if (showAllLink) {
    showAllLink.addEventListener("click", function(event) {
      event.preventDefault();
      if (combinedBounds.isValid()) {
        map.fitBounds(combinedBounds.pad(0.1));
      }
    });
  }

  if (gpx_data) {

    const iconoirIcon = function(iconName, colorClass) {
      return new L.divIcon({
        html: `<i class="iconoir-${iconName}"></i>`,
        className: `${colorClass}`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
    }

    const poiIcon = function(symbol) {
      return new iconoirIcon(symbol, 'map-simple-icon-light-blue');
    }

    const invisibleIcon = new L.divIcon({
      html: '',          // No HTML content
      className: 'invisible-marker', 
      iconSize: [0, 0]
    });

    // Standard icons
    const clusterIcon = iconoirIcon('xmark', 'map-simple-icon-orange map-cluster-icon');
    const starIcon = iconoirIcon('star-solid', 'map-simple-icon-green');
    const markdownIcon = iconoirIcon('book-solid', 'map-simple-icon-purple');
    const audioIcon = iconoirIcon('microphone-solid', 'map-simple-icon-purple');

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
          // Standard icons
          '': starIcon,
          'mkmapdiary|cluster-mass': invisibleIcon,
          'mkmapdiary|cluster-center': invisibleIcon,
          'mkmapdiary|markdown-journal-entry': markdownIcon,
          'mkmapdiary|audio-journal-entry': audioIcon,

          // POI icons based on symbol field
          'mkmapdiary|poi|city': poiIcon('city'),
          'mkmapdiary|poi|town': poiIcon('building'),
          'mkmapdiary|poi|village': poiIcon('neighbourhood'),
          'mkmapdiary|poi|information': poiIcon('info-circle'),
          'mkmapdiary|poi|tourism': poiIcon('spark-solid'),
          'mkmapdiary|poi|picnic_site': poiIcon('home-table'),
          'mkmapdiary|poi|viewpoint': poiIcon('camera'),
          'mkmapdiary|poi|train_station': poiIcon('train'),
          'mkmapdiary|poi|bus_stop': poiIcon('bus-stop'),
          'mkmapdiary|poi|accommodation': poiIcon('bed'),
          'mkmapdiary|poi|restaurant': poiIcon('cutlery'),
          'mkmapdiary|poi|cafe_bar': poiIcon('coffee-cup'),
          'mkmapdiary|poi|museum': poiIcon('palette'),
          'mkmapdiary|poi|historic': poiIcon('historic-shield'),
          'mkmapdiary|poi|place_of_worship': poiIcon('church'),
          'mkmapdiary|poi|shopping': poiIcon('cart'),
          'mkmapdiary|poi|services': poiIcon('spark-solid'),
          'mkmapdiary|poi|recreation': poiIcon('soccer-ball'),
          'mkmapdiary|poi|natural_features': poiIcon('spark-solid'),
          'mkmapdiary|poi|landmarks': poiIcon('spark-solid'),
          'mkmapdiary|poi|airport': poiIcon('airplane'),
          'mkmapdiary|poi|ferry_terminal': poiIcon('sea-waves'),
          'mkmapdiary|poi|forest_or_park': poiIcon('tree'),
          'mkmapdiary|poi|beach': poiIcon('swimming'),
          'mkmapdiary|poi|golf_course': poiIcon('golf'),
          'mkmapdiary|poi|marina': poiIcon('sea-waves'),
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
      if (wpt_data.sym == "mkmapdiary|markdown-journal-entry" || wpt_data.sym == "mkmapdiary|audio-journal-entry") {
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
      if (wpt_data.sym == "mkmapdiary|cluster-center") {
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
      document.getElementById('map_box').scrollIntoView({behavior: "smooth", block: "nearest"});
      const lat = parseFloat(this.getAttribute('data-lat'));
      const lng = parseFloat(this.getAttribute('data-lng'));
      if (!isNaN(lat) && !isNaN(lng)) {
        const zoom = Math.max(map.getZoom(), 13);
        map.setView([lat, lng], zoom);
      }
    });
  });

});