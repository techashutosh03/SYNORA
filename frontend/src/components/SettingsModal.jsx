import React, { useState, useEffect } from 'react';
import { 
  X, 
  Settings, 
  Cpu, 
  HardDrive, 
  Zap, 
  Check, 
  Search, 
  Filter, 
  Radio, 
  AlertCircle,
  Copy,
  Layers,
  Sparkles
} from 'lucide-react';
import { fetchModels, selectActiveModels, updateSettings } from '../services/api';

export default function SettingsModal({
  isOpen,
  onClose,
  settings,
  onSettingsUpdated,
  health,
}) {
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModelIds, setSelectedModelIds] = useState([]);
  const [isSimulated, setIsSimulated] = useState(settings?.allow_simulation || false);
  const [saving, setSaving] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  useEffect(() => {
    setIsSimulated(settings?.allow_simulation || false);
  }, [settings]);

  useEffect(() => {
    if (isOpen) {
      loadModelCatalog();
    }
  }, [isOpen]);

  const loadModelCatalog = async () => {
    setLoadingModels(true);
    try {
      const res = await fetchModels();
      const all = res.models || [];
      setModels(all);
      const active = all.filter(m => m.is_active).map(m => m.id);
      setSelectedModelIds(active.length > 0 ? active : ['qwen2.5-coder:7b', 'deepseek-r1:7b', 'llama3.1:8b']);
    } catch (err) {
      console.error('Failed to load models:', err);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleToggleModel = (id) => {
    setSelectedModelIds(prev => 
      prev.includes(id) 
        ? (prev.length > 1 ? prev.filter(m => m !== id) : prev) 
        : [...prev, id]
    );
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await updateSettings({ allow_simulation: isSimulated });
      await selectActiveModels(selectedModelIds);
      onSettingsUpdated?.();
      onClose();
    } catch (err) {
      console.error('Failed to update settings:', err);
    } finally {
      setSaving(false);
    }
  };

  const categories = ['all', 'coding', 'reasoning', 'creative', 'general', 'math'];

  const filteredModels = models.filter(m => {
    const spec = (m.specialty || (m.specialties && m.specialties[0]) || 'general').toLowerCase();
    const matchesCat = activeCategory === 'all' || spec.includes(activeCategory);
    const matchesSearch = searchQuery === '' || 
      (m.name && m.name.toLowerCase().includes(searchQuery.toLowerCase())) || 
      (m.id && m.id.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  const copyDownloadCommand = () => {
    navigator.clipboard.writeText('ollama pull qwen2.5-coder:7b && ollama pull deepseek-r1:7b && ollama pull llama3.1:8b');
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-2xl bg-[#0B0F19] border border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">SYNORA AI Settings</h2>
              <p className="text-xs text-slate-400">Manage Models, M2 Memory Guardrails & Inference</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-300">
          {/* Simulation Toggle Section */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-semibold text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Simulation & Rapid UI Development Mode
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Generates realistic multi-model orchestration responses locally without waiting for large model downloads.
                </p>
              </div>

              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isSimulated}
                  onChange={(e) => setIsSimulated(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>
          </div>

          {/* Model Catalog Selector */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  Active Model Pool ({selectedModelIds.length} active)
                </h3>
                <p className="text-slate-400 text-xs">
                  Select which models participate in SYNORA's dynamic router.
                </p>
              </div>

              <div className="text-xs font-mono text-purple-400">
                {models.length} Cataloged
              </div>
            </div>

            {/* Filter Chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1 rounded-lg text-xs capitalize transition-colors ${
                    activeCategory === cat
                      ? 'bg-purple-600 text-white font-medium shadow-sm'
                      : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Search Box */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search models by name or id..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Models Grid */}
            <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
              {loadingModels ? (
                <div className="py-8 text-center text-slate-500">Loading catalog...</div>
              ) : (
                filteredModels.map(m => {
                  const isChecked = selectedModelIds.includes(m.id);
                  return (
                    <div
                      key={m.id}
                      onClick={() => handleToggleModel(m.id)}
                      className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                        isChecked
                          ? 'bg-purple-950/20 border-purple-500/40 text-white'
                          : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                          isChecked ? 'bg-purple-600 border-purple-500 text-white' : 'border-slate-700 bg-slate-800'
                        }`}>
                          {isChecked && <Check className="w-3 h-3" />}
                        </div>
                        <div>
                          <div className="font-semibold text-xs flex items-center gap-1.5">
                            {m.name}
                            <span className="font-mono text-[10px] text-purple-400">({m.parameter_size || m.parameters || 'Cloud'})</span>
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {m.id} • <span className="capitalize">{m.specialty || (m.specialties && m.specialties[0]) || 'general'}</span>{m.provider === 'omniroute' ? ' • ⚡ OmniRoute' : ' • 🦙 Ollama'}
                          </div>
                        </div>
                      </div>

                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 border border-slate-700/60 text-slate-300">
                        {m.recommended_role}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Ollama Terminal Setup Command */}
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5 text-xs">
                <HardDrive className="w-3.5 h-3.5 text-purple-400" />
                Starter Trio Download Command
              </span>
              <button
                onClick={copyDownloadCommand}
                className="flex items-center gap-1 text-[11px] text-purple-400 hover:text-purple-300"
              >
                {copiedCmd ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedCmd ? 'Copied' : 'Copy Command'}</span>
              </button>
            </div>
            <pre className="p-2.5 rounded-lg bg-black/60 border border-slate-800/80 text-[11px] font-mono text-purple-200 overflow-x-auto">
              ollama pull qwen2.5-coder:7b && ollama pull deepseek-r1:7b && ollama pull llama3.1:8b
            </pre>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-end gap-3 bg-slate-900/60">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-600 text-white font-medium text-xs shadow-lg shadow-purple-900/30 hover:brightness-110 active:scale-95 transition-all"
          >
            {saving ? 'Saving...' : 'Apply Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
