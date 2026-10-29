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
  Code2
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

export default function ClawStudio({ health, settings }) {
  const [workspacePath, setWorkspacePath] = useState('.');
  const [workspaceInfo, setWorkspaceInfo] = useState(null);
  const [gitStatus, setGitStatus] = useState('');
  const [memoryFiles, setMemoryFiles] = useState([]);
  const [permissionMode, setPermissionMode] = useState('autonomous');

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

  const eventsEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    loadWorkspaceStatus();
  }, []);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamEvents]);

  const loadWorkspaceStatus = async () => {
    try {
      const data = await fetchClawStatus();
      if (data) {
        setWorkspaceInfo(data);
        setWorkspacePath(data.workspace_root || '.');
        setGitStatus(data.git_status || 'Clean');
        setMemoryFiles(data.memory_files || []);
        setPermissionMode(data.permission_mode || 'autonomous');
      }
    } catch (err) {
      console.warn('Could not load workspace status:', err);
    }
  };

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
      setDoctorReport(res.output);
      setActiveTab('stream');
      setStreamEvents(prev => [
        ...prev,
        {
          id: Date.now(),
          type: 'tool_result',
          tool: '/doctor',
          output: res.output,
          success: res.success,
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
      setGitDiff(res.output || res.error || 'No uncommitted diffs.');
    } catch (err) {
      setGitDiff(`Error fetching diff: ${err.message}`);
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRunSlash = async (cmd) => {
    if (isExecuting) return;
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
          output: res.output,
          success: res.success,
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
          output: `Command failed: ${err.message}`
        }
      ]);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecuteTask = async (taskText) => {
    const textToRun = (taskText || prompt).trim();
    if (!textToRun || isExecuting) return;

    setPrompt('');
    setIsExecuting(true);

    // If starts with /, dispatch slash command
    if (textToRun.startsWith('/')) {
      await handleRunSlash(textToRun);
      return;
    }

    setStreamEvents(prev => [
      ...prev,
      { id: Date.now(), type: 'user_task', content: textToRun }
    ]);

    try {
      await streamAgentTask({
        task: textToRun,
        modelId: 'qwen2.5-coder:7b',
        workspaceRoot: workspacePath,
        onStart: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'start', model: d.model }
          ]);
        },
        onThought: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'thought', content: d.content }
          ]);
        },
        onToolStart: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'tool_start', tool: d.tool, arguments: d.arguments }
          ]);
        },
        onToolResult: (d) => {
          setStreamEvents(prev => [
            ...prev,
            {
              id: Date.now(),
              type: 'tool_result',
              tool: d.tool,
              output: d.output,
              success: d.success,
              duration_ms: d.duration_ms
            }
          ]);
        },
        onComplete: (d) => {
          setStreamEvents(prev => [
            ...prev,
            {
              id: Date.now(),
              type: 'complete',
              final_response: d.final_response,
              total_time_ms: d.total_time_ms
            }
          ]);
          setIsExecuting(false);
          loadWorkspaceStatus();
        },
        onError: (d) => {
          setStreamEvents(prev => [
            ...prev,
            { id: Date.now(), type: 'error', output: d.message || JSON.stringify(d) }
          ]);
          setIsExecuting(false);
        }
      });
    } catch (err) {
      setStreamEvents(prev => [
        ...prev,
        { id: Date.now(), type: 'error', output: err.message }
      ]);
      setIsExecuting(false);
    }
  };

  const handleRunDirect = async () => {
    if (!directCommand.trim() || directLoading) return;
    setDirectLoading(true);
    try {
      const res = await executeDirectTool('bash', { command: directCommand.trim() });
      setDirectOutput(res.output || res.error || 'Done.');
    } catch (err) {
      setDirectOutput(`Execution failed: ${err.message}`);
    } finally {
      setDirectLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
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
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200 font-mono text-xs focus:outline-none focus:border-purple-500"
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
            <span className="truncate max-w-[140px]">{gitStatus.split('\n')[0] || 'Clean'}</span>
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

      {/* 2. SLASH COMMAND QUICK ACTION BAR */}
      <div className="px-4 py-2 bg-slate-900/40 border-b border-slate-800/60 flex items-center justify-between gap-2 overflow-x-auto text-xs shrink-0">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] text-slate-500 font-mono">Slash Commands:</span>
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
              className="px-2 py-0.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 rounded font-mono text-[11px] transition-colors whitespace-nowrap"
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
            Execution Stream
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

      {/* 3. MAIN PANE */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
        {/* TAB 1: EXECUTION STREAM */}
        {activeTab === 'stream' && (
          <div className="max-w-4xl mx-auto space-y-4">
            {streamEvents.length === 0 ? (
              <div className="text-center py-16 px-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600/30 to-cyan-500/30 border border-purple-500/30 flex items-center justify-center mx-auto mb-4 shadow-xl">
                  <Terminal className="w-8 h-8 text-cyan-400" />
                </div>
                <h3 className="text-lg font-bold text-slate-100 mb-2">Claw Code Autonomous Studio</h3>
                <p className="text-sm text-slate-400 max-w-lg mx-auto mb-6 leading-relaxed">
                  Combine Claw Code's native filesystem and shell tool engine with SYNORA's multi-model intelligence.
                  Give the agent a task (e.g. <span className="text-purple-300 font-mono">"Write unit tests for router.py"</span> or <span className="text-purple-300 font-mono">"Fix race conditions in cache"</span>), or run slash commands like <span className="text-cyan-300 font-mono">/doctor</span>.
                </p>
                <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
                  <button
                    onClick={() => handleRunSlash('/doctor')}
                    className="px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-300 hover:border-purple-500/60 transition-colors"
                  >
                    🩺 Run Preflight Doctor
                  </button>
                  <button
                    onClick={() => handleRunSlash('/status')}
                    className="px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-300 hover:border-purple-500/60 transition-colors"
                  >
                    📊 Check Workspace Status
                  </button>
                  <button
                    onClick={() => handleRunSlash('/tools')}
                    className="px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-300 hover:border-purple-500/60 transition-colors"
                  >
                    🛠️ Explore 12+ Tools
                  </button>
                </div>
              </div>
            ) : (
              streamEvents.map((ev) => (
                <div key={ev.id} className="animate-fadeIn">
                  {/* User Task */}
                  {ev.type === 'user_task' && (
                    <div className="flex justify-end mb-2">
                      <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-purple-600/40 via-indigo-600/40 to-cyan-600/40 border border-purple-500/40 p-3.5 text-sm text-slate-100 shadow-md">
                        <div className="font-semibold text-xs text-purple-300 mb-1 flex items-center gap-1.5">
                          <Terminal className="w-3.5 h-3.5" />
                          <span>Task Prompt</span>
                        </div>
                        <p className="whitespace-pre-wrap">{ev.content}</p>
                      </div>
                    </div>
                  )}

                  {/* User Command */}
                  {ev.type === 'user_command' && (
                    <div className="flex justify-end mb-2">
                      <div className="rounded-xl bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-mono text-cyan-300">
                        {ev.content}
                      </div>
                    </div>
                  )}

                  {/* Model Thought */}
                  {ev.type === 'thought' && (
                    <div className="rounded-xl bg-purple-950/20 border border-purple-500/20 p-3 text-xs text-purple-200/90 leading-relaxed">
                      <div className="flex items-center gap-1.5 font-semibold text-purple-400 mb-1">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Reasoning & Planning</span>
                      </div>
                      <div className="whitespace-pre-wrap font-sans">{ev.content}</div>
                    </div>
                  )}

                  {/* Tool Call Start */}
                  {ev.type === 'tool_start' && (
                    <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-3 text-xs">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded font-mono font-medium">
                            {ev.tool}
                          </span>
                          <span className="text-slate-400">Executing...</span>
                        </div>
                        <div className="animate-spin w-3.5 h-3.5 border-2 border-amber-400 border-t-transparent rounded-full" />
                      </div>
                      <pre className="p-2 bg-slate-950 rounded text-slate-300 font-mono text-[11px] overflow-x-auto">
                        {JSON.stringify(ev.arguments, null, 2)}
                      </pre>
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
                            {ev.tool}
                          </span>
                          <span className="text-slate-400 font-mono">
                            {ev.success ? 'Success' : 'Failed'}
                          </span>
                        </div>
                        {ev.duration_ms && (
                          <span className="text-[11px] font-mono text-slate-500">
                            {Math.round(ev.duration_ms)}ms
                          </span>
                        )}
                      </div>
                      <pre className="p-2.5 bg-slate-950 rounded-lg text-slate-200 font-mono text-[11px] whitespace-pre-wrap max-h-80 overflow-y-auto leading-relaxed">
                        {ev.output}
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
                        {ev.total_time_ms && (
                          <span className="text-slate-400 font-mono text-[11px]">
                            {Math.round(ev.total_time_ms)}ms total
                          </span>
                        )}
                      </div>
                      <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed mt-2 text-slate-100">
                        {ev.final_response}
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {ev.type === 'error' && (
                    <div className="rounded-xl bg-rose-950/20 border border-rose-500/30 p-3 text-xs text-rose-300 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold text-rose-400 mb-0.5">Execution Error</div>
                        <div>{ev.output}</div>
                      </div>
                    </div>
                  )}
                </div>
              ))
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
                Working Directory Diff
              </h4>
              <button
                onClick={handleLoadDiff}
                disabled={diffLoading}
                className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition-colors border border-slate-700"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${diffLoading ? 'animate-spin' : ''}`} />
                <span>Refresh Diff</span>
              </button>
            </div>
            <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap overflow-x-auto leading-relaxed min-h-[300px]">
              {gitDiff || 'Click "Refresh Diff" to inspect changes.'}
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
                <div key={i} className="rounded-xl bg-slate-900 border border-slate-800 p-4">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="font-semibold text-purple-300 font-mono">{f.file_name}</span>
                    <span className="text-slate-500 font-mono">{f.char_count} chars</span>
                  </div>
                  <pre className="p-3 bg-slate-950 rounded-lg text-slate-300 font-mono text-[11px] whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {f.content}
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
                placeholder="npm test, git status, ls -la..."
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
            {directOutput && (
              <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap overflow-x-auto min-h-[200px]">
                {directOutput}
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
                onClick={() => setIsExecuting(false)}
                className="p-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition-all shrink-0 flex items-center justify-center shadow-lg"
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
