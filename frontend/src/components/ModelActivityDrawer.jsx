import React from 'react';
import { 
  X, 
  Activity, 
  Cpu, 
  Zap, 
  ShieldCheck, 
  Layers, 
  Clock, 
  CheckCircle2, 
  RotateCw,
  HardDrive,
  Info,
  Terminal
} from 'lucide-react';

export default function ModelActivityDrawer({
  isOpen,
  onClose,
  activePipeline,
  latestTurn,
  metrics,
  health,
}) {
  if (!isOpen) return null;

  const stages = activePipeline?.stages || latestTurn?.orchestration_stages || [
    { stage_name: 'Specialist Proposal', model_id: 'qwen2.5-coder:7b', role: 'specialist', execution_time_ms: 1240, status: 'success' },
    { stage_name: 'Reviewer & Security Audit', model_id: 'deepseek-r1:7b', role: 'reviewer', execution_time_ms: 1520, status: 'success' },
    { stage_name: 'Unified Synthesis', model_id: 'llama3.1:8b', role: 'synthesizer', execution_time_ms: 890, status: 'success' }
  ];

  const currentStageIndex = activePipeline?.currentStageIndex ?? -1;
  const isRunning = activePipeline?.isRunning ?? false;

  const rssMb = latestTurn?.memory_rss_mb || metrics?.latest_rss_mb || 680;
  const memoryPct = Math.min(Math.round((rssMb / 16384) * 100), 100);

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-[#0B0F19] border-l border-slate-800 shadow-2xl flex flex-col animate-slide-up sm:animate-none">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">Model Activity</h3>
            <p className="text-[11px] text-slate-400">Live Multi-Model Orchestration</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs">
        {/* Apple Silicon M2 Memory Protection Status */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-purple-400" />
              M2 Memory Safeguard
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              Active Guardrail
            </span>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>RAM Consumption</span>
              <span className="font-mono text-slate-200">{Math.round(rssMb)} MB / 16,384 MB</span>
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 to-cyan-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(memoryPct, 5)}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Strict sequential execution: SYNORA passing <code className="text-purple-300">keep_alive=0</code> to unload each model immediately after its stage.
          </p>
        </div>

        {/* Claw Code Native Tool Arsenal */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-cyan-400" />
              Claw Code Tool Arsenal
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              7 Native Tools Active
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {['bash', 'read_file', 'write_file', 'edit_file', 'grep_search', 'glob_files', 'list_dir'].map(tool => (
              <span key={tool} className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700/60">
                {tool}
              </span>
            ))}
          </div>
          <p className="text-[10px] text-slate-400">
            Enables autonomous filesystem search, surgical diffs, and sandboxed terminal execution.
          </p>
        </div>

        {/* Live Pipeline Flow Stages */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-slate-300 font-semibold">
            <span className="flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" />
              Pipeline Execution Trace
            </span>
            {isRunning && (
              <span className="flex items-center gap-1 text-[11px] text-cyan-400">
                <RotateCw className="w-3 h-3 animate-spin" />
                Executing...
              </span>
            )}
          </div>

          <div className="space-y-2">
            {stages.map((stg, i) => {
              const isCurrent = isRunning && currentStageIndex === i;
              const isFinished = !isRunning || currentStageIndex > i;

              return (
                <div
                  key={i}
                  className={`p-3 rounded-xl border transition-all ${
                    isCurrent
                      ? 'bg-purple-950/30 border-purple-500/60 shadow-[0_0_15px_rgba(139,92,246,0.2)]'
                      : 'bg-slate-900/60 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {isCurrent ? (
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                      ) : isFinished ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-600" />
                      )}
                      <span className="font-semibold text-slate-200">
                        {stg.stage_name}
                      </span>
                    </div>

                    <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 text-slate-300">
                      {stg.role}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1 pl-5">
                    <span className="font-mono text-purple-300">{stg.model_id}</span>
                    {stg.execution_time_ms && (
                      <span className="font-mono text-slate-500">{stg.execution_time_ms} ms</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Latest Turn Metrics */}
        {latestTurn && (
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <h4 className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Latest Turn Telemetry
            </h4>

            <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
              <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                <div className="text-slate-500 text-[10px]">Total Latency</div>
                <div className="text-slate-200 font-bold">{latestTurn.total_time_ms || 0} ms</div>
              </div>

              <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                <div className="text-slate-500 text-[10px]">Routing Latency</div>
                <div className="text-slate-200 font-bold">{latestTurn.routing_time_ms || 0.4} ms</div>
              </div>

              <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                <div className="text-slate-500 text-[10px]">Classification</div>
                <div className="text-slate-200 font-bold capitalize">{latestTurn.task_type || 'General'}</div>
              </div>

              <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                <div className="text-slate-500 text-[10px]">Complexity</div>
                <div className="text-slate-200 font-bold capitalize">{latestTurn.complexity || 'Standard'}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
