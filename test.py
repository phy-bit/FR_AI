import asyncio
import websockets
import json


async def test():

    uri = "ws://127.0.0.1:8000/ws"

    async with websockets.connect(uri) as websocket:

        print("CONNECTED")

        for i in range(5):
            data = await websocket.recv()

            state = json.loads(data)

            print("\n--- RESCUE STATE ---")
            print("Frame:", state.get("frame"))
            print("People:", len(state.get("people", [])))
            print("Drone:", state.get("drone"))

        print("\nWEBSOCKET TEST SUCCESS")


asyncio.run(test())