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

    const template = `
  <div class="popup" style="width:200px; height:200px;">
    <a href="javascript:window.GLightbox().openAt({index}+1)" class="glightbox">
      <img width=200 height=200 src="{photo}" />
    </a>
  </div>
`;

const photoLayer = L.photo.cluster().on('click', function(evt) {
  evt.layer.bindPopup(L.Util.template(template, evt.layer.photo)).openPopup();
});

photoLayer.add(photo_data).addTo(map);

var combinedBounds = L.latLngBounds([]);

combinedBounds.extend(photoLayer.getBounds());

map.fitBounds(combinedBounds);


});