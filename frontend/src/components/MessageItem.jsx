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
  Layers
} from 'lucide-react';

/**
 * Safely format any value into a clean display string
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

/**
 * CodeBlock with syntax language pill and copy button
 */
function CodeBlock({ node, inline, className, children, ...props }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const codeContent = String(children || '').replace(/\n$/, '');

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
  if (message.execution_mode === 'agent' || message.is_agent_mode) {
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
        Inference Notice
      </span>
    );
  }

  if (message.simulated === true || message.is_simulated === true || message.execution_mode === 'simulated') {
    return (
      <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[10px] font-medium flex items-center gap-1">
        <Zap className="w-3 h-3 text-amber-400" />
        Simulation / Dev Mode
      </span>
    );
  }

  if (message.models_used && message.models_used.length > 1) {
    return (
      <span className="px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-[10px] font-medium flex items-center gap-1">
        <ShieldCheck className="w-3 h-3 text-cyan-400" />
        Multi-Model Consensus
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

  const rawContent = message?.content;
  const contentText = safeString(rawContent);

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(contentText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 w-full my-4 animate-fade-in">
        <div className="flex flex-col items-end max-w-[85%] md:max-w-[75%]">
          <div className="px-4 py-3 rounded-2xl rounded-tr-sm bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-900/20 text-sm leading-relaxed whitespace-pre-wrap">
            {contentText}
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-slate-300 shadow-md">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Assistant turn
  const stages = Array.isArray(message.orchestration_stages) ? message.orchestration_stages : [];
  const insights = message.synthesis_insights || null;
  const evaluation = message.evaluation || null;
  const modelsUsed = Array.isArray(message.models_used) ? message.models_used : [];

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

          {message.total_time_ms != null && (
            <span className="text-slate-500 text-[11px] font-mono flex items-center gap-1 ml-auto">
              <Clock className="w-3 h-3" />
              {typeof message.total_time_ms === 'number' ? Math.round(message.total_time_ms) : message.total_time_ms} ms
            </span>
          )}
        </div>

        {/* Multi-Model Orchestration Accordion */}
        {stages.length > 0 && (
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 overflow-hidden text-xs">
            <button
              onClick={() => setTraceExpanded(!traceExpanded)}
              className="w-full px-3.5 py-2.5 flex items-center justify-between text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            >
              <span className="flex items-center gap-2 font-medium">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                <span>Multi-Model Pipeline Execution Trace ({stages.length} Stages)</span>
              </span>
              <span className="flex items-center gap-1 text-[11px] text-slate-500">
                <span>{traceExpanded ? 'Hide Trace' : 'Inspect Pipeline'}</span>
                {traceExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </span>
            </button>

            {traceExpanded && (
              <div className="p-3.5 border-t border-slate-800/80 space-y-3 bg-slate-950/50">
                {stages.map((stg, sIdx) => {
                  const stageName = safeString(stg.stage_name || `Stage ${sIdx + 1}`);
                  const modelId = safeString(stg.model_id || 'Model');
                  const role = safeString(stg.role || 'specialist');
                  const duration = stg.execution_time_ms != null ? `${Math.round(Number(stg.execution_time_ms))} ms` : null;

                  return (
                    <div key={sIdx} className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="font-semibold text-slate-200 font-mono text-[11px]">
                            {stageName}
                          </span>
                        </div>
                        <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono bg-purple-950/60 text-purple-300 border border-purple-800/40">
                          {role}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pl-5">
                        <span>Model: {modelId}</span>
                        {duration && <span>{duration}</span>}
                      </div>
                      {stg.preview && (
                        <p className="text-[11px] text-slate-400 italic pl-5 line-clamp-2">
                          "{safeString(stg.preview)}"
                        </p>
                      )}
                    </div>
                  );
                })}

                {/* Synthesis Insights */}
                {insights && (
                  <div className="p-3 rounded-lg bg-purple-950/20 border border-purple-500/30 text-[11px] space-y-1.5 text-slate-300">
                    {insights.proposal_focus && (
                      <p>
                        <strong className="text-purple-300">Proposal Focus:</strong> {safeString(insights.proposal_focus)}
                      </p>
                    )}
                    {Array.isArray(insights.critique_highlights) && insights.critique_highlights.length > 0 && (
                      <div>
                        <strong className="text-cyan-400">Reviewer Audit Points:</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-0.5">
                          {insights.critique_highlights.map((c, i) => (
                            <li key={i}>{safeString(c)}</li>
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
            {contentText}
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
