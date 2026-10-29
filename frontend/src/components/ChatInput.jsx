import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Square, 
  Sparkles, 
  Layers, 
  Zap, 
  Sliders, 
  Paperclip,
  X,
  FileText,
  FileCode,
  Image as ImageIcon,
  Film,
  File,
  CornerDownLeft 
} from 'lucide-react';

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

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
  const [attachments, setAttachments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [prompt]);

  const processFile = async (file) => {
    const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|svg)$/i.test(file.name);
    const isVideo = file.type.startsWith('video/') || /\.(mp4|mov|webm|mkv|avi)$/i.test(file.name);
    const isCodeOrMarkdown = file.type.startsWith('text/') || /\.(md|txt|py|js|ts|jsx|tsx|json|csv|html|css|yaml|yml|sh|sql|rs|go|c|cpp|h)$/i.test(file.name);

    let category = 'document';
    if (isImage) category = 'image';
    else if (isVideo) category = 'video';
    else if (file.name.endsWith('.md')) category = 'markdown';
    else if (isCodeOrMarkdown) category = 'code';

    return new Promise((resolve) => {
      const reader = new FileReader();

      if (isCodeOrMarkdown && !isImage) {
        reader.onload = (e) => {
          resolve({
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            name: file.name,
            size: file.size,
            type: file.type || 'text/plain',
            category,
            text_content: e.target.result,
            content: e.target.result,
          });
        };
        reader.readAsText(file);
      } else {
        reader.onload = (e) => {
          resolve({
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            name: file.name,
            size: file.size,
            type: file.type || (isVideo ? 'video/mp4' : 'image/png'),
            category,
            data_url: e.target.result,
            content: e.target.result,
          });
        };
        reader.readAsDataURL(file);
      }
    });
  };

  const handleFilesAdded = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const newItems = [];
    for (let i = 0; i < fileList.length; i++) {
      try {
        const item = await processFile(fileList[i]);
        newItems.push(item);
      } catch (err) {
        console.error('Failed reading file:', fileList[i].name, err);
      }
    }
    setAttachments(prev => [...prev, ...newItems]);
  };

  const handleFileChange = (e) => {
    handleFilesAdded(e.target.files);
    e.target.value = '';
  };

  const handleRemoveAttachment = (id) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if ((!prompt.trim() && attachments.length === 0) || isGenerating) return;

    onSendMessage(prompt.trim(), attachments);
    setPrompt('');
    setAttachments([]);
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
    <div 
      className="w-full"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input 
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        multiple
        className="hidden"
        accept="*/*"
      />

      <div className={`glass-input rounded-2xl p-2.5 transition-all relative border shadow-xl ${
        isDragging 
          ? 'border-purple-400 bg-purple-950/20 ring-2 ring-purple-500/40' 
          : 'border-slate-700/80 focus-within:border-purple-500/60'
      }`}>
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
              <option value="auto">Auto Orchestrator (Conversational & Multi-Model)</option>
              <option value="agent">⚡ Autonomous Agent Mode (Claw Code Tools & Execution)</option>
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

        {/* Attachment Chips Preview Bar */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-2 py-2 border-b border-slate-800/60 max-h-36 overflow-y-auto">
            {attachments.map((att) => (
              <div 
                key={att.id}
                className="flex items-center gap-2 bg-slate-900/90 border border-purple-500/30 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 shadow-sm animate-fade-in group hover:border-purple-500/60"
              >
                {att.category === 'image' && att.data_url ? (
                  <img src={att.data_url} alt={att.name} className="w-6 h-6 rounded object-cover border border-slate-700" />
                ) : att.category === 'video' ? (
                  <Film className="w-4 h-4 text-rose-400 shrink-0" />
                ) : att.category === 'markdown' ? (
                  <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : att.category === 'code' ? (
                  <FileCode className="w-4 h-4 text-cyan-400 shrink-0" />
                ) : (
                  <File className="w-4 h-4 text-purple-400 shrink-0" />
                )}

                <div className="flex flex-col min-w-0">
                  <span className="truncate max-w-[140px] font-medium text-[11px]">{att.name}</span>
                  <span className="text-[9px] text-slate-400">{formatFileSize(att.size)}</span>
                </div>

                <button
                  type="button"
                  onClick={() => handleRemoveAttachment(att.id)}
                  className="text-slate-500 hover:text-rose-400 p-0.5 rounded transition-colors"
                  title="Remove attachment"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Text Input Row */}
        <div className="flex items-end gap-2 pt-2 px-1">
          {/* Universal Attachment Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-750 text-slate-400 hover:text-purple-300 transition-all shrink-0 flex items-center justify-center border border-slate-700 hover:border-purple-500/50"
            title="Attach file of any format (.md, video, screenshot, code, zip, pdf...)"
          >
            <Paperclip className="w-4 h-4" />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything, say 'Give me the reality check on...', or drag & drop .md, video, screenshots..."
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
              disabled={!prompt.trim() && attachments.length === 0}
              className={`p-2.5 rounded-xl transition-all shrink-0 flex items-center justify-center ${
                prompt.trim() || attachments.length > 0
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
          <span className="flex items-center gap-1.5">
            <span className="text-purple-400 font-medium">SYNORA AI</span>
            <span>• Universal Multimodal & Reality Check Engine</span>
          </span>
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
