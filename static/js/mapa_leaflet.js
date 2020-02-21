//Función que permite manejar los puntos en el mapa

//Setup del mapa, establece latitud y longitud, y permite generar popups al hacer clic
function onMapClick(e) {
    popup.setLatLng(e.latlng);
    popup.setContent("Has pulsado en Lat=" + e.latlng.lat + " Long=" + e.latlng.lng);
    popup.openOn(map);
}


function mapa_del_puente(coord_x, coord_y){
    //mapa político
    var osmLayer = new L.TileLayer('https://api.maptiler.com/maps/basic/{z}/{x}/{y}.png?key=zZkrANgINoCERa0zI6td');
    //mapa físico
    var ESRIWorldImageryLayer = new L.TileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}');

    var baseMaps = {
        'OpenStreetMap' : osmLayer,
        'ESRI World Imagery': ESRIWorldImageryLayer
    };

    //se agregan imagenes satelitales al mapa
    var layerControl = new L.control.layers(baseMaps);
    //Se crea el mapa, se establece el foco y zoom iniciales
    var map = L.map('map');
    map.setView(new L.LatLng(coord_x, coord_y),10);
    map.addControl(layerControl);    
    map.addLayer(ESRIWorldImageryLayer);

    
    var popup = new L.popup();
    var marker = L.marker([coord_x, coord_y]).addTo(map);
    map.on('click', onMapClick);
}