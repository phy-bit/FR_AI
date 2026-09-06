import asyncio
import json
import os
import traceback

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from .camera_stream import phone_camera
from .pipeline_manager import pipeline_manager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STATE_FILE = os.path.join(OUTPUT_DIR, "rescue_state.json")
QWEN_IMAGE = os.path.join(OUTPUT_DIR, "qwen_current.jpg")
INCIDENT_FILE = os.path.join(OUTPUT_DIR, "incident_context.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="Falcon AI Search & Rescue Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_state():
    if not os.path.exists(STATE_FILE):
        return {
            "timestamp": 0,
            "frame": 0,
            "drone_id": 1,
            "drone": {
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "heading": None,
            },
            "scene": {
                "scene": "unknown",
                "environment": [],
                "hazards": [],
                "people_observations": [],
                "possible_distress_cues": [],
                "rescue_observations": [],
            },
            "people": [],
        }

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[STATE] Read error: {exc}")
        return {
            "timestamp": 0,
            "frame": 0,
            "drone_id": 1,
            "drone": {
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "heading": None,
            },
            "scene": {
                "scene": "unknown",
                "environment": [],
                "hazards": [],
                "people_observations": [],
                "possible_distress_cues": [],
                "rescue_observations": [],
            },
            "people": [],
        }


def read_incident_context():
    if not os.path.exists(INCIDENT_FILE):
        return {
            "incident_id": None,
            "updated_at": None,
            "latest_qwen_analysis": {},
            "analysis_history": [],
            "operator_notes": [],
            "refined_incident": {}
        }

    try:
        with open(INCIDENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[INCIDENT] Read error: {exc}")
        return {
            "incident_id": None,
            "updated_at": None,
            "latest_qwen_analysis": {},
            "analysis_history": [],
            "operator_notes": [],
            "refined_incident": {}
        }


def write_incident_context(context):
    temp_file = INCIDENT_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False, default=str)
    os.replace(temp_file, INCIDENT_FILE)


def get_latest_camera_jpeg():
    frame = phone_camera.get_latest_frame()
    if frame is None:
        return None

    if isinstance(frame, bytes):
        return frame

    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        return None

    return encoded.tobytes()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(read_state()))
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            jpeg = get_latest_camera_jpeg()
            if jpeg is not None:
                await websocket.send_bytes(jpeg)
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"[CAMERA WS] Error: {exc}")
        try:
            await websocket.close()
        except Exception:
            pass


def gen_video_stream():
    while True:
        jpeg = get_latest_camera_jpeg()
        if jpeg is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg
                + b"\r\n"
            )
        else:
            import time
            time.sleep(0.03)


@app.get("/video")
def video_feed():
    return StreamingResponse(
        gen_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/api/pipeline/start")
def start_pipeline():
    return pipeline_manager.start()


@app.post("/api/pipeline/stop")
def stop_pipeline():
    return pipeline_manager.stop()


@app.get("/api/pipeline/status")
def pipeline_status():
    return pipeline_manager.status()


@app.post("/api/enroll-live")
async def enroll_live(request: Request):
    try:
        form = await request.form()
        name = str(form.get("name", "")).strip()
        details = str(form.get("details", "")).strip()
        track_id_value = form.get("track_id")

        if not name:
            return JSONResponse(
                status_code=400,
                content={"error": "Name is required."},
            )

        if track_id_value is None:
            return JSONResponse(
                status_code=400,
                content={"error": "track_id is required."},
            )

        try:
            track_id = int(track_id_value)
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=400,
                content={"error": "track_id must be an integer."},
            )

        from enroll import start_live_enrollment

        result = start_live_enrollment(
            phone_camera=phone_camera,
            name=name,
            details=details,
            track_id=track_id,
        )
        return result
    except Exception as exc:
        print(f"[ENROLL] FAILED: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


def run_scene_analysis():
    from qwen_analyzer import QwenAnalyzer

    if not os.path.exists(QWEN_IMAGE):
        raise RuntimeError("No current Qwen image is available. Start the AI pipeline first.")

    analyzer = QwenAnalyzer()
    return analyzer.analyze(QWEN_IMAGE)


def run_falcon_answer(question, state):
    """Send structured rescue state plus the operator question to Falcon's RescueLLM."""
    try:
        from llm_responder import get_rescue_llm
    except Exception as exc:
        raise RuntimeError(f"Could not load Falcon LLM responder: {exc}") from exc

    try:
        responder = get_rescue_llm()
        result = responder.respond(
            question=question,
            context=state
        )
    except Exception as exc:
        raise RuntimeError(f"Falcon LLM generation failed: {exc}") from exc

    if result is None:
        raise RuntimeError("Falcon LLM returned no response.")

    if isinstance(result, dict):
        answer = (
            result.get("answer")
            or result.get("response")
            or result.get("message")
        )
        if answer is not None:
            return str(answer)
        return result

    return str(result)


def run_incident_refinement(incident_context, current_state):
    """Use Falcon to refine the accumulated Qwen incident context into an operator-ready incident description."""
    try:
        from llm_responder import get_rescue_llm
    except Exception as exc:
        raise RuntimeError(f"Could not load Falcon LLM responder: {exc}") from exc

    refinement_context = {
        "incident_context_from_json": incident_context,
        "current_rescue_state": current_state,
    }

    question = (
        "Define and refine the current rescue incident using the incident context stored in JSON "
        "and the current rescue state. Synthesize the observations into a clear incident report. "
        "Include: scene/environment, people observed, hazards, possible distress cues, rescue "
        "observations, overall incident situation, uncertainty, and recommended rescue focus. "
        "Do not invent facts. Clearly distinguish observed facts from possibilities. "
        "Return a concise structured incident assessment suitable for a rescue operator."
    )

    try:
        responder = get_rescue_llm()
        result = responder.respond(
            question=question,
            context=refinement_context
        )
    except Exception as exc:
        raise RuntimeError(f"Falcon incident refinement failed: {exc}") from exc

    if result is None:
        raise RuntimeError("Falcon returned no incident refinement.")

    if isinstance(result, dict):
        return result

    return {"text": str(result)}


@app.post("/api/analyze-scene")
def analyze_scene():
    try:
        result = run_scene_analysis()
        state = read_state()
        state["scene"] = result if isinstance(result, dict) else state.get("scene", {})
        state["qwen_vl_analysis"] = result

        incident = read_incident_context()
        incident["updated_at"] = state.get("timestamp")
        incident["latest_qwen_analysis"] = result
        incident["analysis_history"].append({
            "timestamp": state.get("timestamp"),
            "frame": state.get("frame"),
            "analysis": result
        })
        incident["analysis_history"] = incident["analysis_history"][-20:]
        incident["refined_incident"] = {
            "scene": result,
            "people": state.get("people", []),
            "drone": state.get("drone", {}),
            "status": "awaiting_falcon_refinement"
        }
        write_incident_context(incident)

        return {"analysis": result, "incident_file": INCIDENT_FILE}
    except Exception as exc:
        print(f"[QWEN] Error: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


@app.post("/api/refine-incident")
def refine_incident():
    try:
        current_state = read_state()
        incident_context = read_incident_context()

        if not incident_context.get("latest_qwen_analysis"):
            raise RuntimeError("No Qwen scene analysis is stored yet. Analyse the scene first.")

        refined = run_incident_refinement(
            incident_context,
            current_state
        )

        incident_context["refined_incident"] = {
            "generated_at": current_state.get("timestamp"),
            "source": "Falcon RescueLLM",
            "analysis": refined
        }
        incident_context["updated_at"] = current_state.get("timestamp")
        write_incident_context(incident_context)

        return {
            "refined_incident": refined,
            "incident_file": INCIDENT_FILE
        }
    except Exception as exc:
        print(f"[INCIDENT] Refinement error: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


@app.post("/api/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        question = str(data.get("question", "")).strip()
        if not question:
            return JSONResponse(
                status_code=400,
                content={"error": "Question is required."},
            )

        current_state = read_state()
        incident_context = read_incident_context()
        falcon_context = {
            "current_rescue_state": current_state,
            "incident_context": incident_context
        }
        answer = run_falcon_answer(question, falcon_context)
        return {"answer": answer}
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )