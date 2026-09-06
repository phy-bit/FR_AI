import React, { useEffect, useRef, useState } from "react";
// Modal for enrolling a person with live camera and five samples
function EnrollPerson({ person, onClose }) {
  const [name, setName] = useState("");
  const [details, setDetails] = useState("");
  const [enrollError, setEnrollError] = useState("");
  const [loading, setLoading] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Start camera on mount, stop on unmount/close
  useEffect(() => {
    let stopped = false;
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false
        });
        if (stopped) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
      } catch (err) {
        // Camera error handling can be added if needed
      }
    }
    startCamera();
    return () => {
      stopped = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []);

  // No manual sample capture in this version

  // Helper: handle enroll
  const handleEnroll = async () => {
    setEnrollError("");
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("details", details);
      formData.append("track_id", person.id);
      // No manual samples appended here
      const resp = await fetch("/api/enroll-live", {
        method: "POST",
        body: formData,
        // Do not set Content-Type, browser will set including boundary
      });
      if (!resp.ok) {
        let msg = "Failed to enroll.";
        try {
          const data = await resp.json();
          msg = data?.error || data?.message || msg;
        } catch { }
        throw new Error(msg);
      }
      onClose();
    } catch (err) {
      setEnrollError(err.message || "Failed to enroll.");
    } finally {
      setLoading(false);
    }
  };

  // Helper: close and cleanup
  const handleCancel = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    onClose();
  };

  const canEnroll = name.trim() && !loading;

  return (
    <div className="modal enroll-modal" style={{
      position: "fixed", zIndex: 1000, left: 0, top: 0, width: "100vw", height: "100vh",
      background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center"
    }}>
      <div style={{
        background: "#fff", padding: 24, borderRadius: 8, minWidth: 350, maxWidth: 400, boxShadow: "0 2px 12px #0003"
      }}>
        <h2 style={{ marginTop: 0 }}>Enroll Person (Track #{person.id})</h2>
        <div style={{ marginBottom: 12 }}>
          <label>
            Name:<br />
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              style={{ width: "100%" }}
              disabled={loading}
            />
          </label>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>
            Details:<br />
            <input
              type="text"
              value={details}
              onChange={e => setDetails(e.target.value)}
              style={{ width: "100%" }}
              disabled={loading}
            />
          </label>
        </div>
        <div style={{ marginBottom: 12 }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: "100%", maxHeight: 220, background: "#222", borderRadius: 6 }}
          />
        </div>
        <p style={{ margin: "10px 0", opacity: 0.75, fontSize: 13 }}>
          Falcon will automatically capture at least 5 face samples from the live camera after you start enrollment.
        </p>
        {enrollError && <div style={{ color: "red", marginBottom: 8 }}>{enrollError}</div>}
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button
            type="button"
            onClick={handleEnroll}
            disabled={!canEnroll}
            style={{ flex: 1, background: canEnroll ? "#218c21" : "#aaa", color: "#fff" }}
          >
            {loading ? "ENROLLING..." : "ENROLL"}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={loading}
            style={{ flex: 1, background: "#e33", color: "#fff" }}
          >
            CANCEL
          </button>
        </div>
      </div>
    </div>
  );
}
import { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Camera,
  ChevronRight,
  Crosshair,
  Gauge,
  MapPin,
  Radio,
  Satellite,
  Shield,
  UserRound,
  Users,
  Wifi,
  WifiOff
} from "lucide-react";
import {
  createPhoneCameraWebSocket,
  createRescueWebSocket,
  startPipeline,
  stopPipeline,
  getPipelineStatus,
  analyzeScene,
  askFalcon
} from "./services";

// Local helper for incident refinement to avoid blank page if not exported from services.js
async function refineIncident() {
  const response = await fetch("/api/refine-incident", {
    method: "POST"
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data?.error || "Incident refinement failed.");
  }

  return data;
}

const EMPTY = {
  timestamp: 0,
  frame: 0,
  drone_id: 1,
  drone: {
    latitude: null,
    longitude: null,
    altitude: null,
    heading: null
  },
  scene: {
    scene: "unknown",
    environment: [],
    hazards: [],
    people_observations: [],
    possible_distress_cues: [],
    rescue_observations: []
  },
  people: []
};

const pretty = v =>
  v == null || v === ""
    ? "—"
    : String(v).replaceAll("_", " ").toUpperCase();

const metricValue = value => {
  if (value == null || value === "") return "—";
  if (typeof value !== "object") return pretty(value);

  const result =
    value.result ??
    value.label ??
    value.status ??
    value.state ??
    value.posture ??
    value.movement ??
    value.condition ??
    value.classification ??
    value.description;

  return result == null || result === "" ? "—" : pretty(result);
};

const metricScore = value => {
  if (value == null || typeof value !== "object") return null;

  const score =
    value.score ??
    value.risk_score ??
    value.condition_score ??
    value.movement_score ??
    value.posture_score;

  return typeof score === "number" && Number.isFinite(score) ? score : null;
};


const pclass = v => String(v || "LOW").toLowerCase();

// Robustness helpers for scene normalization
const safeArray = value => (Array.isArray(value) ? value : []);

const normalizeScene = scene => ({
  scene: scene?.scene ?? "unknown",
  environment: safeArray(scene?.environment),
  hazards: safeArray(scene?.hazards),
  people_observations: safeArray(scene?.people_observations),
  possible_distress_cues: safeArray(scene?.possible_distress_cues),
  rescue_observations: safeArray(scene?.rescue_observations)
});

function Status({ status }) {
  const online = status === "online";
  const connecting = status === "connecting";

  return (
    <div
      className={`status ${
        online ? "online" : connecting ? "connecting" : "offline"
      }`}
    >
      {online ? <Wifi size={14} /> : <WifiOff size={14} />}
      {online ? "ONLINE" : connecting ? "CONNECTING" : "OFFLINE"}
    </div>
  );
}

function Header({ state, connection }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="mark">
          <Shield size={21} />
        </div>
        <div>
          <div className="brand-name">FALCON</div>
          <div className="brand-sub">AI SEARCH &amp; RESCUE SYSTEM</div>
        </div>
      </div>

      <div className="headstats">
        <div>
          <small>DRONE</small>
          <b>DRONE-{String(state.drone_id ?? 1).padStart(2, "0")}</b>
        </div>
        <div>
          <small>FRAME</small>
          <b>{state.frame ?? 0}</b>
        </div>
        <div>
          <small>DETECTED</small>
          <b>{state.people?.length ?? 0}</b>
        </div>
        <Status status={connection} />
      </div>
    </header>
  );
}

function VideoFeed() {
  const [cameraOn, setCameraOn] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [facingMode, setFacingMode] = useState("environment");

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const cameraSocketRef = useRef(null);
  const canvasRef = useRef(null);
  const captureTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (captureTimerRef.current) {
        clearInterval(captureTimerRef.current);
      }

      if (cameraSocketRef.current) {
        cameraSocketRef.current.close();
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  function stopCamera() {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }

    if (cameraSocketRef.current) {
      cameraSocketRef.current.close();
      cameraSocketRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOn(false);
  }

  async function startCamera() {
    try {
      setCameraError("");

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode } },
        audio: false
      });

      streamRef.current = stream;

      const video = videoRef.current;
      video.srcObject = stream;
      await video.play();

      const socket = createPhoneCameraWebSocket();
      cameraSocketRef.current = socket;

      socket.onopen = () => {
        console.log("[PHONE CAMERA] Connected to Falcon backend.");

        const canvas = canvasRef.current;
        const context = canvas.getContext("2d", { alpha: false });

        captureTimerRef.current = setInterval(() => {
          if (
            !video ||
            video.readyState < 2 ||
            socket.readyState !== WebSocket.OPEN
          ) {
            return;
          }

          const width = video.videoWidth || 1280;
          const height = video.videoHeight || 720;

          canvas.width = width;
          canvas.height = height;
          context.drawImage(video, 0, 0, width, height);

          canvas.toBlob(blob => {
            if (blob && socket.readyState === WebSocket.OPEN) {
              socket.send(blob);
            }
          }, "image/jpeg", 0.75);
        }, 100);
      };

      socket.onerror = error => {
        console.error("[PHONE CAMERA] WebSocket error:", error);
        setCameraError("Could not connect the phone camera to Falcon.");
      };

      socket.onclose = () => {
        console.log("[PHONE CAMERA] Backend connection closed.");
      };

      setCameraOn(true);
    } catch (error) {
      console.error("[PHONE CAMERA]", error);
      stopCamera();
      setCameraError("Camera permission denied or camera unavailable.");
    }
  }

  async function switchCamera() {
    if (!cameraOn) return;

    const nextFacingMode =
      facingMode === "environment" ? "user" : "environment";

    try {
      const oldStream = streamRef.current;

      const newStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: nextFacingMode } },
        audio: false
      });

      streamRef.current = newStream;

      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
        await videoRef.current.play();
      }

      if (oldStream) {
        oldStream.getTracks().forEach(track => track.stop());
      }

      setFacingMode(nextFacingMode);
      setCameraError("");
    } catch (error) {
      console.error("[PHONE CAMERA] Camera switch failed:", error);
      setCameraError("Could not switch camera.");
    }
  }

  function toggleCamera() {
    if (cameraOn) {
      stopCamera();
    } else {
      startCamera();
    }
  }

  return (
    <section className="panel">
      <div className="pt">
        <span>
          <Camera size={17} />
          LIVE DRONE FEED
        </span>

        {cameraOn && (
          <button
            type="button"
            onClick={switchCamera}
            className="camera-switch"
          >
            {facingMode === "environment" ? "SELFIE CAMERA" : "MAIN CAMERA"}
          </button>
        )}

        <button
          type="button"
          onClick={toggleCamera}
          className="camera-toggle"
        >
          {cameraOn ? "STOP CAMERA" : "START CAMERA"}
        </button>
      </div>

      <div className="video">
        <img
          src="/video"
          alt="Processed Falcon rescue feed"
          className="processed-video"
        />

        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="phone-video-source"
        />

        <canvas ref={canvasRef} style={{ display: "none" }} />

        {!cameraOn && (
          <div className="video-placeholder">
            <Crosshair size={44} />
            <strong>FALCON PROCESSED FEED</strong>
            <span>
              Start the phone camera to send frames to the rescue AI
            </span>
          </div>
        )}

        {cameraOn && (
          <div className="video-overlay">
            <span>FALCON LIVE</span>
            <span>AI PROCESSED</span>
          </div>
        )}
      </div>

      {cameraError && <div className="camera-error">{cameraError}</div>}
    </section>
  );
}

function PipelineControls() {
  const [status, setStatus] = useState("unknown");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refinedIncident, setRefinedIncident] = useState(null);
  const [refinementError, setRefinementError] = useState("");
  const [refining, setRefining] = useState(false);
  const pollingRef = useRef(null);

  const updateStatus = async () => {
    try {
      const data = await getPipelineStatus();
      if (data?.running === true) {
        setStatus("running");
        setError("");
      } else if (data?.running === false) {
        setStatus("stopped");
        setError("");
      } else if (data?.status) {
        setStatus(String(data.status).toLowerCase());
        setError("");
      } else {
        setStatus("unknown");
      }
    } catch (err) {
      setError(err.message || "Could not read AI pipeline status.");
      setStatus("unknown");
    }
  };

  useEffect(() => {
    updateStatus();
    pollingRef.current = setInterval(updateStatus, 2000);
    return () => {
      clearInterval(pollingRef.current);
    };
  }, []);

  const handleStart = async () => {
    setLoading(true);
    setError("");
    try {
      await startPipeline();
      setStatus("running");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError("");
    try {
      await stopPipeline();
      setStatus("stopped");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyse = async () => {
    setLoading(true);
    setError("");
    setStatus("analysing");
    try {
      await analyzeScene();
      setStatus("analysing"); // Keep showing analysing until next poll
    } catch (err) {
      if (err.message.includes("404")) {
        setError("Scene analysis not available.");
      } else {
        setError(err.message);
      }
      setTimeout(() => setError(""), 10000);
      setStatus("unknown");
    } finally {
      setLoading(false);
    }
  };

  const handleDefineScene = async () => {
    setRefining(true);
    setRefinementError("");
    try {
      const response = await refineIncident();
      setRefinedIncident(response?.refined_incident ?? null);
    } catch (err) {
      setRefinementError(err.message || "Incident refinement failed.");
      setTimeout(() => setRefinementError(""), 10000);
    } finally {
      setRefining(false);
    }
  };

  let statusMessage = "";
  if (error) {
    statusMessage = `ERROR: ${error}`;
  } else if (status === "running") {
    statusMessage = "AI RUNNING";
  } else if (status === "stopped") {
    statusMessage = "AI STOPPED";
  } else if (status === "analysing") {
    statusMessage = "ANALYSING...";
  } else if (status === "unknown") {
    statusMessage = "STATUS UNKNOWN";
  }

  return (
    <section className="panel pipeline-controls">
      <div className="pt">
        <span>
          <Activity size={17} /> AI PIPELINE CONTROLS
        </span>
      </div>
      <div className="pipeline-buttons">
        <button onClick={handleStart} disabled={loading || status === "running"}>
          START AI
        </button>
        <button onClick={handleStop} disabled={loading || status === "stopped"}>
          STOP AI
        </button>
        <button onClick={handleAnalyse} disabled={loading}>
          ANALYSE SCENE
        </button>
        <button onClick={handleDefineScene} disabled={loading || refining}>
          {refining ? "DEFINING..." : "DEFINE SCENE"}
        </button>
      </div>
      <div className={`pipeline-status ${error ? "error" : ""}`}>
        {statusMessage}
      </div>
      {refinementError && (
        <small className="note error">Error: {refinementError}</small>
      )}
      {refinedIncident && (
        <pre className="incident-refinement">
          {typeof refinedIncident === "string"
            ? refinedIncident
            : JSON.stringify(refinedIncident, null, 2)}
        </pre>
      )}
    </section>
  );
}

function Map({ drone }) {
  const gps =
    Number.isFinite(drone?.latitude) && Number.isFinite(drone?.longitude);

  return (
    <section className="panel">
      <div className="pt">
        <span>
          <MapPin size={17} /> RESCUE MAP
        </span>
        <em className={gps ? "gpsok" : "gpsoff"}>
          <Satellite size={14} /> {gps ? "GPS LOCK" : "NO GPS"}
        </em>
      </div>

      <div className="map">
        <div className="grid" />
        <Crosshair className="mapcross" size={32} />

        {gps ? (
          <div className="mapinfo">
            <b>
              {drone.latitude.toFixed(6)}, {drone.longitude.toFixed(6)}
            </b>
            <span>
              ALT {drone.altitude ?? "—"} m · HDG {drone.heading ?? "—"}°
            </span>
          </div>
        ) : (
          <div className="mapoff">
            <Satellite size={32} />
            <b>GPS SIGNAL UNAVAILABLE</b>
            <span>Waiting for drone telemetry</span>
          </div>
        )}
      </div>
    </section>
  );
}

function Person({ person }) {
  const pr =
    person?.priority && typeof person.priority === "object"
      ? person.priority
      : {};
  const level = pr.level || "LOW";
  const [showEnroll, setShowEnroll] = useState(false);

  return (
    <div className={`person ${pclass(level)}`}>
      <div className="persontop">
        <span>
          <UserRound size={15} /> PERSON #{person.id}
        </span>
        <b className={`badge ${pclass(level)}`}>{level}</b>
      </div>

      <div className="identity">
        <strong>{pretty(person.identity)}</strong>
        <small>
          {person.identity_confidence > 0
            ? `${Math.round(person.identity_confidence * 100)}% confidence`
            : "Identity not confirmed"}
        </small>
      </div>

      {(() => {
        const identity = String(person?.identity ?? "").trim().toLowerCase();
        const isUnknown =
          !identity ||
          identity === "unknown" ||
          identity === "none" ||
          identity === "unidentified";

        return isUnknown ? (
          <button
            type="button"
            onClick={() => setShowEnroll(true)}
            style={{
              margin: "10px 0 0 0",
              padding: "6px 12px",
              borderRadius: 4,
              background: "#1a55a1",
              color: "#fff",
              border: "none",
              fontWeight: 500,
              cursor: "pointer"
            }}
          >
            ENROLL PERSON
          </button>
        ) : null;
      })()}

      <div className="metrics">
        {[
          ["MOVEMENT", person.movement],
          ["POSTURE", person.posture],
          ["CONDITION", person.condition]
        ].map(([label, value]) => {
          const score = metricScore(value);
          return (
            <div key={label}>
              <small>{label}</small>
              <b>{metricValue(value)}</b>
              {score !== null && (
                <span style={{ display: "block", fontSize: 11, opacity: 0.7, marginTop: 3 }}>
                  SCORE {score}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="score">
        <span>RESCUE SCORE</span>
        <strong>{pr.score ?? 0}</strong>
      </div>

      {pr.reasons?.length > 0 && (
        <div className="reasons">
          {pr.reasons.map((reason, index) => (
            <div key={index}>
              <ChevronRight size={12} />
              {reason}
            </div>
          ))}
        </div>
      )}
      {showEnroll && (
        <EnrollPerson
          person={person}
          onClose={() => setShowEnroll(false)}
        />
      )}
    </div>
  );
}

function People({ people }) {
  return (
    <section className="panel people">
      <div className="pt">
        <span>
          <Users size={17} /> PEOPLE / PRIORITY
        </span>
        <b className="count">{people.length}</b>
      </div>

      <div className="peoplelist">
        {people.length ? (
          people.map(person => (
            <Person key={person.id} person={person} />
          ))
        ) : (
          <div className="empty">
            <UserRound size={30} />
            <b>NO PEOPLE DETECTED</b>
            <span>Awaiting computer-vision detections</span>
          </div>
        )}
      </div>
    </section>
  );
}

function Intelligence({ scene }) {
  scene = normalizeScene(scene);
  const groups = [
    ["ENVIRONMENT", scene.environment],
    ["HAZARDS", scene.hazards],
    ["DISTRESS CUES", scene.possible_distress_cues],
    ["RESCUE OBSERVATIONS", scene.rescue_observations]
  ];

  return (
    <section className="panel intel">
      <div className="pt">
        <span>
          <Activity size={17} /> SCENE INTELLIGENCE
        </span>
      </div>

      <div className="scenename">
        <small>SCENE</small>
        <b>{pretty(scene.scene)}</b>
      </div>

      <div className="intelgrid">
        {groups.map(([title, items]) => (
          <div className="igroup" key={title}>
            <small>{title}</small>
            {items?.length ? (
              items.map((item, index) => (
                <div className="iitem" key={index}>
                  <ChevronRight size={12} />
                  {item}
                </div>
              ))
            ) : (
              <span className="muted">None reported</span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Telemetry({ drone }) {
  return (
    <section className="panel telemetry">
      <div className="pt">
        <span>
          <Radio size={17} /> DRONE TELEMETRY
        </span>
      </div>

      <div className="telegrid">
        {[
          ["LATITUDE", drone?.latitude],
          ["LONGITUDE", drone?.longitude],
          [
            "ALTITUDE",
            drone?.altitude == null ? null : `${drone.altitude} m`
          ],
          [
            "HEADING",
            drone?.heading == null ? null : `${drone.heading}°`
          ]
        ].map(([label, value]) => (
          <div key={label}>
            <small>{label}</small>
            <b>{value ?? "—"}</b>
          </div>
        ))}
      </div>
    </section>
  );
}

function Falcon() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    try {
      const response = await askFalcon(question.trim());
      // Accept answer from answer, response, or message fields
      const ans = response.answer ?? response.response ?? response.message ?? "";
      setAnswer(
        typeof ans === "string"
          ? ans
          : ans == null
            ? ""
            : JSON.stringify(ans, null, 2)
      );
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(""), 10000);
    } finally {
      setLoading(false);
      setQuestion("");
    }
  };

  return (
    <section className="panel falcon">
      <div className="pt">
        <span>
          <Bot size={17} /> FALCON OPERATOR ASSISTANT
        </span>
        <em>
          <i /> AI READY
        </em>
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={question}
          onChange={event => setQuestion(event.target.value)}
          placeholder="Ask Falcon about the current rescue situation..."
          disabled={loading}
        />
        <button disabled={loading}>
          ASK <ChevronRight size={14} />
        </button>
      </form>

      {loading && <small className="note">Loading...</small>}
      {error && <small className="note error">Error: {error}</small>}
      {answer && (
        <div className="falcon-answer">
          <strong>Answer:</strong>
          <p>{answer}</p>
        </div>
      )}

      <small className="note">
        Ready for future <code>POST /api/ask</code> integration.
      </small>
    </section>
  );
}

export default function App() {
  const [state, setState] = useState(EMPTY);
  const [connection, setConnection] = useState("connecting");

  useEffect(() => {
    return createRescueWebSocket(data => {
      setState(previous => ({
        ...EMPTY,
        ...data,
        drone: {
          ...EMPTY.drone,
          ...(data?.drone || {})
        },
        scene: normalizeScene(data?.scene)
      }));
    }, setConnection);
  }, []);

  const critical = useMemo(
    () =>
      state.people.filter(
        person => person.priority?.level === "CRITICAL"
      ).length,
    [state.people]
  );

  return (
    <div className="shell">
      <Header state={state} connection={connection} />

      {critical > 0 && (
        <div className="critical">
          <AlertTriangle size={15} />
          {critical} CRITICAL RESCUE PRIORITY {critical > 1 ? "CASES" : "CASE"} DETECTED
        </div>
      )}

      <main>
        <div className="maincol">
          <VideoFeed />
          <PipelineControls />
          <Map drone={state.drone} />
          <Intelligence scene={state.scene} />
        </div>

        <aside>
          <People people={state.people} />
          <Telemetry drone={state.drone} />
          <Falcon />
        </aside>
      </main>

      <footer>
        <span>FALCON RESCUE AI · LOCAL COMMAND INTERFACE</span>
        <span>
          <Gauge size={12} /> FRAME {state.frame} · {Number(state.timestamp || 0).toFixed(2)}s
        </span>
      </footer>
    </div>
  );
}