import type { MouseEvent } from "react";
import type { InspectorEntity } from "../types/city";
import { Inspector } from "./Inspector";

interface EntityModalProps {
  entity: InspectorEntity | null;
  loading: boolean;
  refreshing: boolean;
  paused: boolean;
  onClose: () => void;
  onSelectCitizen: (id: number) => void;
  onSelectVehicle: (id: number) => void;
  onSelectIncident: (id: number) => void;
  onSelectHousehold: (id: number) => void;
}

export function EntityModal(props: EntityModalProps) {
  if (!props.loading && props.entity === null) return null;
  return (
    <div className="entity-modal-overlay" role="dialog" aria-modal="true" onMouseDown={props.onClose}>
      <section className="entity-modal-window" onMouseDown={(event: MouseEvent<HTMLElement>) => event.stopPropagation()}>
        <button className="entity-modal-close" onClick={props.onClose}>Fermer</button>
        <Inspector
          entity={props.entity}
          loading={props.loading}
          refreshing={props.refreshing}
          paused={props.paused}
          standalone
          onSelectCitizen={props.onSelectCitizen}
          onSelectVehicle={props.onSelectVehicle}
          onSelectIncident={props.onSelectIncident}
          onSelectHousehold={props.onSelectHousehold}
        />
      </section>
    </div>
  );
}
