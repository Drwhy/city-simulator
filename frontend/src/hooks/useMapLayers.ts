import { useCallback, useState } from "react";

export interface MapLayers {
  citizens: boolean;
  buildings: boolean;
  roads: boolean;
  vehicles: boolean;
  transit: boolean;
  traffic: boolean;
  incidents: boolean;
  social: boolean;
  health: boolean;
  emergencies: boolean;
  ambulances: boolean;
  medicalFacilities: boolean;
}

export const DEFAULT_MAP_LAYERS: Readonly<MapLayers> = Object.freeze({
  citizens: true,
  buildings: true,
  roads: true,
  vehicles: true,
  transit: true,
  traffic: true,
  incidents: true,
  social: true,
  health: true,
  emergencies: true,
  ambulances: true,
  medicalFacilities: true,
});

export function updateMapLayer(
  layers: MapLayers,
  key: keyof MapLayers,
  enabled: boolean,
): MapLayers {
  return { ...layers, [key]: enabled };
}

export function useMapLayers() {
  const [layers, setLayers] = useState<MapLayers>({ ...DEFAULT_MAP_LAYERS });
  const toggleLayer = useCallback((key: keyof MapLayers, enabled: boolean) => {
    setLayers((current) => updateMapLayer(current, key, enabled));
  }, []);
  return { layers, toggleLayer };
}