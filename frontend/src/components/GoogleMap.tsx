import React, { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { VehicleRoute } from '../types';

interface GoogleMapProps {
  routes: VehicleRoute[];
  depotLocations: {
    name: string;
    address: string;
    latitude: number;
    longitude: number;
  }[];
  className?: string;
}

const GoogleMap: React.FC<GoogleMapProps> = ({ routes, depotLocations, className }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  console.log('GoogleMap component rendered with:', {
    routesCount: routes?.length || 0,
    depotLocationsCount: depotLocations?.length || 0,
    hasApiKey: !!GOOGLE_MAPS_API_KEY
  });

  useEffect(() => {
    const initMap = async () => {
      const loader = new Loader({
        apiKey: GOOGLE_MAPS_API_KEY,
        version: 'weekly',
        libraries: ['places']
      });

      try {
        await loader.load();
        setIsLoaded(true);

        if (mapRef.current) {
          const mapInstance = new google.maps.Map(mapRef.current, {
            center: depotLocations && depotLocations.length > 0 ? 
              { lat: depotLocations[0].latitude, lng: depotLocations[0].longitude } : 
              { lat: 31.1435, lng: -93.2607 }, // Default to Leesville
            zoom: 8,
            mapTypeId: google.maps.MapTypeId.ROADMAP,
          });

          setMap(mapInstance);
        }
      } catch (error) {
        console.error('Error loading Google Maps:', error);
      }
    };

    initMap();
  }, [GOOGLE_MAPS_API_KEY, depotLocations]);

  useEffect(() => {
    if (!map || !isLoaded) {
      console.log('GoogleMap useEffect skipped:', { map: !!map, isLoaded });
      return;
    }

    console.log('GoogleMap useEffect running with:', {
      routesLength: routes.length,
      depotLocationsCount: depotLocations.length,
      mapInstance: !!map
    });

    depotLocations.forEach((depot, index) => {
      console.log('Creating depot marker at:', depot);
      const depotColors = ['#FF0000', '#00FF00', '#0000FF']; // Red, Green, Blue
      new google.maps.Marker({
        position: { lat: depot.latitude, lng: depot.longitude },
        map: map,
        title: `Depot: ${depot.name} - ${depot.address}`,
        icon: {
          url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
            <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
              <circle cx="16" cy="16" r="12" fill="${depotColors[index % depotColors.length]}" stroke="#FFFFFF" stroke-width="2"/>
              <text x="16" y="20" text-anchor="middle" fill="white" font-size="10" font-weight="bold">${depot.name.charAt(0)}</text>
            </svg>
          `),
          scaledSize: new google.maps.Size(32, 32),
        }
      });
    });

    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
      '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
    ];

    console.log('Processing routes:', routes.length);
    routes.forEach((route, routeIndex) => {
      console.log(`Processing route ${routeIndex}:`, {
        vehicle_id: route.vehicle_id,
        route_points_count: route.route_points.length,
        total_distance: route.total_distance_miles
      });
      
      const color = colors[routeIndex % colors.length];
      
      const path: google.maps.LatLng[] = [];
      
      const routeDepot = depotLocations.find(depot => depot.name === route.depot_name);
      if (routeDepot) {
        path.push(new google.maps.LatLng(routeDepot.latitude, routeDepot.longitude));
      }

      route.route_points.forEach((point) => {
        console.log(`Creating marker for customer ${point.customer_id}:`, point);
        new google.maps.Marker({
          position: { lat: point.latitude, lng: point.longitude },
          map: map,
          title: `${point.customer_name} (Stop ${point.order + 1})`,
          icon: {
            url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
              <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="${color}" stroke="#FFFFFF" stroke-width="2"/>
                <text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">${route.vehicle_id}</text>
              </svg>
            `),
            scaledSize: new google.maps.Size(24, 24),
          }
        });

        path.push(new google.maps.LatLng(point.latitude, point.longitude));
      });

      if (routeDepot && route.route_points.length > 0) {
        path.push(new google.maps.LatLng(routeDepot.latitude, routeDepot.longitude));
      }

      if (path.length > 1) {
        new google.maps.Polyline({
          path: path,
          geodesic: true,
          strokeColor: color,
          strokeOpacity: 0.8,
          strokeWeight: 3,
          map: map
        });
      }
    });

    if (routes.length > 0 || depotLocations.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      
      depotLocations.forEach(depot => {
        bounds.extend(new google.maps.LatLng(depot.latitude, depot.longitude));
      });
      
      routes.forEach(route => {
        route.route_points.forEach(point => {
          bounds.extend(new google.maps.LatLng(point.latitude, point.longitude));
        });
      });
      
      map.fitBounds(bounds);
    }

  }, [map, routes, depotLocations, isLoaded]);

  return (
    <div 
      ref={mapRef} 
      className={`w-full h-full min-h-[400px] ${className || ''}`}
      style={{ minHeight: '400px' }}
    />
  );
};

export default GoogleMap;
