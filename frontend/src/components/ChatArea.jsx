import React, { useRef, useEffect } from 'react';
import { 
  Sparkles, 
  Code2, 
  ShieldCheck, 
  Cpu, 
  Layers, 
  ArrowRight,
  RotateCw,
  Terminal,
  Zap,
  Brain
} from 'lucide-react';
import SynoraLogo from './SynoraLogo';
import MessageItem from './MessageItem';
import ChatInput from './ChatInput';

export default function ChatArea({
  messages = [],
  isGenerating,
  streamingStage,
  streamingText,
  onSelectPrompt,
  onSendMessage,
  onStopGeneration,
  isSimulated,
  onToggleSimulation,
  selectedPreset,
  setSelectedPreset,
}) {
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, streamingText, streamingStage]);

  const promptSuggestions = [
    {
      title: 'Distributed Rate Limiter',
      desc: 'Build a token-bucket rate limiter for FastAPI with Redis & race condition safeguards.',
      prompt: 'Implement a distributed token-bucket rate limiter middleware in FastAPI using Redis, with race-condition safeguards and unit tests.'
    },
    {
      title: 'Memory Leak & Concurrency Audit',
      desc: 'Audit asynchronous worker pools for memory leaks on Apple Silicon M2.',
      prompt: 'Design an asynchronous task worker pool in Python that guarantees memory safety under 16GB RAM constraints and handles unexpected worker disconnects.'
    },
    {
      title: 'JWT Auth with Token Rotation',
      desc: 'Production-grade authentication system with refresh token hashing & revocation.',
      prompt: 'Write a production-grade JWT authentication service with refresh token rotation, bcrypt password hashing, and role-based access control.'
    },
    {
      title: 'Multi-Model Synthesis Explanation',
      desc: 'Explain how SYNORA routes across Qwen, DeepSeek, and Llama sequentially.',
      prompt: 'Explain the technical architecture of SYNORA AI: how does sequential multi-model orchestration with keep_alive=0 achieve consensus without exceeding 16GB VRAM?'
    }
  ];

  return (
    <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
      {/* Scrollable Messages Container */}
      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl px-4 py-6">
          {messages.length === 0 ? (
            /* Empty State / Welcome Hero */
            <div className="py-6 space-y-10 animate-fade-in">
              {/* Hero Branding */}
              <div className="text-center space-y-4">
                <div className="flex justify-center">
                  <SynoraLogo size="lg" showTagline={false} />
                </div>

                <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-purple-400 via-sky-300 to-cyan-400 bg-clip-text text-transparent">
                  Many Minds. One Intelligence.
                </h1>

                <p className="text-slate-400 text-sm md:text-base max-w-xl mx-auto leading-relaxed">
                  SYNORA unifies open-weight AI models into one coherent intelligence. A specialist proposes, a peer reviewer audits for security and edge cases, and a synthesizer outputs one flawless solution.
                </p>
              </div>

              {/* Three-Stage Architecture Pill Bar */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-purple-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-purple-400 font-semibold text-xs">
                    <Code2 className="w-4 h-4" />
                    <span>1. Specialist Proposal</span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Coding or domain specialist (e.g. Qwen2.5-Coder) establishes the core algorithm and system architecture.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs">
                    <ShieldCheck className="w-4 h-4" />
                    <span>2. Reviewer & Critic Audit</span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Reasoning auditor (e.g. DeepSeek-R1) aggressively checks logic bugs, memory limits, and security vulnerabilities.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-blue-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-blue-400 font-semibold text-xs">
                    <Brain className="w-4 h-4" />
                    <span>3. Unified Synthesis</span>
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Synthesizer (e.g. Llama 3.1) integrates peer fixes into one definitive, production-ready final response.
                  </p>
                </div>
              </div>

              {/* Prompt Suggestions */}
              <div className="space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  <span>Suggested Explorations</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {promptSuggestions.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSelectPrompt(item.prompt)}
                      className="p-3.5 rounded-xl bg-slate-900/50 hover:bg-slate-900/90 border border-slate-800 hover:border-purple-500/40 text-left transition-all group flex flex-col justify-between space-y-2 shadow-sm"
                    >
                      <div>
                        <div className="font-semibold text-slate-200 text-xs group-hover:text-purple-300 transition-colors">
                          {item.title}
                        </div>
                        <div className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                          {item.desc}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 text-[11px] text-purple-400 font-medium group-hover:translate-x-1 transition-transform">
                        <span>Try prompt</span>
                        <ArrowRight className="w-3 h-3" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Conversation Message Feed */
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <MessageItem key={index} message={msg} />
              ))}

              {/* Active Generation Streaming Banner & Typing Preview */}
              {isGenerating && (
                <div className="my-6 animate-fade-in space-y-3">
                  {/* Stage Progress Indicator */}
                  {streamingStage && (
                    <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-500/40 flex items-center justify-between text-xs text-slate-300 shadow-[0_0_15px_rgba(139,92,246,0.15)]">
                      <div className="flex items-center gap-2.5">
                        <RotateCw className="w-4 h-4 text-cyan-400 animate-spin" />
                        <span className="font-semibold text-slate-200">
                          {streamingStage.stage_name || 'Executing Multi-Model Stage'}
                        </span>
                        <span className="font-mono text-purple-300 text-[11px]">
                          ({streamingStage.model_id})
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono text-[11px]">
                        Sequential M2 Pipeline
                      </span>
                    </div>
                  )}

                  {/* Streaming Tokens Display */}
                  {streamingText && (
                    <div className="flex gap-4">
                      <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600/30 via-slate-800 to-cyan-500/20 border border-purple-500/40 flex items-center justify-center shrink-0">
                        <Sparkles className="w-4 h-4 text-purple-300 animate-pulse" />
                      </div>
                      <div className="flex-1 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 synora-prose text-slate-100 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                        {streamingText}
                        <span className="inline-block w-1.5 h-4 ml-1 bg-cyan-400 animate-pulse" />
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>
          )}
        </div>
      </div>

      {/* Chat input */}
      <div className="shrink-0 border-t border-white/10 bg-[#07090E]">
        <div className="mx-auto max-w-4xl p-4">
          <ChatInput
            onSendMessage={onSendMessage}
            isGenerating={isGenerating}
            onStopGeneration={onStopGeneration}
            isSimulated={isSimulated}
            onToggleSimulation={onToggleSimulation}
            selectedPreset={selectedPreset}
            setSelectedPreset={setSelectedPreset}
          />
        </div>
      </div>
    </div>
  );
}
