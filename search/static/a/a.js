async function fetch_stops_bbox(sw_lon, sw_lat, ne_lon, ne_lat, zoom){
    const url = `/location_search/?sw_lon=${sw_lon}&sw_lat=${sw_lat}&ne_lon=${ne_lon}&ne_lat=${ne_lat}&zoom=${zoom}`;
    const response = await fetch(url);
    const json = await response.json();
    return json.data;
};