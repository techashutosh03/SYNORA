// SYNORA AI - API Service Layer

const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/api/settings`);
  if (!res.ok) throw new Error(`Fetch settings failed: ${res.statusText}`);
  return await res.json();
}

export async function updateSettings(settings) {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(`Update settings failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchModels(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/api/models${query ? `?${query}` : ''}`);
  if (!res.ok) throw new Error(`Fetch models failed: ${res.statusText}`);
  return await res.json();
}

export async function selectActiveModels(modelIds) {
  const res = await fetch(`${API_BASE}/api/models/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_ids: modelIds }),
  });
  if (!res.ok) throw new Error(`Select models failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchConversations(limit = 30) {
  const res = await fetch(`${API_BASE}/api/conversations?limit=${limit}`);
  if (!res.ok) throw new Error(`Fetch conversations failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchConversationTurns(sessionId, limit = 50) {
  const res = await fetch(`${API_BASE}/api/conversations/${sessionId}?limit=${limit}`);
  if (!res.ok) throw new Error(`Fetch session turns failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`);
  if (!res.ok) throw new Error(`Fetch metrics failed: ${res.statusText}`);
  return await res.json();
}

/**
 * Standard Chat API call (fallback)
 */
export async function sendChatMessage({ prompt, sessionId, customModels, simulate = false }) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      session_id: sessionId,
      custom_models: customModels,
      simulate: Boolean(simulate),
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: { message: res.statusText } }));
    throw errorData;
  }

  return await res.json();
}

/**
 * Streaming Chat API via Server-Sent Events (SSE)
 */
export async function streamChatMessage({
  prompt,
  sessionId,
  customModels,
  simulate = false,
  onRouting,
  onStageStart,
  onStageComplete,
  onSynthesisStart,
  onToken,
  onDone,
  onError,
}) {
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        session_id: sessionId,
        custom_models: customModels,
        simulate: Boolean(simulate),
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      onError?.(err);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // Keep partial last event in buffer

      for (const eventStr of events) {
        if (!eventStr.trim()) continue;
        const lines = eventStr.split('\n');
        let eventName = '';
        let dataStr = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventName = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            dataStr = line.replace('data:', '').trim();
          }
        }

        if (!dataStr) continue;

        try {
          const payload = JSON.parse(dataStr);
          switch (eventName) {
            case 'routing':
              onRouting?.(payload);
              break;
            case 'stage_start':
              onStageStart?.(payload);
              break;
            case 'stage_complete':
              onStageComplete?.(payload);
              break;
            case 'synthesis_start':
              onSynthesisStart?.(payload);
              break;
            case 'token':
              onToken?.(payload.delta);
              break;
            case 'done':
              onDone?.(payload);
              break;
            case 'error':
              onError?.(payload);
              break;
            default:
              break;
          }
        } catch (e) {
          console.warn('Failed parsing SSE payload:', dataStr, e);
        }
      }
    }
  } catch (err) {
    onError?.(err);
  }
}

/**
 * Run Autonomous Agent Task (Claw Code Engine)
 */
export async function runAgentTask({ task, modelId, maxTurns = 12, workspaceRoot }) {
  const res = await fetch(`${API_BASE}/api/agent/task`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task,
      model_id: modelId,
      max_turns: maxTurns,
      workspace_root: workspaceRoot,
    }),
  });
  if (!res.ok) throw new Error(`Agent task failed: ${res.statusText}`);
  return await res.json();
}

/**
 * Stream Autonomous Agent Task via SSE
 */
export async function streamAgentTask({
  task,
  modelId,
  maxTurns = 12,
  workspaceRoot,
  onStart,
  onThought,
  onToolStart,
  onToolResult,
  onComplete,
  onError,
}) {
  try {
    const res = await fetch(`${API_BASE}/api/agent/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task,
        model_id: modelId,
        max_turns: maxTurns,
        workspace_root: workspaceRoot,
      }),
    });

    if (!res.ok) {
      throw new Error(`Agent stream request failed: ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.slice(5).trim();
        try {
          const data = JSON.parse(jsonStr);
          switch (data.event) {
            case 'start':
              onStart?.(data);
              break;
            case 'thought':
              onThought?.(data);
              break;
            case 'tool_start':
              onToolStart?.(data);
              break;
            case 'tool_result':
              onToolResult?.(data);
              break;
            case 'complete':
              onComplete?.(data);
              break;
            case 'error':
              onError?.(data);
              break;
            default:
              break;
          }
        } catch (e) {
          console.warn('Failed parsing agent SSE event:', jsonStr, e);
        }
      }
    }
  } catch (err) {
    onError?.(err);
  }
}

export async function fetchAgentTools() {
  const res = await fetch(`${API_BASE}/api/agent/tools`);
  if (!res.ok) throw new Error('Failed to fetch agent tools');
  return await res.json();
}

