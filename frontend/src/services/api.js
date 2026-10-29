/**
 * SYNORA AI + Claw Code API Client
 * Robust, memory-safe communication with the local FastAPI backend.
 */

const API_BASE = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? (window.location.port === '8000' ? '' : 'http://127.0.0.1:8000')
  : '';

// ==========================================
// SYSTEM & HEALTH
// ==========================================

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn('fetchHealth error:', err);
    return null;
  }
}

export async function fetchSettings() {
  try {
    const res = await fetch(`${API_BASE}/api/settings`);
    if (!res.ok) throw new Error(`Fetch settings failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn('fetchSettings error:', err);
    return null;
  }
}

export async function updateSettings(newSettings) {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newSettings),
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
  try {
    const res = await fetch(`${API_BASE}/api/conversations?limit=${limit}`);
    if (!res.ok) throw new Error(`Fetch conversations failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn('fetchConversations error:', err);
    return { conversations: [] };
  }
}

export async function fetchConversationTurns(sessionId, limit = 50) {
  const res = await fetch(`${API_BASE}/api/conversations/${sessionId}?limit=${limit}`);
  if (!res.ok) throw new Error(`Fetch conversation turns failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics`);
    if (!res.ok) throw new Error(`Fetch metrics failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    console.warn('fetchMetrics error:', err);
    return null;
  }
}

// ==========================================
// CHAT & MULTI-MODEL ORCHESTRATION
// ==========================================

export async function sendChatMessage({ prompt, sessionId, selectedModels = null, simulate = false }) {
  const payload = {
    prompt,
    session_id: sessionId,
    selected_models: selectedModels,
    simulate: Boolean(simulate),
  };
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Chat request failed: ${res.statusText}`);
  }
  return await res.json();
}

/**
 * SSE Streaming for SYNORA Multi-Model Chat
 * Handles routing, stage_start, stage_complete, synthesis_start, token, done, error
 */
export async function streamChatMessage({
  prompt,
  sessionId,
  customModels = null,
  simulate = false,
  signal = null,
  onRouting,
  onStageStart,
  onStageComplete,
  onSynthesisStart,
  onToken,
  onDone,
  onError,
}) {
  const payload = {
    prompt,
    session_id: sessionId,
    custom_models: customModels,
    simulate: Boolean(simulate),
  };

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || errData.message || `Stream request failed: ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        let currentEvent = null;
        let dataStr = null;

        const lines = block.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            dataStr = trimmed.slice(5).trim();
          }
        }

        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          const eventType = currentEvent || parsed.event;

          switch (eventType) {
            case 'routing':
              onRouting?.(parsed);
              break;
            case 'stage_start':
              onStageStart?.(parsed);
              break;
            case 'stage_complete':
              onStageComplete?.(parsed);
              break;
            case 'synthesis_start':
              onSynthesisStart?.(parsed);
              break;
            case 'token':
              if (parsed.delta) {
                onToken?.(parsed.delta);
              } else if (parsed.token) {
                onToken?.(parsed.token);
              }
              break;
            case 'done':
              onDone?.(parsed);
              break;
            case 'error':
              onError?.(parsed);
              break;
            default:
              break;
          }
        } catch (e) {
          console.warn('Failed parsing chat SSE block:', dataStr, e);
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('Chat stream aborted by user');
      return;
    }
    onError?.(err);
  }
}

// ==========================================
// 🦞 CLAW CODE AGENT HARNESS CLIENT
// ==========================================

/**
 * SSE Streaming for Claw Code Autonomous Loop
 */
export async function streamAgentTask({
  task,
  modelId = 'qwen2.5-coder:7b',
  maxTurns = 12,
  workspaceRoot = null,
  signal = null,
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
      signal,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || errData.message || `Agent stream request failed: ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        let currentEvent = null;
        let dataStr = null;

        const lines = block.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            dataStr = trimmed.slice(5).trim();
          }
        }

        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);
          const eventType = currentEvent || data.event;

          switch (eventType) {
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
          console.warn('Failed parsing agent SSE event:', dataStr, e);
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('Agent stream aborted by user');
      return;
    }
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
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Slash command execution failed: ${res.statusText}`);
  }
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
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Failed to set workspace: ${res.statusText}`);
  }
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
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || 'Failed to execute tool directly');
  }
  return await res.json();
}
