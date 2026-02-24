import asyncio

from app.services.session_event_broker import SessionEventBroker


def test_broker_delivers_payload_to_subscriber():
    async def run() -> None:
        broker = SessionEventBroker()
        async with broker.subscribe("session-1") as queue:
            await broker.publish("session-1", {"change_type": "player_joined"})
            payload = await asyncio.wait_for(queue.get(), timeout=0.2)
            assert payload["change_type"] == "player_joined"

    asyncio.run(run())


def test_broker_isolated_by_session_id():
    async def run() -> None:
        broker = SessionEventBroker()
        async with broker.subscribe("session-a") as queue_a:
            async with broker.subscribe("session-b") as queue_b:
                await broker.publish("session-a", {"change_type": "session_started"})
                payload_a = await asyncio.wait_for(queue_a.get(), timeout=0.2)
                assert payload_a["change_type"] == "session_started"
                assert queue_b.empty()

    asyncio.run(run())
