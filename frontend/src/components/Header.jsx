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
  Radio,
  Terminal,
  MessageSquare
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
  currentView = 'chat',
  setCurrentView,
}) {
  const isSimulated = Boolean(settings?.allow_simulation);
  const ollamaStatus = health?.ollama?.status;
  const isOllamaConnected = ollamaStatus === 'connected';
  const isOmniRouteConnected = Boolean(health?.omniroute?.online || health?.omniroute?.status === 'connected');

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

      {/* Center: Dual Mode Switcher (SYNORA Chat vs Claw Code Studio) */}
      <div className="flex items-center gap-3">
        <div className="flex items-center bg-slate-900/90 border border-slate-800 rounded-xl p-1 shadow-inner">
          <button
            onClick={() => setCurrentView?.('chat')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              currentView === 'chat'
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Multi-Model Collaborative Chat"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">SYNORA Chat</span>
          </button>
          <button
            onClick={() => setCurrentView?.('claw')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              currentView === 'claw'
                ? 'bg-gradient-to-r from-purple-600 to-cyan-500 text-white shadow-md shadow-purple-900/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Claw Code Autonomous Coding Harness"
          >
            <Terminal className="w-3.5 h-3.5 text-cyan-300" />
            <span className="font-semibold">Claw Code Studio</span>
          </button>
        </div>

        {/* Dual Live Status Indicators: OmniRoute 376 & Claw Code */}
        <div className="hidden lg:flex items-center gap-2">
          {/* OmniRoute Status Pill */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-mono transition-all ${
              isOmniRouteConnected
                ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                : 'bg-slate-900/60 border-slate-800 text-slate-400'
            }`}
            title="OmniRoute AI Proxy Gateway with 376 LLM Providers and auto-fallbacks"
          >
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isOmniRouteConnected ? 'bg-cyan-400' : 'bg-amber-400'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isOmniRouteConnected ? 'bg-cyan-500' : 'bg-amber-500'
                }`}
              />
            </span>
            <span>⚡ OmniRoute: {isOmniRouteConnected ? `Online (${health?.omniroute?.models_count || 455})` : 'Connecting...'}</span>
          </div>

          {/* Claw Code Status Pill */}
          <div
            onClick={() => setCurrentView?.('claw')}
            className="cursor-pointer flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-[11px] font-mono hover:bg-purple-500/20 transition-all"
            title="Claw Code Autonomous Coding Harness & 12 Native Tools"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span>🦞 Claw Code: Active ({health?.claw_code?.tools_count || 12} Tools)</span>
          </div>
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
          <span className="hidden sm:inline">{isSimulated ? 'Sim: ON' : 'Sim: OFF'}</span>
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
          <span className="hidden sm:inline">Activity</span>
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
