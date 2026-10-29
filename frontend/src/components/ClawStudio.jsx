import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Play, 
  Square, 
  Folder, 
  GitBranch, 
  Shield, 
  Stethoscope, 
  CheckCircle2, 
  AlertTriangle, 
  FileCode, 
  Sparkles, 
  Copy, 
  RefreshCw, 
  Layers, 
  Cpu, 
  FileText,
  CornerDownLeft,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Code2,
  Trash2,
  Check,
  Search,
  Zap,
  HelpCircle,
  Clock,
  ArrowRight
} from 'lucide-react';
import { 
  streamAgentTask, 
  executeSlashCommand, 
  fetchClawStatus, 
  fetchClawDoctor, 
  fetchClawDiff, 
  setClawWorkspace,
  updateClawPermissions,
  executeDirectTool
} from '../services/api';

/**
 * Safely stringify any value to prevent React child rendering errors
 */
function safeString(val) {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string') return val;
  try {
    return JSON.stringify(val, null, 2);
  } catch (e) {
    return String(val);
  }
}

export default function ClawStudio({ health, settings }) {
  const [workspacePath, setWorkspacePath] = useState('.');
  const [workspaceInfo, setWorkspaceInfo] = useState(null);
  const [gitStatus, setGitStatus] = useState('');
  const [memoryFiles, setMemoryFiles] = useState([]);
  const [permissionMode, setPermissionMode] = useState('autonomous');
  const [selectedModel, setSelectedModel] = useState('auto');

  const [prompt, setPrompt] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [streamEvents, setStreamEvents] = useState([]);
  const [activeTab, setActiveTab] = useState('stream'); // 'stream' | 'diff' | 'memory' | 'direct'
  
  const [gitDiff, setGitDiff] = useState('');
  const [diffLoading, setDiffLoading] = useState(false);

  const [directCommand, setDirectCommand] = useState('');
  const [directOutput, setDirectOutput] = useState('');
  const [directLoading, setDirectLoading] = useState(false);

  const [doctorReport, setDoctorReport] = useState(null);
  const [doctorLoading, setDoctorLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const eventsEndRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);

  const loadWorkspaceStatus = async () => {
    try {
      const data = await fetchClawStatus();
      if (data) {
        setWorkspaceInfo(data);
        setWorkspacePath(data.workspace_root || '.');
        setGitStatus(safeString(data.git_status || 'Clean'));
        setMemoryFiles(Array.isArray(data.memory_files) ? data.memory_files : []);
        setPermissionMode(data.permission_mode || 'autonomous');
      }
    } catch (err) {
      console.warn('Could not load workspace status:', err);
    }
  };

  useEffect(() => {
    loadWorkspaceStatus();
    return () => {
      // Abort any pending stream on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamEvents]);

  const handleSetWorkspace = async () => {
    if (!workspacePath.trim()) return;
    try {
      await setClawWorkspace(workspacePath.trim());
      await loadWorkspaceStatus();
    } catch (err) {
      alert(`Failed to set workspace: ${err.message}`);
    }
  };

  const handleModeChange = async (newMode) => {
    try {
      await updateClawPermissions(newMode);
      setPermissionMode(newMode);
    } catch (err) {
      console.error('Failed to change permission mode:', err);
    }
  };

  const handleRunDoctor = async () => {
    setDoctorLoading(true);
    try {
      const res = await fetchClawDoctor();
      const outputText = safeString(res?.output || 'Doctor preflight finished.');
      setDoctorReport(outputText);
      setActiveTab('stream');
      setStreamEvents(prev => [
        ...prev,
        {
          id: Date.now(),
          type: 'tool_result',
          tool: '/doctor',
          output: outputText,
          success: Boolean(res?.success),
          duration_ms: 120
        }
      ]);
    } catch (err) {
      alert(`Doctor preflight failed: ${err.message}`);
    } finally {
      setDoctorLoading(false);
    }
  };

  const handleLoadDiff = async () => {
    setDiffLoading(true);
    setActiveTab('diff');
    try {
      const res = await fetchClawDiff();
      setGitDiff(safeString(res?.output || res?.error || 'No uncommitted diffs found. Working tree is clean.'));
    } catch (err) {
      setGitDiff(`Error fetching diff: ${err.message}`);
    } finally {
      setDiffLoading(false);
    }
  };

  // Internal executor for slash commands
  const runSlashCommandInternal = async (cmd) => {
    setIsExecuting(true);
    setStreamEvents(prev => [
      ...prev,
      { id: Date.now(), type: 'user_command', content: cmd }
    ]);

    try {
      const res = await executeSlashCommand({ command: cmd, workspaceRoot: workspacePath });
      setStreamEvents(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          type: 'tool_result',
          tool: cmd,
          output: safeString(res?.output || 'Done.'),
          success: Boolean(res?.success),
          duration_ms: 80
        }
      ]);
      await loadWorkspaceStatus();
    } catch (err) {
      setStreamEvents(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          type: 'error',
          output: `Command failed: ${err?.message || safeString(err)}`
        }
      ]);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleRunSlash = (cmd) => {
    if (isExecuting) return;
    runSlashCommandInternal(cmd);
  };

  const handleExecuteTask = async (taskText) => {
    const textToRun = (taskText || prompt).trim();
    if (!textToRun || isExecuting) return;

    setPrompt('');

    // If starts with /, dispatch slash command cleanly
    if (textToRun.startsWith('/')) {
      await runSlashCommandInternal(textToRun);
      return;
    }

    setIsExecuting(true);
    setStreamEvents(prev => [
      ...prev,
      { id: Date.now(), type: 'user_task', content: textToRun }
    ]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await streamAgentTask({
        task: textToRun,
        modelId: selectedModel || 'auto',
        workspaceRoot: workspacePath,
        signal: abortController.signal,
        onStart: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'start', model: safeString(d?.model || selectedModel || 'auto') }
          ]);
        },
        onThought: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'thought', content: safeString(d?.content) }
          ]);
        },
        onToolStart: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'tool_start', tool: safeString(d?.tool), arguments: d?.arguments }
          ]);
        },
        onToolResult: (d) => {
          setStreamEvents(prev => [
            ...prev,
            {
              id: Date.now(),
              type: 'tool_result',
              tool: safeString(d?.tool),
              output: safeString(d?.output),
              success: Boolean(d?.success),
              duration_ms: typeof d?.duration_ms === 'number' ? d.duration_ms : 0
            }
          ]);
        },
        onComplete: (d) => {
          setStreamEvents(prev => [
            ...prev,
            {
              id: Date.now(),
              type: 'complete',
              final_response: safeString(d?.final_response),
              total_time_ms: typeof d?.total_time_ms === 'number' ? d.total_time_ms : 0
            }
          ]);
          setIsExecuting(false);
          loadWorkspaceStatus();
        },
        onError: (d) => {
          const errMsg = d?.message ? safeString(d.message) : safeString(d);
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'error', output: errMsg }
          ]);
          setIsExecuting(false);
        }
      });
    } catch (err) {
      if (err.name === 'AbortError') {
        setStreamEvents(prev => [
          ...prev,
          { id: Date.now(), type: 'error', output: 'Task execution stopped by user.' }
        ]);
      } else {
        setStreamEvents(prev => [
          ...prev,
          { id: Date.now(), type: 'error', output: err?.message || safeString(err) }
        ]);
      }
      setIsExecuting(false);
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleStopExecution = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsExecuting(false);
  };

  const handleRunDirect = async () => {
    if (!directCommand.trim() || directLoading) return;
    setDirectLoading(true);
    try {
      const res = await executeDirectTool('bash', { command: directCommand.trim() });
      setDirectOutput(safeString(res?.output || res?.error || 'Command executed cleanly.'));
    } catch (err) {
      setDirectOutput(`Execution failed: ${err.message}`);
    } finally {
      setDirectLoading(false);
    }
  };

  const handleClearStream = () => {
    setStreamEvents([]);
  };

  const handleCopyText = (id, text) => {
    navigator.clipboard.writeText(safeString(text));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const gitBranchDisplay = String(gitStatus || '').split('\n')[0] || 'Clean';

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07090E] text-slate-100 overflow-hidden relative">
      {/* 1. WORKSPACE & ENVIRONMENT TOP BAR */}
      <div className="px-4 py-2.5 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0 shadow-lg">
        {/* Workspace Path Input */}
        <div className="flex items-center gap-2 flex-1 min-w-[280px]">
          <Folder className="w-4 h-4 text-purple-400 shrink-0" />
          <span className="text-slate-400 font-medium shrink-0">Workspace:</span>
          <input
            type="text"
            value={workspacePath}
            onChange={(e) => setWorkspacePath(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-purple-500 transition-colors"
            placeholder="/path/to/project"
          />
          <button
            onClick={handleSetWorkspace}
            className="px-2.5 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 rounded-lg font-medium transition-colors"
          >
            Set
          </button>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Git Branch Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800/70 border border-slate-700/60 rounded-md font-mono text-[11px] text-slate-300">
            <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
            <span className="truncate max-w-[140px]">{gitBranchDisplay}</span>
          </div>

          {/* Security Mode Selector */}
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => handleModeChange('autonomous')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                permissionMode === 'autonomous'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Auto-approve non-destructive tools"
            >
              Autonomous
            </button>
            <button
              onClick={() => handleModeChange('ask')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                permissionMode === 'ask'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Ask confirmation before executing writes or shell commands"
            >
              Ask
            </button>
            <button
              onClick={() => handleModeChange('read_only')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                permissionMode === 'read_only'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Reject all write and bash execution operations"
            >
              Read-Only
            </button>
          </div>

          {/* Model Selector */}
          <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1">
            <Cpu className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-transparent text-[11px] font-mono text-slate-200 outline-none cursor-pointer max-w-[170px]"
              title="Select Claw Code Reasoning & Coding Model"
            >
              <option value="auto" className="bg-slate-900 text-purple-300">⚡ Auto (Best Model)</option>
              <optgroup label="OmniRoute Cloud Flagships" className="bg-slate-900 text-cyan-300 font-semibold">
                <option value="claude-3-7-sonnet" className="bg-slate-900 text-slate-200">Claude 3.7 Sonnet (Hybrid)</option>
                <option value="claude-3-5-sonnet" className="bg-slate-900 text-slate-200">Claude 3.5 Sonnet (Refactor)</option>
                <option value="gpt-4o" className="bg-slate-900 text-slate-200">GPT-4o (OpenAI)</option>
                <option value="deepseek-reasoner" className="bg-slate-900 text-slate-200">DeepSeek R1 (Reasoner)</option>
                <option value="deepseek-chat" className="bg-slate-900 text-slate-200">DeepSeek V3 (Coding)</option>
                <option value="gemini-2.0-flash" className="bg-slate-900 text-slate-200">Gemini 2.0 Flash (Fast)</option>
                <option value="qwen-2.5-coder-32b" className="bg-slate-900 text-slate-200">Qwen 2.5 Coder 32B</option>
              </optgroup>
              <optgroup label="Local Ollama Models" className="bg-slate-900 text-emerald-300 font-semibold">
                <option value="qwen2.5-coder:7b" className="bg-slate-900 text-slate-200">Qwen 2.5 Coder 7B (Local)</option>
                <option value="deepseek-r1:7b" className="bg-slate-900 text-slate-200">DeepSeek R1 7B (Local)</option>
                <option value="llama3.1:8b" className="bg-slate-900 text-slate-200">Llama 3.1 8B (Local)</option>
              </optgroup>
            </select>
          </div>

          {/* Doctor Preflight Button */}
          <button
            onClick={handleRunDoctor}
            disabled={doctorLoading}
            className="flex items-center gap-1 px-2.5 py-1 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 rounded-lg font-medium transition-colors shadow-sm"
            title="Run preflight diagnostic health check"
          >
            <Stethoscope className={`w-3.5 h-3.5 ${doctorLoading ? 'animate-spin' : ''}`} />
            <span>Doctor</span>
          </button>
        </div>
      </div>

      {/* 2. SLASH COMMAND QUICK ACTION BAR & TAB SELECTORS */}
      <div className="px-4 py-2 bg-slate-900/40 border-b border-slate-800/60 flex items-center justify-between gap-2 overflow-x-auto text-xs shrink-0">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] text-slate-500 font-mono">Quick Actions:</span>
          {[
            { label: '🩺 /doctor', cmd: '/doctor' },
            { label: '🔍 /review', cmd: '/review' },
            { label: '📝 /diff', cmd: '/diff' },
            { label: '💾 /commit', cmd: '/commit' },
            { label: '⚙️ /init', cmd: '/init' },
            { label: '🛠️ /tools', cmd: '/tools' },
            { label: '⚡ /compact', cmd: '/compact' },
            { label: '❓ /help', cmd: '/help' },
          ].map((item) => (
            <button
              key={item.cmd}
              onClick={() => handleRunSlash(item.cmd)}
              disabled={isExecuting}
              className="px-2 py-0.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 rounded font-mono text-[11px] transition-colors whitespace-nowrap active:scale-95 disabled:opacity-50"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => setActiveTab('stream')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'stream'
                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Live Stream {streamEvents.length > 0 && `(${streamEvents.length})`}
          </button>
          <button
            onClick={handleLoadDiff}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'diff'
                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Git Diff
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'memory'
                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Project Guidelines ({memoryFiles.length})
          </button>
          <button
            onClick={() => setActiveTab('direct')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'direct'
                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Terminal Runner
          </button>
        </div>
      </div>

      {/* 3. MAIN WORKSPACE VIEWPORT */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6 space-y-4">
        {/* TAB 1: EXECUTION STREAM */}
        {activeTab === 'stream' && (
          <div className="max-w-4xl mx-auto space-y-3">
            {/* Stream Header Action Bar */}
            {streamEvents.length > 0 && (
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-300">Active Execution Trace</span>
                  {isExecuting && (
                    <span className="flex items-center gap-1.5 text-cyan-400">
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                      Running...
                    </span>
                  )}
                </div>
                <button
                  onClick={handleClearStream}
                  className="flex items-center gap-1 px-2 py-1 text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 rounded transition-colors"
                  title="Clear feed"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear Feed</span>
                </button>
              </div>
            )}

            {streamEvents.length === 0 ? (
              /* EMPTY STATE HERO */
              <div className="py-8 space-y-8 animate-fade-in">
                <div className="text-center space-y-3">
                  <div className="inline-flex p-3 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 mb-1">
                    <Terminal className="w-8 h-8 text-cyan-400" />
                  </div>
                  <h3 className="text-2xl font-bold text-white tracking-tight">
                    Claw Code Studio
                  </h3>
                  <p className="text-slate-400 text-xs md:text-sm max-w-lg mx-auto leading-relaxed">
                    Autonomous software engineering harness powered by SYNORA multi-model intelligence. Performs surgical code edits, git operations, and terminal tasks with full verification.
                  </p>
                </div>

                {/* 4 Quick Start Action Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 max-w-2xl mx-auto">
                  <button
                    onClick={handleRunDoctor}
                    className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-left transition-all group flex flex-col justify-between space-y-2 shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-semibold text-cyan-400 text-xs">
                        <Stethoscope className="w-4 h-4" />
                        <span>1. Run Diagnostic Doctor</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                        Verify Ollama connectivity, model readiness, git repository health, and permissions.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-cyan-400 font-medium group-hover:translate-x-1 transition-transform">
                      <span>Execute /doctor</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </button>

                  <button
                    onClick={() => handleRunSlash('/review')}
                    className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-purple-500/40 text-left transition-all group flex flex-col justify-between space-y-2 shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-semibold text-purple-400 text-xs">
                        <Sparkles className="w-4 h-4" />
                        <span>2. Autonomous Code Review</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                        Perform a surgical security and logic review of uncommitted git diffs across the project.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-purple-400 font-medium group-hover:translate-x-1 transition-transform">
                      <span>Execute /review</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </button>

                  <button
                    onClick={handleLoadDiff}
                    className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 text-left transition-all group flex flex-col justify-between space-y-2 shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-semibold text-indigo-400 text-xs">
                        <GitBranch className="w-4 h-4" />
                        <span>3. Inspect Git Diff</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                        View modified files and syntax changes in real-time before generating semantic commits.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-indigo-400 font-medium group-hover:translate-x-1 transition-transform">
                      <span>View Diff</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </button>

                  <button
                    onClick={() => handleRunSlash('/tools')}
                    className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/40 text-left transition-all group flex flex-col justify-between space-y-2 shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-semibold text-emerald-400 text-xs">
                        <FileCode className="w-4 h-4" />
                        <span>4. Explore 12+ Tools</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                        Inspect registered native tools for bash, filesystem editing, grep search, and git operations.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium group-hover:translate-x-1 transition-transform">
                      <span>List Tools</span>
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  </button>
                </div>

                {/* Example Prompts */}
                <div className="max-w-2xl mx-auto pt-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-purple-400" />
                    <span>Try a Task</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Audit repository git status and modified files',
                      'Search for all TODO items across the backend codebase',
                      'Check project memory files and guidelines',
                      'Run test suite and verify system health'
                    ].map((example, i) => (
                      <button
                        key={i}
                        onClick={() => handleExecuteTask(example)}
                        className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-purple-500/50 text-xs transition-colors"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              /* EVENT LIST */
              streamEvents.map((ev) => {
                const isCopied = copiedId === ev.id;
                const outputText = safeString(ev.output);

                return (
                  <div key={ev.id} className="animate-fadeIn space-y-2">
                    {/* User Task */}
                    {ev.type === 'user_task' && (
                      <div className="flex justify-end mb-2">
                        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-purple-600/40 via-indigo-600/40 to-cyan-600/40 border border-purple-500/40 p-3.5 text-sm text-slate-100 shadow-md">
                          <div className="font-semibold text-xs text-purple-300 mb-1 flex items-center gap-1.5">
                            <Terminal className="w-3.5 h-3.5" />
                            <span>Task Prompt</span>
                          </div>
                          <p className="whitespace-pre-wrap">{safeString(ev.content)}</p>
                        </div>
                      </div>
                    )}

                    {/* User Slash Command */}
                    {ev.type === 'user_command' && (
                      <div className="flex justify-end mb-2">
                        <div className="rounded-xl bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-mono text-cyan-300 shadow-sm">
                          {safeString(ev.content)}
                        </div>
                      </div>
                    )}

                    {/* Model Thought */}
                    {ev.type === 'thought' && (
                      <div className="rounded-xl bg-purple-950/20 border border-purple-500/20 p-3 text-xs text-purple-200/90 leading-relaxed shadow-sm">
                        <div className="flex items-center justify-between gap-1.5 font-semibold text-purple-400 mb-1">
                          <span className="flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Reasoning & Planning</span>
                          </span>
                          <button
                            onClick={() => handleCopyText(ev.id, ev.content)}
                            className="text-purple-400 hover:text-purple-200 transition-colors p-1"
                            title="Copy thought"
                          >
                            {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                        <div className="whitespace-pre-wrap font-sans">{safeString(ev.content)}</div>
                      </div>
                    )}

                    {/* Tool Call Start */}
                    {ev.type === 'tool_start' && (
                      <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded font-mono font-medium">
                              {safeString(ev.tool)}
                            </span>
                            <span className="text-slate-400">Executing tool...</span>
                          </div>
                          <div className="animate-spin w-3.5 h-3.5 border-2 border-amber-400 border-t-transparent rounded-full" />
                        </div>
                        {ev.arguments && Object.keys(ev.arguments).length > 0 && (
                          <pre className="p-2 bg-slate-950 rounded text-slate-300 font-mono text-[11px] overflow-x-auto">
                            {safeString(ev.arguments)}
                          </pre>
                        )}
                      </div>
                    )}

                    {/* Tool Result */}
                    {ev.type === 'tool_result' && (
                      <div className="rounded-xl bg-slate-900/80 border border-slate-800/80 p-3.5 text-xs shadow-md">
                        <div className="flex items-center justify-between gap-2 mb-2 border-b border-slate-800 pb-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded font-mono font-medium text-[11px] ${
                              ev.success
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            }`}>
                              {safeString(ev.tool)}
                            </span>
                            <span className="text-slate-400 font-mono text-[11px]">
                              {ev.success ? 'Success' : 'Notice / Handled'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {ev.duration_ms != null && (
                              <span className="text-[11px] font-mono text-slate-500">
                                {Math.round(Number(ev.duration_ms))}ms
                              </span>
                            )}
                            <button
                              onClick={() => handleCopyText(ev.id, ev.output)}
                              className="text-slate-400 hover:text-white transition-colors p-1"
                              title="Copy output"
                            >
                              {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                        <pre className="p-2.5 bg-slate-950 rounded-lg text-slate-200 font-mono text-[11px] whitespace-pre-wrap max-h-80 overflow-y-auto leading-relaxed">
                          {outputText}
                        </pre>
                      </div>
                    )}

                    {/* Task Complete */}
                    {ev.type === 'complete' && (
                      <div className="rounded-2xl bg-gradient-to-r from-emerald-950/30 via-slate-900 to-slate-900 border border-emerald-500/30 p-4 text-xs text-slate-200 shadow-xl">
                        <div className="flex items-center justify-between gap-2 mb-2 border-b border-slate-800 pb-2">
                          <div className="flex items-center gap-2 font-semibold text-emerald-400 text-sm">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Task Completed Successfully</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {ev.total_time_ms != null && (
                              <span className="text-slate-400 font-mono text-[11px]">
                                {Math.round(Number(ev.total_time_ms))}ms total
                              </span>
                            )}
                            <button
                              onClick={() => handleCopyText(ev.id, ev.final_response)}
                              className="text-slate-400 hover:text-white transition-colors p-1"
                              title="Copy final response"
                            >
                              {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                        <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed mt-2 text-slate-100">
                          {safeString(ev.final_response)}
                        </div>
                      </div>
                    )}

                    {/* Error */}
                    {ev.type === 'error' && (
                      <div className="rounded-xl bg-rose-950/20 border border-rose-500/30 p-3 text-xs text-rose-300 flex items-start gap-2 shadow-sm">
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-rose-400 mb-0.5">Execution Notification</div>
                          <div className="whitespace-pre-wrap font-mono text-[11px]">{safeString(ev.output)}</div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
            <div ref={eventsEndRef} />
          </div>
        )}

        {/* TAB 2: GIT DIFF */}
        {activeTab === 'diff' && (
          <div className="max-w-4xl mx-auto space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h4 className="font-semibold text-slate-200 flex items-center gap-2 text-sm">
                <GitBranch className="w-4 h-4 text-cyan-400" />
                Working Directory Git Diff
              </h4>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleRunSlash('/commit')}
                  className="flex items-center gap-1.5 px-3 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 text-xs rounded-lg transition-colors border border-purple-500/40"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Commit Diff (/commit)</span>
                </button>
                <button
                  onClick={handleLoadDiff}
                  disabled={diffLoading}
                  className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition-colors border border-slate-700"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${diffLoading ? 'animate-spin' : ''}`} />
                  <span>Refresh Diff</span>
                </button>
              </div>
            </div>
            <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap overflow-x-auto leading-relaxed min-h-[300px]">
              {safeString(gitDiff || 'Click "Refresh Diff" to inspect changes.')}
            </pre>
          </div>
        )}

        {/* TAB 3: PROJECT GUIDELINES */}
        {activeTab === 'memory' && (
          <div className="max-w-4xl mx-auto space-y-4">
            <h4 className="font-semibold text-slate-200 flex items-center gap-2 text-sm">
              <FileText className="w-4 h-4 text-purple-400" />
              Loaded Project Guidelines & Memory Files ({memoryFiles.length})
            </h4>
            {memoryFiles.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/50 rounded-2xl border border-slate-800 text-slate-400 text-xs">
                No CLAUDE.md or AGENTS.md detected in the active workspace.
                <div className="mt-3">
                  <button
                    onClick={() => handleRunSlash('/init')}
                    className="px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 rounded-lg text-xs font-medium"
                  >
                    ⚙️ Run /init to Scaffold Guidelines
                  </button>
                </div>
              </div>
            ) : (
              memoryFiles.map((f, i) => (
                <div key={i} className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-purple-300 font-mono">{safeString(f.file_name)}</span>
                    <span className="text-slate-500 font-mono">{safeString(f.char_count)} chars</span>
                  </div>
                  <pre className="p-3 bg-slate-950 rounded-lg text-slate-300 font-mono text-[11px] whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {safeString(f.content)}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: DIRECT TERMINAL RUNNER */}
        {activeTab === 'direct' && (
          <div className="max-w-4xl mx-auto space-y-3">
            <h4 className="font-semibold text-slate-200 flex items-center gap-2 text-sm">
              <Terminal className="w-4 h-4 text-emerald-400" />
              Direct Workspace Shell Runner
            </h4>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-mono text-sm">$</span>
              <input
                type="text"
                value={directCommand}
                onChange={(e) => setDirectCommand(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRunDirect()}
                placeholder="git status, git diff, ls -la, python3 -m unittest..."
                className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={handleRunDirect}
                disabled={directLoading}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                {directLoading ? 'Running...' : 'Run'}
              </button>
            </div>
            
            {/* Quick Command Chips */}
            <div className="flex items-center gap-2 pt-1">
              <span className="text-[10px] text-slate-500 font-mono">Quick Run:</span>
              {['git status', 'git diff', 'ls -la', 'pwd'].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => {
                    setDirectCommand(cmd);
                    executeDirectTool('bash', { command: cmd }).then(res => {
                      setDirectOutput(safeString(res?.output || res?.error));
                    });
                  }}
                  className="px-2 py-0.5 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded font-mono text-[10px] border border-slate-800"
                >
                  {cmd}
                </button>
              ))}
            </div>

            {directOutput && (
              <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap overflow-x-auto min-h-[200px]">
                {safeString(directOutput)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* 4. PROMPT INPUT BAR */}
      <div className="p-4 bg-slate-900/90 border-t border-slate-800/80 shrink-0">
        <div className="max-w-4xl mx-auto relative glass-input rounded-2xl p-2 border border-slate-700/80 focus-within:border-purple-500/60 shadow-2xl">
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              rows={1}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleExecuteTask();
                }
              }}
              placeholder="Give Claw Code a task (or type /doctor, /review, /diff, /commit, /help)..."
              className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 text-sm resize-none focus:outline-none max-h-40 leading-relaxed py-1 px-2 font-mono"
              disabled={isExecuting}
            />

            {isExecuting ? (
              <button
                onClick={handleStopExecution}
                className="p-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition-all shrink-0 flex items-center justify-center shadow-lg active:scale-95"
                title="Stop Execution"
              >
                <Square className="w-4 h-4 fill-white" />
              </button>
            ) : (
              <button
                onClick={() => handleExecuteTask()}
                disabled={!prompt.trim()}
                className={`p-2.5 rounded-xl transition-all shrink-0 flex items-center justify-center ${
                  prompt.trim()
                    ? 'bg-gradient-to-r from-purple-600 to-cyan-500 text-white shadow-lg hover:brightness-110 active:scale-95'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                }`}
                title="Execute Task"
              >
                <Play className="w-4 h-4 fill-white" />
              </button>
            )}
          </div>
          <div className="flex items-center justify-between px-2 pt-1.5 text-[10px] text-slate-500 font-mono">
            <span>Claw Code Autonomous Agent Harness</span>
            <span>Enter to run, Shift+Enter for new line</span>
          </div>
        </div>
      </div>
    </div>
  );
}
