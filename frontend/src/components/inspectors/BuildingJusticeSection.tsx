import type { BuildingDetail } from "../../types/city";

interface BuildingJusticeSectionProps {
  justice: NonNullable<BuildingDetail["justice"]>;
  onSelectCitizen: (citizenId: number) => void;
}

export function BuildingJusticeSection({ justice, onSelectCitizen }: BuildingJusticeSectionProps) {
  if (justice.institutionType === "court") {
    return (
      <>
        <h3>Monitoring du tribunal</h3>
        <dl className="facts">
          <div><dt>Audiences du jour</dt><dd>{justice.hearingsToday} / {justice.dailyCapacity}</dd></div>
          <div><dt>Dossiers en attente</dt><dd>{justice.queue.length}</dd></div>
        </dl>
        <div className="justice-list">
          {justice.queue.map((row) => (
            <article key={row.id}>
              <strong>Dossier #{row.id}</strong>
              <span>{row.defendantName} · priorité {row.priority} · {Math.round(row.evidenceScore)} %</span>
            </article>
          ))}
        </div>
      </>
    );
  }
  return (
    <>
      <h3>Monitoring de la détention</h3>
      <dl className="facts">
        <div><dt>Occupation</dt><dd>{justice.detained.length} / {justice.capacity}</dd></div>
        <div><dt>Peines actives suivies</dt><dd>{justice.activeSentences.length}</dd></div>
      </dl>
      <div className="passenger-list">
        {justice.detained.filter((person): person is { id: number; name: string } => person !== null).map((person) => (
          <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>
        ))}
      </div>
    </>
  );
}