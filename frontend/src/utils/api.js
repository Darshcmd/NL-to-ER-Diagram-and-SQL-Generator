const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail || body?.message || 'Request failed';
    throw new Error(detail);
  }
  return body;
}

export async function initializeSession(inputText, fileContext = null) {
  return requestJson(`${API_BASE_URL}/api/chat/init`, {
    method: 'POST',
    body: JSON.stringify({
      input_text: inputText,
      file_context: fileContext,
    }),
  });
}

export async function confirmAnswers(sessionId, answers) {
  return requestJson(`${API_BASE_URL}/api/chat/confirm-answers`, {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      answers_summary: answers,
    }),
  });
}

export async function refineSchema(sessionId, refinementRequest) {
  return requestJson(`${API_BASE_URL}/api/chat/refine`, {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      refinement_request: refinementRequest,
    }),
  });
}

export async function generateSQL(sessionId, dialect = 'PostgreSQL') {
  return requestJson(`${API_BASE_URL}/api/chat/generate-sql`, {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      dialect,
    }),
  });
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
    method: 'POST',
    body: formData,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail || 'Failed to upload file';
    throw new Error(detail);
  }
  return body;
}

export async function getSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/chat/session/${sessionId}`);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail || 'Failed to get session';
    throw new Error(detail);
  }
  return body;
}
