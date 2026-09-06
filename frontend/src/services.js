const HTTP_BASE = "";
const STATE_WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;
const CAMERA_WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/camera`;

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${HTTP_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message = data?.detail || data?.error || `HTTP ${response.status}`;
    throw new Error(message);
  }

  return data;
}

export function startPipeline() {
  return apiRequest("/api/pipeline/start", {
    method: "POST"
  });
}

export function stopPipeline() {
  return apiRequest("/api/pipeline/stop", {
    method: "POST"
  });
}

export function getPipelineStatus() {
  return apiRequest("/api/pipeline/status");
}

export function analyzeScene() {
  return apiRequest("/api/analyze-scene", {
    method: "POST"
  });
}

export function askFalcon(question) {
  return apiRequest("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export function createRescueWebSocket(onState, onStatus) {
  let socket;
  let timer;
  let stopped = false;

  const connect = () => {
    if (stopped) return;

    onStatus("connecting");
    socket = new WebSocket(STATE_WS_URL);

    socket.onopen = () => {
      onStatus("online");
      socket.send("state");
    };

    socket.onmessage = event => {
      try {
        onState(JSON.parse(event.data));
      } catch (error) {
        console.error("[STATE WS] Invalid JSON:", error);
      }
    };

    socket.onerror = error => {
      console.error("[STATE WS] Error:", error);
      onStatus("offline");
    };

    socket.onclose = () => {
      onStatus("offline");
      if (!stopped) {
        timer = setTimeout(connect, 1500);
      }
    };
  };

  connect();

  return () => {
    stopped = true;
    clearTimeout(timer);
    if (socket) socket.close();
  };
}

export function createPhoneCameraWebSocket() {
  return new WebSocket(CAMERA_WS_URL);
}