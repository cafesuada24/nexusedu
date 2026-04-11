export const registerModelPayloadHandler = (handler) => {
  window.receiveModelPayload = handler;
  return () => {
    delete window.receiveModelPayload;
  };
};

export const pushModelPayload = (payload) => {
  if (typeof window.receiveModelPayload === "function") {
    window.receiveModelPayload(payload);
  } else {
    console.warn("receiveModelPayload is not registered yet.");
  }
};

export const fetchModelPayload = async (url) => {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

export const askModel = async (
  query,
  threadId,
  url = "http://localhost:8000/api/v1",
) => {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};
