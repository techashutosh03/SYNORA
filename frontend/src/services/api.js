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
  if (!res.ok) throw new Error(`Fetch conversation turns failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`);
  if (!res.ok) throw new Error(`Fetch metrics failed: ${res.statusText}`);
  return await res.json();
}

export async function sendChatMessage({ prompt, sessionId, selectedModels = null }) {
  const payload = {
    prompt,
    session_id: sessionId,
    selected_models: selectedModels,
  };
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.statusText}`);
  return await res.json();
}

export async function streamChatMessage({
  prompt,
  sessionId,
  selectedModels = null,
  onStageChange,
  onToken,
  onComplete,
  onError,
}) {
  const payload = {
    prompt,
    session_id: sessionId,
    selected_models: selectedModels,
  };

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Stream request failed: ${res.statusText}`);
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
            case 'stage':
              onStageChange?.(data);
              break;
            case 'token':
              onToken?.(data.token);
              break;
            case 'complete':
              onComplete?.(data);
              break;
            case 'error':
              onError?.(data.message || 'Stream error');
              break;
            default:
              break;
          }
        } catch (e) {
          console.warn('Failed parsing SSE JSON:', jsonStr, e);
        }
      }
    }
  } catch (err) {
    onError?.(err.message || 'Network error streaming chat');
  }
}

// ==========================================
// 🦞 CLAW CODE AGENT HARNESS CLIENT
// ==========================================

export async function streamAgentTask({
  task,
  modelId = 'qwen2.5-coder:7b',
  maxTurns = 12,
  workspaceRoot = null,
  onStart,
  onThought,
  onToolStart,
  onToolResult,
  onComplete,
  onError,
}) {
  const payload = {
    task,
    model_id: modelId,
    max_turns: maxTurns,
    workspace_root: workspaceRoot,
  };

  try {
    const res = await fetch(`${API_BASE}/api/agent/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
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

export async function executeSlashCommand({ command, workspaceRoot = null }) {
  const res = await fetch(`${API_BASE}/api/claw/slash`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, workspace_root: workspaceRoot }),
  });
  if (!res.ok) throw new Error(`Slash command execution failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchClawStatus() {
  const res = await fetch(`${API_BASE}/api/claw/status`);
  if (!res.ok) throw new Error(`Failed to fetch Claw status: ${res.statusText}`);
  return await res.json();
}

export async function fetchClawDoctor() {
  const res = await fetch(`${API_BASE}/api/claw/doctor`);
  if (!res.ok) throw new Error(`Failed to run Claw doctor: ${res.statusText}`);
  return await res.json();
}

export async function fetchClawDiff(path = null) {
  const query = path ? `?path=${encodeURIComponent(path)}` : '';
  const res = await fetch(`${API_BASE}/api/claw/diff${query}`);
  if (!res.ok) throw new Error(`Failed to fetch git diff: ${res.statusText}`);
  return await res.json();
}

export async function setClawWorkspace(path) {
  const res = await fetch(`${API_BASE}/api/claw/workspace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(`Failed to set workspace: ${res.statusText}`);
  return await res.json();
}

export async function fetchClawPermissions() {
  const res = await fetch(`${API_BASE}/api/agent/permissions`);
  if (!res.ok) throw new Error('Failed to fetch permissions');
  return await res.json();
}

export async function updateClawPermissions(mode) {
  const res = await fetch(`${API_BASE}/api/agent/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  if (!res.ok) throw new Error('Failed to update permissions');
  return await res.json();
}

export async function executeDirectTool(toolName, argumentsObj = {}) {
  const res = await fetch(`${API_BASE}/api/agent/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_name: toolName, arguments: argumentsObj }),
  });
  if (!res.ok) throw new Error('Failed to execute tool directly');
  return await res.json();
}
