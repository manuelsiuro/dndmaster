import asyncio

from app.services.voice_signal_broker import VoiceSignalBroker


def test_voice_broker_direct_message_targeting():
    async def run() -> None:
        broker = VoiceSignalBroker()
        async with broker.subscribe("session-1", "user-a") as queue_a:
            async with broker.subscribe("session-1", "user-b") as queue_b:
                await broker.publish(
                    "session-1",
                    {"type": "signal", "signal_type": "offer"},
                    target_user_id="user-b",
                )
                payload_b = await asyncio.wait_for(queue_b.get(), timeout=0.2)
                assert payload_b["signal_type"] == "offer"
                assert queue_a.empty()

    asyncio.run(run())


def test_voice_broker_broadcast_excludes_sender():
    async def run() -> None:
        broker = VoiceSignalBroker()
        async with broker.subscribe("session-2", "user-a") as queue_a:
            async with broker.subscribe("session-2", "user-b") as queue_b:
                await broker.publish(
                    "session-2",
                    {"type": "peer_joined", "user_id": "user-b"},
                    exclude_user_id="user-b",
                )
                payload_a = await asyncio.wait_for(queue_a.get(), timeout=0.2)
                assert payload_a["type"] == "peer_joined"
                assert queue_b.empty()

    asyncio.run(run())


def test_voice_broker_tracks_muted_users():
    async def run() -> None:
        broker = VoiceSignalBroker()
        await broker.set_muted("session-3", "player-1", True)
        assert await broker.is_muted("session-3", "player-1")
        assert await broker.muted_user_ids("session-3") == {"player-1"}

        await broker.set_muted("session-3", "player-1", False)
        assert not await broker.is_muted("session-3", "player-1")
        assert await broker.muted_user_ids("session-3") == set()

    asyncio.run(run())
