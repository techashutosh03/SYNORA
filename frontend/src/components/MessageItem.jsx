import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Bot, 
  User, 
  Copy, 
  Check, 
  ChevronDown, 
  ChevronUp, 
  ShieldCheck, 
  Zap, 
  Cpu, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  Sparkles,
  Terminal,
  Code2,
  Share2
} from 'lucide-react';

/**
 * CodeBlock with syntax language pill and copy button
 */
function CodeBlock({ node, inline, className, children, ...props }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const codeContent = String(children).replace(/\n$/, '');

  if (inline) {
    return (
      <code className="bg-purple-950/40 text-purple-200 border border-purple-500/20 px-1.5 py-0.5 rounded text-[13px] font-mono" {...props}>
        {children}
      </code>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(codeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-4 rounded-xl overflow-hidden border border-slate-700/70 bg-[#0A0E17] group">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-400">
        <span className="font-mono text-[11px] uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
          <Code2 className="w-3.5 h-3.5" />
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Code Body */}
      <pre className="p-4 overflow-x-auto text-xs md:text-sm font-mono text-slate-200 leading-relaxed">
        <code>{codeContent}</code>
      </pre>
    </div>
  );
}

function ExecutionStatus({ message }) {
  if (message.is_agent_mode) {
    return (
      <span className="px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-[10px] font-medium flex items-center gap-1">
        <Terminal className="w-3 h-3 text-cyan-400" />
        Claw Agent Execution
      </span>
    );
  }

  if (message.error) {
    return (
      <span className="px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-400 text-[10px] font-medium flex items-center gap-1">
        <AlertTriangle className="w-3 h-3 text-rose-400" />
        Inference Failed
      </span>
    );
  }

  if (message.simulated === true || message.is_simulated === true || message.execution_mode === 'simulated') {
    return (
      <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[10px] font-medium flex items-center gap-1">
        <Zap className="w-3 h-3 text-amber-400" />
        Simulation — Not Evaluated
      </span>
    );
  }

  if (message.models_used && message.models_used.length > 1) {
    return (
      <span className="px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-[10px] font-medium flex items-center gap-1">
        <ShieldCheck className="w-3 h-3 text-cyan-400" />
        Multi-Model Review
      </span>
    );
  }

  return (
    <span className="px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-[10px] font-medium flex items-center gap-1">
      <Cpu className="w-3 h-3 text-purple-400" />
      Single Model Response
    </span>
  );
}

export default function MessageItem({ message }) {
  const isUser = message.role === 'user';
  const [traceExpanded, setTraceExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message.content || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 w-full my-4 animate-fade-in">
        <div className="flex flex-col items-end max-w-[85%] md:max-w-[75%]">
          <div className="px-4 py-3 rounded-2xl rounded-tr-sm bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-900/20 text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-slate-300">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Assistant turn
  const stages = message.orchestration_stages || [];
  const insights = message.synthesis_insights;
  const evaluation = message.evaluation;
  const modelsUsed = message.models_used || [];

  return (
    <div className="flex gap-4 w-full my-6 animate-fade-in group">
      {/* SYNORA Assistant Emblem Avatar */}
      <div className={`relative w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 shadow-lg ${
        message.error
          ? 'bg-rose-950/40 border-rose-500/50 shadow-rose-900/20'
          : 'bg-gradient-to-br from-purple-600/30 via-slate-800 to-cyan-500/20 border-purple-500/40 shadow-[0_0_15px_rgba(139,92,246,0.25)]'
      }`}>
        {message.error ? (
          <AlertTriangle className="w-4 h-4 text-rose-400" />
        ) : (
          <Sparkles className="w-4 h-4 text-purple-300" />
        )}
      </div>

      <div className="flex-1 min-w-0 space-y-3">
        {/* Header Metadata Ribbon */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-bold text-slate-200 tracking-wide flex items-center gap-1.5">
            SYNORA AI
          </span>

          {/* Qualitative Execution Status */}
          <ExecutionStatus message={message} />

          {message.task_type && !message.error && (
            <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700/80 text-purple-300 text-[10px] font-medium capitalize">
              {message.sub_domain ? `${message.task_type} · ${message.sub_domain}` : message.task_type}
            </span>
          )}

          {modelsUsed.length === 1 && !message.error && (
            <span className="px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300 text-[10px] font-mono">
              {modelsUsed[0]}
            </span>
          )}

          {modelsUsed.length > 1 && !message.error && (
            <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-[10px] font-mono">
              {modelsUsed.length} Models
            </span>
          )}

          {message.total_time_ms && (
            <span className="text-slate-500 text-[11px] font-mono flex items-center gap-1 ml-auto">
              <Clock className="w-3 h-3" />
              {message.total_time_ms} ms
            </span>
          )}
        </div>

        {/* Multi-Model Orchestration Accordion */}
        {stages.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden text-xs">
            <button
              onClick={() => setTraceExpanded(!traceExpanded)}
              className="w-full px-3.5 py-2.5 flex items-center justify-between bg-slate-900/90 hover:bg-slate-800/60 transition-colors text-slate-300"
            >
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="font-semibold text-slate-200">
                  Multi-Model Orchestration Pipeline
                </span>
                <span className="text-slate-500 text-[11px]">
                  ({stages.length} sequential stages executed)
                </span>
              </div>
              <div className="flex items-center gap-1 text-slate-400">
                <span className="text-[11px]">{traceExpanded ? 'Hide Trace' : 'View Pipeline'}</span>
                {traceExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </div>
            </button>

            {traceExpanded && (
              <div className="p-3 space-y-2.5 border-t border-slate-800 bg-[#0B0F19]/90">
                {stages.map((stage, sIdx) => {
                  const roleColor =
                    stage.role === 'specialist'
                      ? 'border-purple-500/40 text-purple-300 bg-purple-500/10'
                      : stage.role === 'reviewer'
                      ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                      : 'border-blue-500/40 text-blue-300 bg-blue-500/10';

                  return (
                    <div
                      key={sIdx}
                      className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/70 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-200 font-mono text-[11px]">
                            Stage {sIdx + 1}: {stage.stage_name}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono border ${roleColor}`}>
                            {stage.role}
                          </span>
                        </div>
                        <span className="text-slate-400 font-mono text-[10px]">
                          {stage.execution_time_ms} ms
                        </span>
                      </div>

                      <div className="text-[11px] font-mono text-slate-400">
                        Model: <span className="text-slate-200">{stage.model_id}</span>
                      </div>

                      {stage.preview && (
                        <div className="mt-1.5 p-2 rounded bg-slate-950/80 border border-slate-800/60 text-[11px] text-slate-400 font-mono line-clamp-3">
                          {stage.preview}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Synthesis Insights Summary */}
                {insights && (
                  <div className="mt-3 p-3 rounded-lg bg-gradient-to-r from-purple-950/30 to-indigo-950/30 border border-purple-500/20 text-[11px] space-y-1.5">
                    <div className="font-semibold text-purple-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                      Synthesis Insights:
                    </div>
                    {insights.proposal_focus && (
                      <p className="text-slate-300">
                        <strong className="text-slate-400">Specialist Focus:</strong> {insights.proposal_focus}
                      </p>
                    )}
                    {insights.critique_highlights?.length > 0 && (
                      <div>
                        <strong className="text-cyan-400">Reviewer Audit Points:</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-0.5 text-slate-300">
                          {insights.critique_highlights.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Primary Markdown Response */}
        <div className="synora-prose text-slate-100 text-sm leading-relaxed overflow-hidden">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code: CodeBlock,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Turn Action Bar */}
        <div className="flex items-center gap-2 pt-2 text-slate-500 text-xs opacity-70 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopyMessage}
            className="flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-800 hover:text-slate-300 transition-colors"
            title="Copy response"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
