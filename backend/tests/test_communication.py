from fastapi.testclient import TestClient

from app.main import app, service
from app.simulation.communication import MAX_REPLY_DEPTH, send_communication
from app.simulation.models import Activity, CommunicationChannel, CommunicationStatus, CommunicationTone, JudicialSentence, SentenceStatus, SentenceType, TravelStage
from app.simulation.world import World


def _available(world: World, citizen_id: int) -> None:
    citizen = world.citizens[citizen_id]
    citizen.activity = Activity.AT_HOME
    citizen.travel_stage = TravelStage.IDLE
    citizen.detained_until_tick = None


def test_phone_call_completes_immediately_and_changes_relationship() -> None:
    world = World(seed=7101, citizen_count=20)
    _available(world, 2)
    before = world.citizens[2].relationships[1].affection
    call = send_communication(world, sender_id=1, recipient_id=2, channel=CommunicationChannel.PHONE_CALL, tone=CommunicationTone.FRIENDLY, subject="Nouvelles", body="Comment vas-tu ?")
    world.run_minutes(1)
    assert call.status == CommunicationStatus.READ
    assert call.duration_minutes >= 3
    assert world.citizens[2].relationships[1].affection > before


def test_async_channels_are_delivered_and_read_with_bounded_replies() -> None:
    world = World(seed=7102, citizen_count=20)
    for citizen_id in (1, 2):
        _available(world, citizen_id)
    sent = [
        send_communication(world, sender_id=1, recipient_id=2, channel=channel, tone=CommunicationTone.PRACTICAL, subject="Organisation", body="Peux-tu confirmer ?")
        for channel in (CommunicationChannel.SMS, CommunicationChannel.EMAIL, CommunicationChannel.LETTER)
    ]
    world.run_minutes(4 * 24 * 60)
    assert all(item.status in {CommunicationStatus.READ, CommunicationStatus.REPLIED} for item in sent)
    assert all(item.reply_depth <= MAX_REPLY_DEPTH for item in world.communications.values())
    assert not [item for item in world.communications.values() if item.status == CommunicationStatus.DELIVERED and item.delivery_tick < world.tick - 24 * 60]


def test_communication_save_resume_preserves_queue_and_determinism() -> None:
    world = World(seed=7103, citizen_count=20)
    send_communication(world, sender_id=1, recipient_id=2, channel=CommunicationChannel.LETTER, tone=CommunicationTone.INVITATION, subject="Invitation", body="Retrouvons-nous.")
    world.run_minutes(120)
    state = world.export_state()
    restored = World.from_state(state)
    assert restored.export_state() == state
    world.run_minutes(3 * 24 * 60)
    restored.run_minutes(3 * 24 * 60)
    assert restored.snapshot() == world.snapshot()


def test_communication_api_exposes_send_history_and_websocket_domain(tmp_path) -> None:
    service.save_path = tmp_path / "city.json"
    with TestClient(app) as client:
        client.post("/api/simulation/pause")
        client.post("/api/city/reset", json={"seed": 7104})
        response = client.post("/api/communications", json={"senderId": 1, "recipientId": 2, "channel": "sms", "tone": "friendly", "subject": "Bonjour", "body": "Un petit message."})
        assert response.status_code == 201
        assert response.json()["channel"] == "sms"
        assert client.get("/api/communications").json()["metrics"]["sentToday"] == 1
        history = client.get("/api/citizens/2/communications").json()
        assert history["messages"][0]["recipient"]["id"] == 2
        with client.websocket_connect("/ws/city") as websocket:
            payload = websocket.receive_json()
            assert "communications" in payload
            assert payload["stats"]["sentToday"] == 1


def test_communication_api_rejects_self_contact_and_unknown_citizen(tmp_path) -> None:
    service.save_path = tmp_path / "city.json"
    with TestClient(app) as client:
        client.post("/api/simulation/pause")
        client.post("/api/city/reset", json={"seed": 7105})
        payload = {"senderId": 1, "recipientId": 1, "channel": "email", "tone": "friendly"}
        assert client.post("/api/communications", json=payload).status_code == 422
        payload["recipientId"] = 9999
        assert client.post("/api/communications", json=payload).status_code == 404


def test_contact_order_blocks_all_communication_channels() -> None:
    world = World(seed=7106, citizen_count=20)
    world.sentences[1] = JudicialSentence(id=1, case_id=1, citizen_id=1, sentence_type=SentenceType.RESTRAINING_ORDER, label="Interdiction de contact", status=SentenceStatus.ACTIVE, start_tick=0, end_tick=world.tick + 1440, beneficiary_id=2)
    for channel in CommunicationChannel:
        try:
            send_communication(world, sender_id=1, recipient_id=2, channel=channel, tone=CommunicationTone.FRIENDLY, subject="Test", body="Test")
        except ValueError as error:
            assert "interdiction de contact" in str(error).lower()
        else:
            raise AssertionError(f"Le canal {channel} aurait dû être bloqué")


def test_thirty_days_leave_no_overdue_communication_and_keep_history_bounded() -> None:
    world = World(seed=7107, citizen_count=20)
    world.run_minutes(30 * 24 * 60)
    assert len(world.communications) <= 2_000
    queued_ids = {communication_id for due_tick, communication_id in world.communication_queue if due_tick >= world.tick}
    assert all(item.id in queued_ids for item in world.communications.values() if item.status in {CommunicationStatus.QUEUED, CommunicationStatus.RINGING, CommunicationStatus.DELIVERED})
    assert all(len(citizen.communication_ids) <= 120 for citizen in world.citizens.values())
