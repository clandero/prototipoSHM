function showBridgeOnMap(x, y){
    var mymap = L.map('map').setView([x,y],17);
    L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(mymap);
    var marker = L.marker([x,y]).addTo(mymap);
}