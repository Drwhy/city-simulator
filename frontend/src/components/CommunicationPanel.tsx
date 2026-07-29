import { useEffect, useState } from "react";
import { sendCommunication } from "../api";
import type { CitizenDetail, CommunicationChannel, CommunicationTone } from "../types/city";
import "./Communications.css";

const CHANNELS: Array<[CommunicationChannel, string]> = [["phone_call", "Téléphone"], ["sms", "SMS"], ["email", "E-mail"], ["letter", "Lettre"]];
const TONES: Array<[CommunicationTone, string]> = [["friendly", "Amical"], ["practical", "Pratique"], ["apology", "Excuses"], ["invitation", "Invitation"], ["conflict", "Conflictuel"]];
export const channelLabel = (channel: CommunicationChannel) => CHANNELS.find(([value]) => value === channel)?.[1] ?? channel;
export const statusLabel = (status: string) => ({ queued: "En transit", ringing: "Appel en cours", delivered: "Livré", read: "Lu", replied: "Répondu", failed: "Échec" }[status] ?? status);

export function CommunicationPanel({ citizen, onSelectCitizen }: { citizen: CitizenDetail; onSelectCitizen: (id: number) => void }) {
  const contacts = citizen.relationships.filter((row) => row.citizenId !== citizen.id);
  const [recipientId, setRecipientId] = useState(contacts[0]?.citizenId ?? 0);
  const [channel, setChannel] = useState<CommunicationChannel>("sms");
  const [tone, setTone] = useState<CommunicationTone>("friendly");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [feedback, setFeedback] = useState("");
  const [sending, setSending] = useState(false);
  useEffect(() => { if (!contacts.some((row) => row.citizenId === recipientId)) setRecipientId(contacts[0]?.citizenId ?? 0); }, [citizen.id, contacts.length]);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setSending(true); setFeedback("");
    try { await sendCommunication({ senderId: citizen.id, recipientId, channel, tone, subject, body }); setBody(""); setSubject(""); setFeedback("Communication enregistrée dans la simulation."); }
    catch (error) { setFeedback(error instanceof Error ? error.message : "Envoi impossible."); }
    finally { setSending(false); }
  }
  return <div className="communication-layout">
    <section className="profile-section communication-compose"><h3>Nouveau contact</h3>
      <dl className="profile-facts"><div><dt>Téléphone</dt><dd>{citizen.communications.phoneNumber}</dd></div><div><dt>E-mail</dt><dd>{citizen.communications.emailAddress}</dd></div><div><dt>Non lus</dt><dd>{citizen.communications.unreadCount}</dd></div></dl>
      <form onSubmit={submit}>
        <label>Destinataire<select value={recipientId} onChange={(event) => setRecipientId(Number(event.target.value))}>{contacts.map((row) => <option key={row.citizenId} value={row.citizenId}>{row.name}</option>)}</select></label>
        <div className="communication-form-row"><label>Canal<select value={channel} onChange={(event) => setChannel(event.target.value as CommunicationChannel)}>{CHANNELS.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Ton<select value={tone} onChange={(event) => setTone(event.target.value as CommunicationTone)}>{TONES.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
        <label>Objet<input maxLength={120} value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Objet facultatif" /></label>
        <label>Contenu<textarea maxLength={800} value={body} onChange={(event) => setBody(event.target.value)} placeholder="Le moteur complétera un contenu vide selon le ton." /></label>
        <button disabled={sending || recipientId === 0}>{sending ? "Envoi…" : `Envoyer par ${channelLabel(channel)}`}</button>{feedback && <p className="communication-feedback">{feedback}</p>}
      </form>
    </section>
    <section className="profile-section communication-history"><h3>Historique</h3>{citizen.communications.messages.length === 0 ? <p className="muted">Aucune communication enregistrée.</p> : citizen.communications.messages.map((message) => {
      const incoming = message.recipient.id === citizen.id; const other = incoming ? message.sender : message.recipient;
      return <article className={`communication-row communication-${message.status}`} key={message.id}><header><span>{incoming ? "Reçu de" : "Envoyé à"} <button onClick={() => onSelectCitizen(other.id)}>{other.name}</button></span><b>{channelLabel(message.channel)} · {statusLabel(message.status)}</b></header><strong>{message.subject}</strong><p>{message.body}</p>{message.durationMinutes > 0 && <small>Durée : {message.durationMinutes} min</small>}{message.failureReason && <small className="communication-error">{message.failureReason}</small>}</article>;
    })}</section>
  </div>;
}
