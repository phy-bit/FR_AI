# Falcon Rescue AI 🚁

> Modular AI-powered search-and-rescue system designed to assist
> operators in locating, identifying, and prioritizing people during
> emergency drone missions.

## Overview

**Falcon Rescue AI** is a modular computer-vision and AI system for
search-and-rescue operations.

The system separates major capabilities into independent modules so they
can be developed, debugged, and extended individually.

**Core principle:** real-time vision modules continuously observe the
scene, while higher-level AI analysis is invoked when the operator needs
it.

## Features

-   Person detection with YOLO
-   Multi-person tracking with persistent track IDs
-   Movement analysis
-   Pose and posture analysis
-   Observable condition cues
-   Face recognition and identity association
-   Unknown-person handling
-   Live person enrollment from the camera stream
-   Image-based person enrollment
-   Qwen-VL scene analysis on operator request
-   Rescue-priority scoring
-   Structured rescue state shared through JSON
-   Falcon operator assistant using the structured rescue state
-   FastAPI backend
-   React/Vite frontend
-   Phone-camera streaming bridge

## Architecture

``` text
Drone / Camera
      |
      v
Camera / Stream
      |
      +----------------------+
      |                      |
      v                      v
Person Detector         Object Tracker
(YOLO)                  (ByteTrack)
      |                      |
      +----------+-----------+
                 |
                 v
        Per-Person AI Modules
        +-------------------+
        | Movement          |
        | Pose / Posture    |
        | Condition         |
        | Face Recognition  |
        | Identity Mapping  |
        +---------+---------+
                  |
                  v
        Rescue Priority Engine
                  |
                  v
           Rescue State JSON
              /         \
             /           \
            v             v
       Qwen-VL         Falcon LLM
     Scene Analysis   Operator Assistant
       On Request
             \           /
              \         /
               v       v
              FastAPI Backend
                    |
                    v
              React Frontend
```

## Project Structure

``` text
FR_AI/
├── backend/
│   ├── camera_stream.py
│   ├── main.py
│   ├── pipeline_manager.py
│   ├── state_manager.py
│   └── websocket.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── services.js
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── ai_orchestrator.py
├── camera.py
├── condition.py
├── detector.py
├── enroll.py
├── face_association.py
├── face_database.py
├── face_recognizer.py
├── live_identity.py
├── llm_responder.py
├── movement.py
├── person_state.py
├── pose.py
├── qwen_analyzer.py
├── rescue_context.py
├── rescue_priority.py
├── test.py
├── tracker.py
└── .gitignore
```

## AI Modules

### Detection

`detector.py` detects people in incoming frames using a YOLO model.

### Tracking

`tracker.py` maintains persistent IDs for tracked people using object
tracking.

### Movement

`movement.py` extracts movement-related information for each tracked
person.

### Pose

`pose.py` analyses observable body posture and pose information.

### Condition

`condition.py` combines movement and pose observations into structured
condition cues.

> These are observable signals and are not intended to provide medical
> diagnoses.

### Identity

The face-recognition layer is separate from person tracking and supports
known-person matching, unknown-person handling, face embeddings, and
track-to-face association.

### Enrollment

`enroll.py` and `live_identity.py` support enrolling people from images
or the live camera workflow.

### Rescue Priority

`rescue_priority.py` converts structured observations into a
rescue-priority result to help the operator decide who may require
attention first.

### Qwen-VL Scene Analysis

`qwen_analyzer.py` provides higher-level scene understanding such as
environment, visible hazards, people observations, possible distress
cues, and rescue-relevant observations.

Qwen-VL is **operator-triggered**, rather than continuously executed, to
avoid unnecessary computation.

### Falcon LLM

`llm_responder.py` provides the operator-facing conversational layer. It
receives structured rescue state and answers questions without replacing
the dedicated vision modules.

## Backend API

### System

``` text
GET  /
GET  /api/status
GET  /api/state
```

### AI Analysis

``` text
POST /api/analyze-scene
POST /api/ask
```

`/api/analyze-scene` triggers a single Qwen-VL scene analysis.

`/api/ask` lets the operator ask Falcon questions using the current
structured rescue state.

### Enrollment

``` text
POST /api/enroll-live
```

Captures multiple samples from the live phone-camera stream and enrolls
the person.

### Video and Camera

``` text
GET /video
WS   /ws
WS   /ws/camera
```

### Pipeline Control

``` text
POST /api/pipeline/start
POST /api/pipeline/stop
GET  /api/pipeline/status
```

## Data Flow

A simplified per-person state looks like:

``` json
{
  "id": 1,
  "bbox": [100, 120, 250, 500],
  "confidence": 0.94,
  "identity": "UNKNOWN",
  "movement": {},
  "posture": {},
  "condition": {},
  "priority": "HIGH",
  "priority_score": 8,
  "priority_reasons": []
}
```

The backend stores broader rescue state as structured JSON so the
frontend, Qwen-VL layer, and Falcon assistant can work from a common
state.

## Technology Stack

### AI / Computer Vision

-   Python
-   OpenCV
-   Ultralytics YOLO
-   ByteTrack
-   Face embeddings / recognition
-   Qwen-VL
-   Local MLX inference

### Backend

-   FastAPI
-   WebSockets
-   Python threading / asynchronous execution

### Frontend

-   React
-   Vite
-   JavaScript / JSX
-   CSS

## Running Locally

### Backend

Create and activate a Python virtual environment, install the project's
Python dependencies, then start FastAPI with Uvicorn.

``` bash
cd FR_AI

python3 -m venv .venv
source .venv/bin/activate

# Install the project's Python dependencies.
# Then start the backend:
uvicorn backend.main:app --reload
```

### Frontend

``` bash
cd frontend
npm install
npm run dev
```

Camera, model, and local-inference configuration depends on the
development environment.

## Privacy and Sensitive Data

The repository intentionally excludes local/generated data such as:

-   Face databases
-   Captured images
-   Recordings
-   Generated output
-   Model weights
-   Local development certificates
-   Environment files and secrets

Never commit API keys, passwords, private certificates, biometric
databases, or other sensitive information.

## Design Philosophy

Falcon is intentionally modular:

``` text
Detection   → Who is visible?
Tracking    → Where is each person over time?
Movement    → How are they moving?
Pose        → What posture is observable?
Condition   → What observable cues are present?
Identity    → Who might this person be?
Priority    → Who may need attention first?
Qwen-VL     → What is happening in the wider scene?
Falcon LLM  → How should the operator interact with the system?
```

This separation makes the system easier to debug, extend, and integrate
with future drone hardware.

## Roadmap

-   [ ] Improved multi-person identity association
-   [ ] Better movement and posture scoring
-   [ ] More robust rescue-priority logic
-   [ ] Drone telemetry integration
-   [ ] GPS-based person localization
-   [ ] Operator-selected person analysis
-   [ ] Improved frontend visualization
-   [ ] More comprehensive automated testing
-   [ ] Hardware flight-controller integration
-   [ ] Full Falcon voice-assistant integration

## Disclaimer

Falcon Rescue AI is an experimental engineering project intended to
assist search-and-rescue operators.

AI-generated observations should be treated as decision-support
information and verified by a human operator. The system does not
replace trained emergency personnel or professional medical assessment.

## License

License information will be added as the project is prepared for public
release.
