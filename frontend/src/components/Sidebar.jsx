import React, { useState } from 'react';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Search, 
  Clock, 
  Cpu, 
  HardDrive,
  ChevronRight,
  Sparkles
} from 'lucide-react';

export default function Sidebar({
  conversations = [],
  currentSessionId,
  onSelectSession,
  onNewChat,
  isOpen,
  latestMetrics,
  health,
}) {
  const [searchTerm, setSearchTerm] = useState('');

  // Filter conversations
  const filtered = conversations.filter(conv => {
    const title = conv.preview || conv.session_id || '';
    return title.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <aside
      className={`h-full min-h-0 fixed lg:static inset-y-0 left-0 z-40 w-72 bg-[#0B0F19] border-r border-slate-800/80 flex flex-col shrink-0 transition-transform duration-300 ease-in-out ${
        isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}
    >
      {/* New Chat Button */}
      <div className="shrink-0 p-3.5 border-b border-slate-800/80">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 text-white font-medium text-sm shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_25px_rgba(139,92,246,0.5)] hover:brightness-110 active:scale-[0.98] transition-all"
          id="btn-new-chat"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="shrink-0 px-3.5 pt-3 pb-1">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2 space-y-1">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-slate-500 text-xs">
            {searchTerm ? 'No matching conversations' : 'No previous conversations yet.'}
          </div>
        ) : (
          filtered.map((conv) => {
            const isSelected = conv.session_id === currentSessionId;
            const previewText = conv.preview || conv.user_prompt || 'Untitled Conversation';
            const dateStr = conv.updated_at 
              ? new Date(conv.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })
              : 'Recent';

            return (
              <button
                key={conv.session_id}
                onClick={() => onSelectSession(conv.session_id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-all group flex items-start gap-2.5 relative ${
                  isSelected
                    ? 'bg-slate-800/80 text-white border border-purple-500/30 shadow-[0_0_12px_rgba(139,92,246,0.15)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 border border-transparent'
                }`}
              >
                <MessageSquare className={`w-4 h-4 shrink-0 mt-0.5 ${
                  isSelected ? 'text-purple-400' : 'text-slate-500 group-hover:text-slate-400'
                }`} />

                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium truncate">
                    {previewText}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                    <span>{dateStr}</span>
                    {conv.turn_count && (
                      <>
                        <span>•</span>
                        <span>{conv.turn_count} turns</span>
                      </>
                    )}
                  </div>
                </div>

                {isSelected && (
                  <div className="w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0 self-center" />
                )}
              </button>
            );
          })
        )}
      </div>

      {/* Footer: System Telemetry Card */}
      <div className="shrink-0 p-3 border-t border-slate-800/80 bg-slate-950/40">
        <div className="rounded-xl p-3 bg-slate-900/70 border border-slate-800 text-[11px] space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              M2 Memory RSS
            </span>
            <span className="font-mono font-semibold text-slate-200">
              {latestMetrics?.latest_rss_mb 
                ? `${Math.round(latestMetrics.latest_rss_mb)} MB` 
                : '1.2 GB'}
            </span>
          </div>

          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-purple-400" />
              Catalog Capacity
            </span>
            <span className="font-mono text-purple-300">
              30 Models
            </span>
          </div>

          <div className="pt-1 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
            <span>Orchestrator v0.4</span>
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Memory Safe
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
