import React from 'react';
import { 
  Menu, 
  Settings as SettingsIcon, 
  Activity, 
  Cpu, 
  Zap, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle,
  Radio
} from 'lucide-react';
import SynoraLogo from './SynoraLogo';

export default function Header({
  sidebarOpen,
  setSidebarOpen,
  onOpenSettings,
  activityOpen,
  setActivityOpen,
  health,
  settings,
  onToggleSimulation,
  activeModelsCount = 3,
  latestMetrics,
}) {
  const isSimulated = Boolean(settings?.allow_simulation);
  const ollamaStatus = health?.ollama?.status;
  const isOllamaConnected = ollamaStatus === 'connected';

  return (
    <header className="h-16 px-4 md:px-6 glass-header flex items-center justify-between z-30 shrink-0">
      {/* Left: Hamburger & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          title="Toggle Sidebar"
          id="btn-toggle-sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        <SynoraLogo size="sm" showTagline={true} />
      </div>

      {/* Center: System Status & Pipeline Info */}
      <div className="hidden lg:flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/60 text-xs">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isOllamaConnected ? 'bg-emerald-400' : isSimulated ? 'bg-amber-400' : 'bg-rose-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isOllamaConnected ? 'bg-emerald-500' : isSimulated ? 'bg-amber-500' : 'bg-rose-500'
              }`}
            />
          </span>

          <span className="text-slate-300 font-medium">
            {isOllamaConnected ? (
              <span className="text-emerald-400">Ollama Ready</span>
            ) : isSimulated ? (
              <span className="text-amber-400">Simulation / Dev Mode</span>
            ) : (
              <span className="text-rose-400">Ollama Awaiting Models</span>
            )}
          </span>

          <span className="text-slate-600">|</span>

          <span className="text-slate-400 flex items-center gap-1 font-mono text-[11px]">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            16GB M2 Safe (1-at-a-time)
          </span>
        </div>
      </div>

      {/* Right: Quick actions */}
      <div className="flex items-center gap-2">
        {/* Simulation Mode Quick Toggle */}
        <button
          onClick={onToggleSimulation}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
            isSimulated
              ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 hover:bg-amber-500/25'
              : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
          title="Toggle Simulation mode for instant testing while models download"
          id="btn-toggle-simulation"
        >
          <Zap className={`w-3.5 h-3.5 ${isSimulated ? 'text-amber-400 fill-amber-400/20' : 'text-slate-400'}`} />
          <span>{isSimulated ? 'Sim Mode: ON' : 'Sim Mode: OFF'}</span>
        </button>

        {/* Model Activity Button */}
        <button
          onClick={() => setActivityOpen(!activityOpen)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
            activityOpen
              ? 'bg-purple-600/20 border-purple-500/50 text-purple-200 shadow-[0_0_15px_rgba(168,85,247,0.25)]'
              : 'bg-slate-900/60 border-slate-700/60 text-slate-300 hover:text-white hover:bg-slate-800/60'
          }`}
          title="Open Model Activity & Orchestration Trace Drawer"
          id="btn-model-activity"
        >
          <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span className="hidden sm:inline">Model Activity</span>
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors border border-transparent hover:border-slate-700"
          title="SYNORA Settings & Model Management"
          id="btn-settings"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
