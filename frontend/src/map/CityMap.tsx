import { useEffect, useRef } from "react";
import { Application, Container, Graphics, Text, TextStyle } from "pixi.js";
import type {
  BuildingSummary,
  CitizenSummary,
  CitySnapshot,
  SelectedEntity,
  VehicleSummary,
} from "../types/city";

interface CityMapProps {
  snapshot: CitySnapshot | null;
  selectedEntity: SelectedEntity | null;
  onSelectCitizen: (citizenId: number) => void;
  onSelectVehicle: (vehicleId: number) => void;
  onSelectIncident: (incidentId: number) => void;
  onSelectBuilding: (buildingId: number) => void;
  showCitizens: boolean;
  showBuildings: boolean;
  showRoads: boolean;
  showVehicles: boolean;
  showTransit: boolean;
  showTraffic: boolean;
  showIncidents: boolean;
  showSocial: boolean;
  selectedRelationships: Array<{ citizenId: number; status: string; affection: number }>;
}

interface CitizenVisualState {
  activity: string;
  selected: boolean;
}

interface VehicleVisualState {
  type: string;
  status: string;
  occupancy: number;
  selected: boolean;
}

interface SceneState {
  world: Container;
  background: Graphics;
  grid: Graphics;
  roadsLayer: Container;
  transitLayer: Container;
  trafficLayer: Container;
  buildingsLayer: Container;
  socialLayer: Container;
  vehiclesLayer: Container;
  citizensLayer: Container;
  incidentsLayer: Container;
  citizens: Map<number, Graphics>;
  vehicles: Map<number, Graphics>;
  citizenVisualStates: Map<number, CitizenVisualState>;
  vehicleVisualStates: Map<number, VehicleVisualState>;
  mapWidth: number;
  mapHeight: number;
  buildingSignature: string;
  roadSignature: string;
  transitSignature: string;
}

const CELL_SIZE = 22;
const ACTIVITY_COLORS: Record<string, number> = {
  sleeping: 0x8b8f9a,
  working: 0x43a267,
  walking: 0x4b9fea,
  driving: 0x4b9fea,
  waiting_bus: 0x5dc3c7,
  riding_bus: 0x5dc3c7,
  eating: 0xe9b949,
  relaxing: 0xbb78e8,
  at_home: 0xb5bac7,
  detained: 0xe05f6b,
  shopping: 0xf0c45c,
};

const BUILDING_COLORS: Record<string, number> = {
  home: 0x4d5669,
  office: 0x436e9f,
  factory: 0x73584a,
  shop: 0x4f8b6d,
  cafe: 0xa76d49,
  park: 0x397a4c,
  public: 0x8067a6,
  police: 0x315d87,
};

function destroyChildren(container: Container): void {
  const children = container.removeChildren();
  children.forEach((child) => child.destroy({ children: true }));
}

function drawBuilding(layer: Container, building: BuildingSummary, onSelect: (id: number) => void): void {
  const graphics = new Graphics();
  graphics.beginFill(BUILDING_COLORS[building.type] ?? 0x555b66, 0.95);
  graphics.lineStyle(1, 0xd7dbe3, 0.3);
  graphics.drawRoundedRect(
    building.x * CELL_SIZE,
    building.y * CELL_SIZE,
    building.width * CELL_SIZE,
    building.height * CELL_SIZE,
    4,
  );
  graphics.endFill();
  graphics.eventMode = "static";
  graphics.cursor = "pointer";
  graphics.on("pointertap", () => onSelect(building.id));
  layer.addChild(graphics);

  const label = new Text(
    building.name,
    new TextStyle({
      fontFamily: "Arial",
      fontSize: 10,
      fill: 0xf3f5f8,
      wordWrap: true,
      wordWrapWidth: Math.max(65, building.width * CELL_SIZE),
      align: "center",
    }),
  );
  label.anchor.set(0.5);
  label.x = (building.x + building.width / 2) * CELL_SIZE;
  label.y = (building.y + building.height / 2) * CELL_SIZE;
  layer.addChild(label);
}

function drawCitizenGraphic(graphics: Graphics, citizen: CitizenSummary, selected: boolean): void {
  graphics.clear();
  graphics.lineStyle(selected ? 3 : 1, selected ? 0xffffff : 0x0e1015, selected ? 1 : 0.8);
  graphics.beginFill(ACTIVITY_COLORS[citizen.activity] ?? 0xffffff, 1);
  const radius = citizen.activeVehicleId ? 3.5 : selected ? 7 : 5;
  graphics.drawCircle(0, 0, radius);
  graphics.endFill();
}

function drawVehicleGraphic(graphics: Graphics, vehicle: VehicleSummary, selected: boolean): void {
  graphics.clear();
  const isBus = vehicle.type === "bus";
  const isPolice = vehicle.type === "police";
  const fill = isBus
    ? 0x52c7cf
    : isPolice
      ? vehicle.status === "on_scene" ? 0x4f8fd8 : 0x3f75b5
      : vehicle.status === "parked" ? 0x778394 : 0xf0a654;
  graphics.lineStyle(selected ? 3 : 1, selected ? 0xffffff : 0x10141b, 1);
  graphics.beginFill(fill, vehicle.status === "parked" ? 0.75 : 1);
  graphics.drawRoundedRect(
    isBus ? -9 : -6,
    isBus ? -5 : -4,
    isBus ? 18 : 12,
    isBus ? 10 : 8,
    2,
  );
  graphics.endFill();
  if (isBus) {
    graphics.beginFill(0x17222b, 0.9);
    graphics.drawRect(-5, -3, 4, 3);
    graphics.drawRect(2, -3, 4, 3);
    graphics.endFill();
  } else if (isPolice) {
    graphics.beginFill(0xdcecff, 0.95);
    graphics.drawRect(-2, -5, 4, 2);
    graphics.endFill();
  }
}

function createScene(app: Application): SceneState {
  const world = new Container();
  const background = new Graphics();
  const grid = new Graphics();
  const roadsLayer = new Container();
  const transitLayer = new Container();
  const trafficLayer = new Container();
  const buildingsLayer = new Container();
  const socialLayer = new Container();
  const vehiclesLayer = new Container();
  const citizensLayer = new Container();
  const incidentsLayer = new Container();

  world.addChild(
    background,
    grid,
    roadsLayer,
    transitLayer,
    trafficLayer,
    buildingsLayer,
    socialLayer,
    vehiclesLayer,
    citizensLayer,
    incidentsLayer,
  );
  app.stage.addChild(world);

  return {
    world,
    background,
    grid,
    roadsLayer,
    transitLayer,
    trafficLayer,
    buildingsLayer,
    socialLayer,
    vehiclesLayer,
    citizensLayer,
    incidentsLayer,
    citizens: new Map(),
    vehicles: new Map(),
    citizenVisualStates: new Map(),
    vehicleVisualStates: new Map(),
    mapWidth: 0,
    mapHeight: 0,
    buildingSignature: "",
    roadSignature: "",
    transitSignature: "",
  };
}

function updateMapGeometry(scene: SceneState, width: number, height: number): void {
  if (scene.mapWidth === width && scene.mapHeight === height) return;

  scene.mapWidth = width;
  scene.mapHeight = height;
  const worldWidth = width * CELL_SIZE;
  const worldHeight = height * CELL_SIZE;

  scene.background.clear();
  scene.background.beginFill(0x171c25);
  scene.background.drawRect(0, 0, worldWidth, worldHeight);
  scene.background.endFill();

  scene.grid.clear();
  scene.grid.lineStyle(1, 0x2b3340, 0.22);
  for (let x = 0; x <= width; x += 1) {
    scene.grid.moveTo(x * CELL_SIZE, 0);
    scene.grid.lineTo(x * CELL_SIZE, worldHeight);
  }
  for (let y = 0; y <= height; y += 1) {
    scene.grid.moveTo(0, y * CELL_SIZE);
    scene.grid.lineTo(worldWidth, y * CELL_SIZE);
  }
}

function fitWorld(app: Application, scene: SceneState): void {
  if (scene.mapWidth === 0 || scene.mapHeight === 0) return;

  const worldWidth = scene.mapWidth * CELL_SIZE;
  const worldHeight = scene.mapHeight * CELL_SIZE;
  const availableWidth = app.renderer.width / app.renderer.resolution;
  const availableHeight = app.renderer.height / app.renderer.resolution;
  const scale = Math.min(availableWidth / worldWidth, availableHeight / worldHeight) * 0.96;

  scene.world.scale.set(scale);
  scene.world.x = (availableWidth - worldWidth * scale) / 2;
  scene.world.y = (availableHeight - worldHeight * scale) / 2;
}

function buildingSignature(buildings: BuildingSummary[]): string {
  return buildings
    .map((building) => [
      building.id,
      building.name,
      building.type,
      building.x,
      building.y,
      building.width,
      building.height,
    ].join(":"))
    .join("|");
}

function drawRoads(scene: SceneState, snapshot: CitySnapshot): void {
  const signature = `${snapshot.map.width}:${snapshot.map.height}:${snapshot.roads.cells.length}`;
  if (signature === scene.roadSignature) return;
  destroyChildren(scene.roadsLayer);
  const roads = new Graphics();
  roads.beginFill(0x303845, 0.9);
  snapshot.roads.cells.forEach((cell) => {
    roads.drawRect(cell.x * CELL_SIZE, cell.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
  });
  roads.endFill();
  roads.lineStyle(1, 0x4a5566, 0.25);
  snapshot.roads.cells.forEach((cell) => {
    roads.drawRect(cell.x * CELL_SIZE, cell.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
  });
  scene.roadsLayer.addChild(roads);
  scene.roadSignature = signature;
}

function drawTransit(scene: SceneState, snapshot: CitySnapshot): void {
  const line = snapshot.transport.busLines[0];
  if (!line) return;
  const signature = `${line.id}:${line.route.length}:${snapshot.transport.busStops.length}`;
  if (signature === scene.transitSignature) return;
  destroyChildren(scene.transitLayer);

  const route = new Graphics();
  route.lineStyle(3, 0x58c6cc, 0.55);
  line.route.forEach((cell, index) => {
    const x = cell.x * CELL_SIZE + CELL_SIZE / 2;
    const y = cell.y * CELL_SIZE + CELL_SIZE / 2;
    if (index === 0) route.moveTo(x, y);
    else route.lineTo(x, y);
  });
  scene.transitLayer.addChild(route);

  snapshot.transport.busStops.forEach((stop) => {
    const marker = new Graphics();
    marker.lineStyle(2, 0xd9ffff, 0.9);
    marker.beginFill(0x2e858b, 1);
    marker.drawCircle(0, 0, 6);
    marker.endFill();
    marker.x = stop.x * CELL_SIZE + CELL_SIZE / 2;
    marker.y = stop.y * CELL_SIZE + CELL_SIZE / 2;
    scene.transitLayer.addChild(marker);
  });
  scene.transitSignature = signature;
}

function drawTraffic(scene: SceneState, snapshot: CitySnapshot): void {
  destroyChildren(scene.trafficLayer);
  snapshot.roads.congestion.forEach((cell) => {
    const marker = new Graphics();
    marker.beginFill(cell.level === "heavy" ? 0xe4555f : 0xe2a43f, 0.72);
    marker.drawRect(cell.x * CELL_SIZE + 3, cell.y * CELL_SIZE + 3, CELL_SIZE - 6, CELL_SIZE - 6);
    marker.endFill();
    scene.trafficLayer.addChild(marker);
  });
}

function drawSocialLinks(
  scene: SceneState,
  snapshot: CitySnapshot,
  selectedEntity: SelectedEntity | null,
  relationships: Array<{ citizenId: number; status: string; affection: number }>,
): void {
  destroyChildren(scene.socialLayer);
  if (selectedEntity?.kind !== "citizen") return;
  const selected = snapshot.citizens.find((citizen) => citizen.id === selectedEntity.id);
  if (!selected) return;

  relationships.slice(0, 8).forEach((relationship) => {
    const other = snapshot.citizens.find((citizen) => citizen.id === relationship.citizenId);
    if (!other) return;
    const line = new Graphics();
    const color = relationship.status === "rival"
      ? 0xd95c65
      : relationship.status === "close_friend"
        ? 0xb976d8
        : relationship.status === "friend"
          ? 0x57b77a
          : 0x718096;
    const alpha = relationship.status === "acquaintance" ? 0.28 : 0.68;
    line.lineStyle(relationship.status === "close_friend" ? 3 : 2, color, alpha);
    line.moveTo(selected.x * CELL_SIZE + CELL_SIZE / 2, selected.y * CELL_SIZE + CELL_SIZE / 2);
    line.lineTo(other.x * CELL_SIZE + CELL_SIZE / 2, other.y * CELL_SIZE + CELL_SIZE / 2);
    scene.socialLayer.addChild(line);
  });

  snapshot.social.events.forEach((event) => {
    event.participants.forEach((participant) => {
      const citizen = snapshot.citizens.find((row) => row.id === participant.id);
      if (!citizen) return;
      const ring = new Graphics();
      ring.lineStyle(2, event.status === "active" ? 0xf4cf67 : 0xb976d8, 0.85);
      ring.drawCircle(0, 0, 9);
      ring.x = citizen.x * CELL_SIZE + CELL_SIZE / 2;
      ring.y = citizen.y * CELL_SIZE + CELL_SIZE / 2;
      scene.socialLayer.addChild(ring);
    });
  });
}

export function CityMap({
  snapshot,
  selectedEntity,
  onSelectCitizen,
  onSelectVehicle,
  onSelectIncident,
  onSelectBuilding,
  showCitizens,
  showBuildings,
  showRoads,
  showVehicles,
  showTransit,
  showTraffic,
  showIncidents,
  showSocial,
  selectedRelationships,
}: CityMapProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const appRef = useRef<Application | null>(null);
  const sceneRef = useRef<SceneState | null>(null);
  const onSelectCitizenRef = useRef(onSelectCitizen);
  const onSelectVehicleRef = useRef(onSelectVehicle);
  const onSelectIncidentRef = useRef(onSelectIncident);
  const onSelectBuildingRef = useRef(onSelectBuilding);

  onSelectCitizenRef.current = onSelectCitizen;
  onSelectVehicleRef.current = onSelectVehicle;
  onSelectIncidentRef.current = onSelectIncident;
  onSelectBuildingRef.current = onSelectBuilding;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const app = new Application({
      backgroundColor: 0x11151d,
      antialias: true,
      resizeTo: host,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      autoDensity: true,
    });
    host.appendChild(app.view as HTMLCanvasElement);
    appRef.current = app;
    sceneRef.current = createScene(app);

    const resizeObserver = new ResizeObserver(() => {
      app.renderer.resize(host.clientWidth, host.clientHeight);
      if (sceneRef.current) fitWorld(app, sceneRef.current);
    });
    resizeObserver.observe(host);

    return () => {
      resizeObserver.disconnect();
      app.destroy(true, { children: true, texture: true, baseTexture: true });
      appRef.current = null;
      sceneRef.current = null;
    };
  }, []);

  useEffect(() => {
    const app = appRef.current;
    const scene = sceneRef.current;
    if (!app || !scene || !snapshot) return;

    updateMapGeometry(scene, snapshot.map.width, snapshot.map.height);
    drawRoads(scene, snapshot);
    drawTransit(scene, snapshot);
    drawTraffic(scene, snapshot);
    scene.roadsLayer.visible = showRoads;
    scene.transitLayer.visible = showTransit;
    scene.trafficLayer.visible = showTraffic;

    const nextBuildingSignature = buildingSignature(snapshot.buildings);
    if (scene.buildingSignature !== nextBuildingSignature) {
      destroyChildren(scene.buildingsLayer);
      snapshot.buildings.forEach((building) => drawBuilding(scene.buildingsLayer, building, (id) => onSelectBuildingRef.current(id)));
      scene.buildingSignature = nextBuildingSignature;
    }
    scene.buildingsLayer.visible = showBuildings;

    drawSocialLinks(scene, snapshot, selectedEntity, selectedRelationships);
    scene.socialLayer.visible = showSocial;

    const selectedCitizenVehicleId = selectedEntity?.kind === "citizen"
      ? snapshot.citizens.find((citizen) => citizen.id === selectedEntity.id)?.activeVehicleId ?? null
      : null;

    const visibleVehicleIds = new Set<number>();
    snapshot.vehicles.forEach((vehicle) => {
      visibleVehicleIds.add(vehicle.id);
      let graphics = scene.vehicles.get(vehicle.id);
      if (!graphics) {
        graphics = new Graphics();
        graphics.eventMode = "static";
        graphics.cursor = "pointer";
        graphics.on("pointertap", () => onSelectVehicleRef.current(vehicle.id));
        scene.vehicles.set(vehicle.id, graphics);
        scene.vehiclesLayer.addChild(graphics);
      }
      const selected = (selectedEntity?.kind === "vehicle" && selectedEntity.id === vehicle.id)
        || selectedCitizenVehicleId === vehicle.id;
      const previous = scene.vehicleVisualStates.get(vehicle.id);
      if (
        !previous
        || previous.type !== vehicle.type
        || previous.status !== vehicle.status
        || previous.occupancy !== vehicle.occupancy
        || previous.selected !== selected
      ) {
        drawVehicleGraphic(graphics, vehicle, selected);
        scene.vehicleVisualStates.set(vehicle.id, {
          type: vehicle.type,
          status: vehicle.status,
          occupancy: vehicle.occupancy,
          selected,
        });
      }
      const parkedOffset = vehicle.type === "car" && vehicle.status === "parked"
        ? ((vehicle.id % 3) - 1) * 3
        : 0;
      graphics.x = vehicle.x * CELL_SIZE + CELL_SIZE / 2 + parkedOffset;
      graphics.y = vehicle.y * CELL_SIZE + CELL_SIZE / 2 + (vehicle.status === "parked" ? 4 : 0);
    });
    scene.vehicles.forEach((graphics, vehicleId) => {
      if (visibleVehicleIds.has(vehicleId)) return;
      scene.vehicles.delete(vehicleId);
      scene.vehicleVisualStates.delete(vehicleId);
      graphics.destroy();
    });
    scene.vehiclesLayer.visible = showVehicles;

    const visibleCitizenIds = new Set<number>();
    snapshot.citizens.forEach((citizen) => {
      visibleCitizenIds.add(citizen.id);
      let graphics = scene.citizens.get(citizen.id);
      if (!graphics) {
        graphics = new Graphics();
        graphics.eventMode = "static";
        graphics.cursor = "pointer";
        graphics.on("pointertap", () => onSelectCitizenRef.current(citizen.id));
        scene.citizens.set(citizen.id, graphics);
        scene.citizensLayer.addChild(graphics);
      }

      const selected = selectedEntity?.kind === "citizen" && selectedEntity.id === citizen.id;
      const previous = scene.citizenVisualStates.get(citizen.id);
      if (!previous || previous.activity !== citizen.activity || previous.selected !== selected) {
        drawCitizenGraphic(graphics, citizen, selected);
        scene.citizenVisualStates.set(citizen.id, { activity: citizen.activity, selected });
      }

      graphics.x = citizen.x * CELL_SIZE + CELL_SIZE / 2;
      graphics.y = citizen.y * CELL_SIZE + CELL_SIZE / 2;
      graphics.visible = citizen.activeVehicleId === null;
    });
    scene.citizens.forEach((graphics, citizenId) => {
      if (visibleCitizenIds.has(citizenId)) return;
      scene.citizens.delete(citizenId);
      scene.citizenVisualStates.delete(citizenId);
      graphics.destroy();
    });
    scene.citizensLayer.visible = showCitizens;

    destroyChildren(scene.incidentsLayer);
    if (showIncidents) {
      snapshot.incidents.forEach((incident) => {
        const selected = selectedEntity?.kind === "incident" && selectedEntity.id === incident.id;
        const marker = new Graphics();
        marker.eventMode = "static";
        marker.cursor = "pointer";
        marker.lineStyle(selected ? 3 : 1, selected ? 0xffffff : 0x151922, 1);
        marker.beginFill(incident.severity === "danger" ? 0xf05d5e : 0xf4b942, 0.98);
        const radius = selected ? 12 : 9;
        marker.drawPolygon([0, -radius, radius, radius - 1, -radius, radius - 1]);
        marker.endFill();
        if (incident.reported) {
          marker.beginFill(0xeaf4ff, 0.95);
          marker.drawCircle(0, 2, 2.4);
          marker.endFill();
        }
        marker.x = incident.x * CELL_SIZE + CELL_SIZE / 2;
        marker.y = incident.y * CELL_SIZE - 8;
        marker.on("pointertap", () => onSelectIncidentRef.current(incident.id));
        scene.incidentsLayer.addChild(marker);
      });
    }
    scene.incidentsLayer.visible = showIncidents;

    fitWorld(app, scene);
  }, [
    snapshot,
    selectedEntity,
    showBuildings,
    showCitizens,
    showIncidents,
    showRoads,
    showSocial,
    selectedRelationships,
    showTraffic,
    showTransit,
    showVehicles,
  ]);

  return <div className="city-map" ref={hostRef} />;
}
