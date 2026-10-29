import { useCallback, useEffect, useRef } from 'react'

const DEFAULT_MAP_CENTER = { latitude: 35.771055, longitude: -78.674592 }

const MAP_DOCUMENT = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
      html, body, #map { height: 100%; margin: 0; }
      body { background: #e5e7eb; }
      .leaflet-container { overflow: hidden; font: 12px/1.5 Arial, Helvetica, sans-serif; }
      .leaflet-pane, .leaflet-tile, .leaflet-marker-icon, .leaflet-marker-shadow,
      .leaflet-tile-container, .leaflet-pane > svg, .leaflet-pane > canvas,
      .leaflet-zoom-box { position: absolute; left: 0; top: 0; }
      .leaflet-tile, .leaflet-marker-icon, .leaflet-marker-shadow { user-select: none; }
      .leaflet-tile { visibility: inherit; }
      .leaflet-tile-container { width: 0; height: 0; }
      .leaflet-control { position: relative; z-index: 800; pointer-events: auto; }
      .leaflet-top, .leaflet-bottom { position: absolute; z-index: 1000; pointer-events: none; }
      .leaflet-top { top: 0; }
      .leaflet-bottom { bottom: 0; }
      .leaflet-left { left: 0; }
      .leaflet-right { right: 0; }
      .leaflet-top .leaflet-control, .leaflet-bottom .leaflet-control { margin-top: 10px; }
      .leaflet-left .leaflet-control { margin-left: 10px; float: left; clear: both; }
      .leaflet-right .leaflet-control { margin-right: 10px; float: right; clear: both; }
      .leaflet-control-zoom a { display: block; width: 26px; height: 26px; line-height: 26px; text-align: center; text-decoration: none; color: #333; background: #fff; }
      .leaflet-control-zoom a + a { border-top: 1px solid #ccc; }
      .leaflet-control-zoom { box-shadow: 0 1px 5px rgba(0,0,0,.4); border-radius: 4px; overflow: hidden; }
      .leaflet-control-attribution { padding: 0 5px; color: #333; background: rgba(255,255,255,.8); }
      .leaflet-control-attribution a { color: #0078a8; }
      .map-loading {
        display: grid;
        height: 100%;
        place-items: center;
        color: #4b5563;
        font: 14px system-ui, sans-serif;
      }
    </style>
  </head>
  <body>
    <div id="map" aria-label="Street map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      (function () {
        var fallbackCenter = [35.771055, -78.674592];
        var marker;
        var map = L.map('map', {
          zoomControl: true,
          scrollWheelZoom: true,
          wheelDebounceTime: 40,
          wheelPxPerZoomLevel: 80,
        }).setView(fallbackCenter, 4);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
        }).addTo(map);

        function setLocation(latitude, longitude, zoom, hasPosition) {
          var nextCenter = [latitude, longitude];
          map.setView(nextCenter, zoom || map.getZoom());
          if (hasPosition) {
            if (!marker) marker = L.marker(nextCenter).addTo(map);
            marker.setLatLng(nextCenter);
          } else if (marker) {
            map.removeLayer(marker);
            marker = undefined;
          }
        }

        map.on('click', function (event) {
          var position = event.latlng;
          setLocation(position.lat, position.lng, map.getZoom(), true);
          window.parent.postMessage({
            type: 'site-map-position',
            latitude: Number(position.lat.toFixed(7)),
            longitude: Number(position.lng.toFixed(7)),
          }, '*');
        });

        window.addEventListener('message', function (event) {
          if (!event.data || event.data.type !== 'site-map-location') return;
          setLocation(event.data.latitude, event.data.longitude, event.data.zoom, event.data.hasPosition);
        });

        window.parent.postMessage({ type: 'site-map-ready' }, '*');
      }());
    </script>
  </body>
</html>`

function getMapLocation(gpsX, gpsY) {
  const longitude = Number(gpsX)
  const latitude = Number(gpsY)
  const hasPosition = gpsX !== '' && gpsY !== '' && Number.isFinite(longitude) && Number.isFinite(latitude)

  return {
    ...DEFAULT_MAP_CENTER,
    ...(hasPosition ? { latitude, longitude } : {}),
    hasPosition,
  }
}

export default function SiteLocationMap({ gpsX, gpsY, canWrite, onPositionChange }) {
  const iframeRef = useRef(null)
  const location = getMapLocation(gpsX, gpsY)

  const sendLocation = useCallback(() => {
    iframeRef.current?.contentWindow?.postMessage({
      type: 'site-map-location',
      latitude: location.latitude,
      longitude: location.longitude,
      hasPosition: location.hasPosition,
      zoom: location.hasPosition ? 15 : 4,
    }, '*')
  }, [location.latitude, location.longitude, location.hasPosition])

  useEffect(() => {
    function handleMapMessage(event) {
      if (event.source !== iframeRef.current?.contentWindow || !event.data) return
      if (event.data.type === 'site-map-ready') {
        sendLocation()
      } else if (event.data.type === 'site-map-position' && canWrite) {
        onPositionChange(event.data.latitude, event.data.longitude)
      }
    }

    window.addEventListener('message', handleMapMessage)
    return () => window.removeEventListener('message', handleMapMessage)
  }, [canWrite, onPositionChange, sendLocation])

  useEffect(() => {
    sendLocation()
  }, [sendLocation])

  return (
    <section className="site-location-map" aria-labelledby="site-location-map-heading">
      <div className="site-location-map-header">
        <div>
          <h2 id="site-location-map-heading">Choose a site location</h2>
          <p className="text-sm">Click the map to update the GPS longitude and latitude fields.</p>
        </div>
        {!canWrite && <span className="editor-readonly-badge">Read-only</span>}
      </div>
      <iframe
        ref={iframeRef}
        className="site-location-map-frame"
        title="Navigable street map for selecting the site location"
        srcDoc={MAP_DOCUMENT}
        sandbox="allow-scripts"
        onLoad={sendLocation}
      />
      <p className="site-location-map-attribution">Map data &copy; OpenStreetMap contributors.</p>
      <p className="site-location-map-reference">
        See also{' '}
        <a href="https://gis13.services.ncdot.gov/latlongmap/" target="_blank" rel="noreferrer">
          https://gis13.services.ncdot.gov/latlongmap/
        </a>{' '}
        for quick access to coordinates.
      </p>
    </section>
  )
}
