from __future__ import annotations

import heapq
import random
from typing import TYPE_CHECKING, Any

from .banking import available_funds, withdraw
from .justice import attempt_contact_violation, contact_forbidden
from .models import (
    Activity,
    CareStatus,
    Communication,
    CommunicationChannel,
    CommunicationStatus,
    CommunicationTone,
    TravelStage,
)
from .social import apply_interaction

if TYPE_CHECKING:
    from .models import Citizen
    from .world import World

MAX_COMMUNICATIONS = 2_000
MAX_CITIZEN_HISTORY = 120
MAX_REPLY_DEPTH = 2

CHANNEL_DELAYS = {
    CommunicationChannel.PHONE_CALL: (0, 0),
    CommunicationChannel.SMS: (1, 5),
    CommunicationChannel.EMAIL: (5, 30),
    CommunicationChannel.LETTER: (24 * 60, 3 * 24 * 60),
}
READ_DELAYS = {
    CommunicationChannel.SMS: (1, 20),
    CommunicationChannel.EMAIL: (20, 240),
    CommunicationChannel.LETTER: (30, 720),
}
CHANNEL_COSTS = {
    CommunicationChannel.PHONE_CALL: 0.30,
    CommunicationChannel.SMS: 0.05,
    CommunicationChannel.EMAIL: 0.0,
    CommunicationChannel.LETTER: 1.20,
}


def initialize_communications(world: World) -> None:
    world.communication_rng = random.Random(world.seed ^ 0xC011CA7E)
    world.communications: dict[int, Communication] = {}
    world.communication_queue: list[tuple[int, int]] = []
    world._next_communication_id = 1
    world._last_communication_slot = -1
    world.communications_sent_today = 0
    world.communications_delivered_today = 0
    world.phone_calls_today = 0
    world.communication_replies_today = 0
    for citizen in world.citizens.values():
        citizen.phone_number = citizen.phone_number or f"06 {citizen.id:02d} {world.seed % 100:02d} {(citizen.id * 17) % 100:02d} {(citizen.id * 31) % 100:02d}"
        slug = f"{citizen.first_name}.{citizen.last_name}".lower().replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a").replace("ç", "c")
        citizen.email_address = citizen.email_address or f"{slug}.{citizen.id}@ville.test"


def reset_communication_day(world: World) -> None:
    world.communications_sent_today = 0
    world.communications_delivered_today = 0
    world.phone_calls_today = 0
    world.communication_replies_today = 0


def update_communications(world: World) -> None:
    _process_due(world)
    daily_slot = {9: 0, 12: 1, 18: 2, 21: 3}.get(world.hour)
    slot = (world.day - 1) * 4 + daily_slot if daily_slot is not None else -1
    if slot >= 0 and slot != world._last_communication_slot and world.minute == 0:
        world._last_communication_slot = slot
        _plan_autonomous_communications(world)


def send_communication(
    world: World,
    *,
    sender_id: int,
    recipient_id: int,
    channel: CommunicationChannel,
    tone: CommunicationTone,
    subject: str,
    body: str,
    reply_to_id: int | None = None,
    reply_depth: int = 0,
    attempt_order_violation: bool = False,
) -> Communication:
    if sender_id == recipient_id:
        raise ValueError("Un habitant ne peut pas s’envoyer un message à lui-même.")
    sender = world.citizens[sender_id]
    recipient = world.citizens[recipient_id]
    violates_order = False
    if contact_forbidden(world, sender_id, recipient_id):
        if not attempt_order_violation or not attempt_contact_violation(world, sender_id, recipient_id):
            raise ValueError("Une interdiction de contact empêche cette communication.")
        violates_order = True
    _validate_channel(sender, recipient, channel)
    subject = subject.strip()[:120] or _default_subject(tone)
    body = body.strip()[:800] or _default_body(tone, sender, recipient)
    cost = CHANNEL_COSTS[channel]
    if available_funds(sender, allow_credit=True) < cost:
        raise ValueError("Fonds insuffisants pour utiliser ce canal.")
    withdraw(world, sender, cost, label=f"Communication {channel.value}", transaction_type="communication", allow_credit=True)
    low, high = CHANNEL_DELAYS[channel]
    delivery_tick = world.tick + (world.communication_rng.randint(low, high) if high else 0)
    communication = Communication(
        id=world._next_communication_id,
        thread_id=(world.communications[reply_to_id].thread_id if reply_to_id in world.communications else world._next_communication_id),
        sender_id=sender_id,
        recipient_id=recipient_id,
        channel=channel,
        tone=tone,
        subject=subject,
        body=body,
        status=CommunicationStatus.RINGING if channel == CommunicationChannel.PHONE_CALL else CommunicationStatus.QUEUED,
        created_tick=world.tick,
        delivery_tick=delivery_tick,
        reply_to_id=reply_to_id,
        reply_depth=reply_depth,
        cost=cost,
        violates_order=violates_order,
    )
    world._next_communication_id += 1
    world.communications[communication.id] = communication
    _record_for_citizen(sender, communication.id)
    _record_for_citizen(recipient, communication.id)
    heapq.heappush(world.communication_queue, (delivery_tick, communication.id))
    world.communications_sent_today += 1
    if channel == CommunicationChannel.PHONE_CALL:
        world.phone_calls_today += 1
    if reply_to_id in world.communications:
        world.communications[reply_to_id].status = CommunicationStatus.REPLIED
        world.communications[reply_to_id].replied_tick = world.tick
        world.communication_replies_today += 1
    world._emit(
        "communication_sent",
        f"{sender.full_name} contacte {recipient.full_name} par {_channel_label(channel)}.",
        citizen_ids=(sender.id, recipient.id),
        severity="warning" if tone == CommunicationTone.CONFLICT else "info",
    )
    _prune(world)
    return communication


def _process_due(world: World) -> None:
    while world.communication_queue and world.communication_queue[0][0] <= world.tick:
        _, communication_id = heapq.heappop(world.communication_queue)
        communication = world.communications.get(communication_id)
        if communication is None:
            continue
        if communication.status in {CommunicationStatus.QUEUED, CommunicationStatus.RINGING}:
            _deliver(world, communication)
        elif communication.status == CommunicationStatus.DELIVERED:
            _read(world, communication)


def _deliver(world: World, communication: Communication) -> None:
    sender = world.citizens[communication.sender_id]
    recipient = world.citizens[communication.recipient_id]
    if contact_forbidden(world, sender.id, recipient.id) and not communication.violates_order:
        communication.status = CommunicationStatus.FAILED
        communication.failure_reason = "Interdiction de contact active au moment de la livraison."
        return
    if communication.channel == CommunicationChannel.PHONE_CALL:
        if not _available_for_call(world, recipient):
            communication.status = CommunicationStatus.FAILED
            communication.failure_reason = "Appel manqué : destinataire indisponible."
            world._emit("phone_call_missed", f"{recipient.full_name} manque un appel de {sender.full_name}.", citizen_ids=(sender.id, recipient.id))
            return
        communication.duration_minutes = world.communication_rng.randint(3, 24)
        communication.status = CommunicationStatus.READ
        communication.read_tick = world.tick
        _apply_social_effect(world, communication)
        world.communications_delivered_today += 1
        world._emit("phone_call_completed", f"{sender.full_name} et {recipient.full_name} terminent un appel de {communication.duration_minutes} minutes.", citizen_ids=(sender.id, recipient.id))
        return
    communication.status = CommunicationStatus.DELIVERED
    world.communications_delivered_today += 1
    if communication.id not in recipient.unread_communication_ids:
        recipient.unread_communication_ids.append(communication.id)
    low, high = READ_DELAYS[communication.channel]
    heapq.heappush(world.communication_queue, (world.tick + world.communication_rng.randint(low, high), communication.id))
    world._emit("communication_delivered", f"Un {_channel_label(communication.channel)} de {sender.full_name} est livré à {recipient.full_name}.", citizen_ids=(sender.id, recipient.id))


def _read(world: World, communication: Communication) -> None:
    recipient = world.citizens[communication.recipient_id]
    if not _available_to_read(world, recipient):
        heapq.heappush(world.communication_queue, (world.tick + 30, communication.id))
        return
    communication.status = CommunicationStatus.READ
    communication.read_tick = world.tick
    if communication.id in recipient.unread_communication_ids:
        recipient.unread_communication_ids.remove(communication.id)
    _apply_social_effect(world, communication)
    if communication.reply_depth < MAX_REPLY_DEPTH and _should_reply(world, communication):
        reply_channel = communication.channel if communication.channel != CommunicationChannel.LETTER or world.communication_rng.random() < 0.72 else CommunicationChannel.SMS
        try:
            send_communication(
                world,
                sender_id=communication.recipient_id,
                recipient_id=communication.sender_id,
                channel=reply_channel,
                tone=_reply_tone(communication.tone),
                subject=f"Re: {communication.subject}",
                body=_reply_body(communication.tone, recipient),
                reply_to_id=communication.id,
                reply_depth=communication.reply_depth + 1,
            )
        except ValueError:
            pass


def _apply_social_effect(world: World, communication: Communication) -> None:
    sender = world.citizens[communication.sender_id]
    recipient = world.citizens[communication.recipient_id]
    positive = communication.tone != CommunicationTone.CONFLICT
    strength = {
        CommunicationChannel.PHONE_CALL: 1.4,
        CommunicationChannel.SMS: 0.6,
        CommunicationChannel.EMAIL: 0.8,
        CommunicationChannel.LETTER: 1.2,
    }[communication.channel]
    if communication.tone == CommunicationTone.APOLOGY:
        strength *= 1.35
    apply_interaction(world, sender, recipient, recipient.home_id, positive=positive, strength=strength, emit=False)
    if communication.tone == CommunicationTone.PRACTICAL:
        sender.needs.stress = max(0.0, sender.needs.stress - 0.4)
        recipient.needs.stress = max(0.0, recipient.needs.stress - 0.4)


def _plan_autonomous_communications(world: World) -> None:
    candidates = sorted(world.citizens.values(), key=lambda citizen: (-citizen.needs.social, citizen.id))
    created = 0
    for sender in candidates:
        if created >= max(2, len(world.citizens) // 20):
            break
        relationships = sorted(sender.relationships.values(), key=lambda relation: (relation.familiarity, relation.affection), reverse=True)
        recipients = [world.citizens[relation.other_id] for relation in relationships if relation.other_id in world.citizens]
        if not recipients:
            continue
        recipient = recipients[world.communication_rng.randrange(min(4, len(recipients)))]
        relation = sender.relationships[recipient.id]
        tone = CommunicationTone.CONFLICT if relation.affection < -12 and world.communication_rng.random() < 0.25 else CommunicationTone.APOLOGY if relation.conflict_level > 0 and world.communication_rng.random() < 0.35 else CommunicationTone.INVITATION if sender.needs.social > 55 else CommunicationTone.FRIENDLY
        channel = world.communication_rng.choices(
            [CommunicationChannel.PHONE_CALL, CommunicationChannel.SMS, CommunicationChannel.EMAIL, CommunicationChannel.LETTER],
            weights=[18, 48, 25, 9],
            k=1,
        )[0]
        try:
            send_communication(world, sender_id=sender.id, recipient_id=recipient.id, channel=channel, tone=tone, subject=_default_subject(tone), body=_default_body(tone, sender, recipient), attempt_order_violation=True)
        except ValueError:
            continue
        created += 1


def communication_summary(world: World, communication: Communication) -> dict[str, Any]:
    return {
        "id": communication.id,
        "threadId": communication.thread_id,
        "sender": world._citizen_ref(communication.sender_id),
        "recipient": world._citizen_ref(communication.recipient_id),
        "channel": communication.channel.value,
        "tone": communication.tone.value,
        "subject": communication.subject,
        "body": communication.body,
        "status": communication.status.value,
        "createdTick": communication.created_tick,
        "deliveryTick": communication.delivery_tick,
        "readTick": communication.read_tick,
        "repliedTick": communication.replied_tick,
        "replyToId": communication.reply_to_id,
        "replyDepth": communication.reply_depth,
        "durationMinutes": communication.duration_minutes,
        "cost": communication.cost,
        "failureReason": communication.failure_reason,
        "violatesOrder": communication.violates_order,
    }


def communication_overview(world: World) -> dict[str, Any]:
    return {
        "metrics": communication_metrics(world),
        "recent": [communication_summary(world, item) for item in sorted(world.communications.values(), key=lambda row: row.created_tick, reverse=True)[:30]],
    }


def communication_metrics(world: World) -> dict[str, int]:
    day_start = max(0, world.tick - (world.hour * 60 + world.minute))
    today = [item for item in world.communications.values() if item.created_tick >= day_start]
    return {
        "sentToday": len(today),
        "deliveredToday": sum(item.status in {CommunicationStatus.DELIVERED, CommunicationStatus.READ, CommunicationStatus.REPLIED} for item in today),
        "phoneCallsToday": sum(item.channel == CommunicationChannel.PHONE_CALL for item in today),
        "smsToday": sum(item.channel == CommunicationChannel.SMS for item in today),
        "emailsToday": sum(item.channel == CommunicationChannel.EMAIL for item in today),
        "lettersToday": sum(item.channel == CommunicationChannel.LETTER for item in today),
        "unreadCommunications": sum(len(citizen.unread_communication_ids) for citizen in world.citizens.values()),
        "communicationRepliesToday": world.communication_replies_today,
    }


def citizen_communications(world: World, citizen_id: int) -> dict[str, Any]:
    citizen = world.citizens[citizen_id]
    rows = [world.communications[item_id] for item_id in citizen.communication_ids if item_id in world.communications]
    return {
        "phoneNumber": citizen.phone_number,
        "emailAddress": citizen.email_address,
        "unreadCount": len(citizen.unread_communication_ids),
        "messages": [communication_summary(world, item) for item in sorted(rows, key=lambda row: row.created_tick, reverse=True)[:MAX_CITIZEN_HISTORY]],
    }


def _available_for_call(world: World, citizen: Citizen) -> bool:
    return (
        citizen.detained_until_tick is None or world.tick >= citizen.detained_until_tick
    ) and citizen.care_status in {CareStatus.NONE, CareStatus.RECOVERING} and citizen.activity not in {Activity.SLEEPING, Activity.WORKING, Activity.DRIVING, Activity.RIDING_BUS, Activity.IN_TREATMENT, Activity.HOSPITALIZED}


def _available_to_read(world: World, citizen: Citizen) -> bool:
    return citizen.travel_stage == TravelStage.IDLE and citizen.activity not in {Activity.SLEEPING, Activity.WORKING, Activity.DETAINED, Activity.IN_TREATMENT, Activity.HOSPITALIZED}


def _should_reply(world: World, communication: Communication) -> bool:
    recipient = world.citizens[communication.recipient_id]
    relation = recipient.relationships.get(communication.sender_id)
    base = 0.62 if communication.tone in {CommunicationTone.PRACTICAL, CommunicationTone.INVITATION, CommunicationTone.APOLOGY} else 0.48
    if relation is not None:
        base += relation.trust / 250.0 + relation.affection / 300.0 - relation.conflict_level * 0.08
    return world.communication_rng.random() < max(0.08, min(0.88, base))


def _validate_channel(sender: Citizen, recipient: Citizen, channel: CommunicationChannel) -> None:
    if channel in {CommunicationChannel.PHONE_CALL, CommunicationChannel.SMS} and (not sender.phone_number or not recipient.phone_number):
        raise ValueError("Les deux habitants doivent disposer d’un téléphone.")
    if channel == CommunicationChannel.EMAIL and (not sender.email_address or not recipient.email_address):
        raise ValueError("Les deux habitants doivent disposer d’une adresse e-mail.")
    if channel == CommunicationChannel.LETTER and (sender.home_id <= 0 or recipient.home_id <= 0):
        raise ValueError("Une adresse postale est nécessaire pour envoyer une lettre.")


def _record_for_citizen(citizen: Citizen, communication_id: int) -> None:
    citizen.communication_ids.append(communication_id)
    citizen.communication_ids[:] = citizen.communication_ids[-MAX_CITIZEN_HISTORY:]


def _prune(world: World) -> None:
    if len(world.communications) <= MAX_COMMUNICATIONS:
        return
    pending = {CommunicationStatus.QUEUED, CommunicationStatus.RINGING, CommunicationStatus.DELIVERED}
    for communication_id in sorted(world.communications, key=lambda item_id: world.communications[item_id].created_tick):
        if len(world.communications) <= MAX_COMMUNICATIONS:
            break
        if world.communications[communication_id].status in pending:
            continue
        del world.communications[communication_id]
        for citizen in world.citizens.values():
            if communication_id in citizen.communication_ids:
                citizen.communication_ids.remove(communication_id)
            if communication_id in citizen.unread_communication_ids:
                citizen.unread_communication_ids.remove(communication_id)


def _default_subject(tone: CommunicationTone) -> str:
    return {
        CommunicationTone.FRIENDLY: "Prendre des nouvelles",
        CommunicationTone.PRACTICAL: "Organisation",
        CommunicationTone.APOLOGY: "Mes excuses",
        CommunicationTone.INVITATION: "Une proposition de sortie",
        CommunicationTone.CONFLICT: "À propos de notre différend",
    }[tone]


def _default_body(tone: CommunicationTone, sender: Citizen, recipient: Citizen) -> str:
    return {
        CommunicationTone.FRIENDLY: f"Bonjour {recipient.first_name}, comment vas-tu ?",
        CommunicationTone.PRACTICAL: f"Bonjour {recipient.first_name}, pouvons-nous nous organiser aujourd’hui ?",
        CommunicationTone.APOLOGY: f"Bonjour {recipient.first_name}, je regrette notre dernier différend.",
        CommunicationTone.INVITATION: f"Bonjour {recipient.first_name}, aimerais-tu que nous nous retrouvions bientôt ?",
        CommunicationTone.CONFLICT: f"{recipient.first_name}, nous devons reparler de ce qui s’est passé.",
    }[tone]


def _reply_tone(tone: CommunicationTone) -> CommunicationTone:
    return CommunicationTone.PRACTICAL if tone == CommunicationTone.CONFLICT else CommunicationTone.FRIENDLY


def _reply_body(original_tone: CommunicationTone, sender: Citizen) -> str:
    return "Je préfère que nous en parlions calmement." if original_tone == CommunicationTone.CONFLICT else f"Merci pour ton message. À bientôt, {sender.first_name}."


def _channel_label(channel: CommunicationChannel) -> str:
    return {
        CommunicationChannel.PHONE_CALL: "téléphone",
        CommunicationChannel.SMS: "SMS",
        CommunicationChannel.EMAIL: "e-mail",
        CommunicationChannel.LETTER: "lettre",
    }[channel]