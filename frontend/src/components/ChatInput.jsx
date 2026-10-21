import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Square, 
  Sparkles, 
  Layers, 
  Zap, 
  Sliders, 
  CornerDownLeft 
} from 'lucide-react';

export default function ChatInput({
  onSendMessage,
  isGenerating,
  onStopGeneration,
  isSimulated,
  onToggleSimulation,
  selectedPreset,
  setSelectedPreset,
}) {
  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [prompt]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    onSendMessage(prompt.trim());
    setPrompt('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full">
      <div className="glass-input rounded-2xl p-2.5 transition-all relative border border-slate-700/80 focus-within:border-purple-500/60 shadow-xl">
        {/* Preset & Simulation Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-2 pb-2 border-b border-slate-800/80 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 flex items-center gap-1 text-[11px]">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              Routing Mode:
            </span>
            <select
              value={selectedPreset}
              onChange={(e) => setSelectedPreset(e.target.value)}
              className="bg-slate-900 border border-slate-700/70 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-purple-500"
            >
              <option value="auto">Auto Orchestrator (Dynamic Classification)</option>
              <option value="coding">Manual Override: Coding Trio (Qwen + DeepSeek + Llama)</option>
              <option value="reasoning">Manual Override: Reasoning Focus (DeepSeek + Llama)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleSimulation}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                isSimulated
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
              }`}
              title="Toggle Simulated responses while Ollama models are actively downloading"
            >
              <Zap className={`w-3 h-3 ${isSimulated ? 'text-amber-400' : 'text-slate-500'}`} />
              <span>{isSimulated ? 'Simulation Active' : 'Real Inference'}</span>
            </button>
          </div>
        </div>

        {/* Text Input Row */}
        <div className="flex items-end gap-2 pt-2 px-1">
          <textarea
            ref={textareaRef}
            rows={1}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask SYNORA AI anything (e.g. 'Build a distributed rate limiter in Python' or 'Analyze race conditions')..."
            className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 text-sm resize-none focus:outline-none max-h-48 leading-relaxed py-1 px-1"
            disabled={isGenerating}
          />

          {isGenerating ? (
            <button
              onClick={onStopGeneration}
              className="p-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition-all shrink-0 flex items-center justify-center shadow-lg shadow-rose-900/30"
              title="Stop Generation"
            >
              <Square className="w-4 h-4 fill-white" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!prompt.trim()}
              className={`p-2.5 rounded-xl transition-all shrink-0 flex items-center justify-center ${
                prompt.trim()
                  ? 'bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 text-white shadow-lg shadow-purple-900/40 hover:brightness-110 active:scale-95'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed'
              }`}
              title="Send message"
              id="btn-send-message"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Input Footer Note */}
        <div className="flex items-center justify-between px-2 pt-2 text-[10px] text-slate-500">
          <span>SYNORA v0.4 Multi-Model Engine</span>
          <span className="flex items-center gap-1">
            <span>Press</span>
            <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">Enter</kbd>
            <span>to send,</span>
            <kbd className="px-1 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">Shift+Enter</kbd>
            <span>for new line</span>
          </span>
        </div>
      </div>
    </div>
  );
}
