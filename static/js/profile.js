function getValue(){
	var shownVal = document.getElementById("autocomplete").value;
	var value2send = document.querySelector("#estructuras" + " option[value='" + shownVal + "']").dataset.value;
	print(value2send);
}
function setMarkersOnMap(x){
    var mymap = L.map('map').setView([-36.906289,-72.398971],6);
    L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(mymap);
    var markers = L.markerClusterGroup()
    var puentes = x;
    for (var i=0; i < puentes.length; i++){
    markers.addLayer(L.marker([puentes[i][0], puentes[i][1]]).bindPopup('<a href=\"/estructura/'+puentes[i][3]+'\">'+puentes[i][2]+'</a>'));
    }
    mymap.addLayer(markers);
}