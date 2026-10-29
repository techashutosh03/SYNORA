import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ClawStudio from './components/ClawStudio';
import ModelActivityDrawer from './components/ModelActivityDrawer';
import SettingsModal from './components/SettingsModal';
import ErrorBoundary from './components/ErrorBoundary';
import { 
  fetchHealth, 
  fetchSettings, 
  updateSettings, 
  fetchConversations, 
  fetchConversationTurns, 
  fetchMetrics,
  sendChatMessage,
  streamChatMessage,
  streamAgentTask
} from './services/api';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [currentView, setCurrentView] = useState('chat'); // 'chat' | 'claw'

  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [conversations, setConversations] = useState([]);
  
  const [currentSessionId, setCurrentSessionId] = useState(() => 'synora-' + Math.random().toString(36).substring(2, 9));
  const [messages, setMessages] = useState([]);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingStage, setStreamingStage] = useState(null);
  const [streamingText, setStreamingText] = useState('');
  const [activePipeline, setActivePipeline] = useState(null);
  const [latestTurn, setLatestTurn] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState('auto');

  const chatAbortControllerRef = useRef(null);

  // Load initial system data
  useEffect(() => {
    refreshAllData();
    return () => {
      if (chatAbortControllerRef.current) {
        chatAbortControllerRef.current.abort();
      }
    };
  }, []);

  const refreshAllData = async () => {
    try {
      const [hData, sData, mData, cData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchSettings().catch(() => null),
        fetchMetrics().catch(() => null),
        fetchConversations().catch(() => ({ conversations: [] }))
      ]);

      if (hData) setHealth(hData);
      if (sData) setSettings(sData);
      if (mData) setMetrics(mData);
      if (cData?.conversations) setConversations(cData.conversations);
    } catch (err) {
      console.warn('Error refreshing system data:', err);
    }
  };

  // Switch session
  const handleSelectSession = async (sessionId) => {
    setCurrentSessionId(sessionId);
    setStreamingText('');
    setStreamingStage(null);

    try {
      const res = await fetchConversationTurns(sessionId);
      if (res?.turns) {
        const formatted = [];
        for (const t of res.turns) {
          formatted.push({
            role: 'user',
            content: t.user_prompt || ''
          });
          formatted.push({
            role: 'assistant',
            content: t.final_response || '',
            models_used: t.models_used || [],
            total_time_ms: t.total_time_ms,
            memory_rss_mb: t.memory_rss_mb,
            orchestration_stages: t.orchestration_trace?.stages || [],
            evaluation: t.orchestration_trace?.evaluation || {},
            is_simulated: false
          });
        }
        setMessages(formatted);
      }
    } catch (err) {
      console.error('Failed loading session turns:', err);
    }
  };

  // Start new chat
  const handleNewChat = () => {
    const newId = 'synora-' + Math.random().toString(36).substring(2, 9);
    setCurrentSessionId(newId);
    setMessages([]);
    setStreamingText('');
    setStreamingStage(null);
    setLatestTurn(null);
    setActivePipeline(null);
    setIsGenerating(false);
  };

  // Quick toggle for simulation mode
  const handleToggleSimulation = async () => {
    const currentSim = settings?.allow_simulation ?? false;
    const nextSim = !currentSim;
    try {
      await updateSettings({ allow_simulation: nextSim });
      setSettings(prev => ({ ...prev, allow_simulation: nextSim }));
    } catch (err) {
      console.error('Failed toggling simulation:', err);
    }
  };

  // Send message with streaming
  const handleSendMessage = async (userPrompt) => {
    if (!userPrompt.trim() || isGenerating) return;

    // Add user message immediately
    const userMsg = { role: 'user', content: userPrompt };
    setMessages(prev => [...prev, userMsg]);
    setIsGenerating(true);
    setStreamingText('');
    setStreamingStage({ stage_name: 'Routing & Multi-Factor Fitness Analysis...', model_id: 'Intelligent Router' });

    const abortController = new AbortController();
    chatAbortControllerRef.current = abortController;

    // Direct autonomous agent execution if user selected 'agent' preset
    if (selectedPreset === 'agent') {
      try {
        await streamAgentTask({
          task: userPrompt,
          modelId: 'qwen2.5-coder:7b',
          workspaceRoot: '.',
          signal: abortController.signal,
          onStart: (d) => {
            setStreamingStage({
              stage_name: 'Claw Code Agent: Initializing Execution Loop',
              model_id: d?.model || 'qwen2.5-coder:7b'
            });
          },
          onThought: (d) => {
            setStreamingText(prev => prev + '\n🧠 ' + (d?.content || ''));
          },
          onToolStart: (d) => {
            setStreamingStage({
              stage_name: `Claw Tool: ${d?.tool}`,
              model_id: 'tool_executor'
            });
          },
          onToolResult: (d) => {
            const preview = typeof d?.output === 'string' ? d.output.slice(0, 150) : JSON.stringify(d?.output || '');
            setStreamingText(prev => prev + `\n🛠️ [${d?.tool}] ${preview}`);
          },
          onComplete: (d) => {
            const assistantMsg = {
              role: 'assistant',
              content: d?.final_response || 'Task completed successfully.',
              models_used: ['qwen2.5-coder:7b'],
              execution_mode: 'agent',
              simulated: true,
              error: false
            };
            setMessages(prev => [...prev, assistantMsg]);
            setIsGenerating(false);
            setStreamingText('');
            setStreamingStage(null);
            refreshAllData();
          },
          onError: (err) => {
            setIsGenerating(false);
            setStreamingText('');
            setStreamingStage(null);
            setActivePipeline(null);
            const errMsg = typeof err === 'string' ? err : (err?.message || JSON.stringify(err, null, 2));
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: `⚠️ Agent execution notice: ${errMsg}`,
              error: true
            }]);
          }
        });
      } catch (err) {
        setIsGenerating(false);
        setStreamingText('');
        setStreamingStage(null);
        setActivePipeline(null);
      } finally {
        chatAbortControllerRef.current = null;
      }
      return;
    }

    let customModels = null;
    if (selectedPreset === 'coding') {
      customModels = ['qwen2.5-coder:7b', 'deepseek-r1:7b', 'llama3.1:8b'];
    } else if (selectedPreset === 'reasoning') {
      customModels = ['deepseek-r1:7b', 'llama3.1:8b'];
    }

    let accumulatedText = '';
    let currentStages = [];
    const isSim = Boolean(settings?.allow_simulation);

    try {
      await streamChatMessage({
        prompt: userPrompt,
        sessionId: currentSessionId,
        customModels,
        simulate: isSim,
        signal: abortController.signal,
        onRouting: (data) => {
          setStreamingStage({
            stage_name: `Routing: ${String(data.task_type || 'GENERAL').toUpperCase()} (${data.complexity || 'standard'})`,
            model_id: 'Router'
          });
          setActivePipeline({
            stages: data.stages || [],
            currentStageIndex: 0,
            isRunning: true
          });
        },
        onStageStart: (data) => {
          setStreamingStage({
            stage_name: `Executing Stage ${data.stage_index + 1}: ${data.stage_name}`,
            model_id: data.model_id,
            role: data.role
          });
          setActivePipeline(prev => ({
            ...prev,
            currentStageIndex: data.stage_index,
            isRunning: true
          }));
        },
        onStageComplete: (data) => {
          currentStages.push(data);
        },
        onSynthesisStart: (data) => {
          setStreamingStage({
            stage_name: 'Synthesizing Consensus Response...',
            model_id: 'SYNORA Synthesis Engine'
          });
        },
        onToken: (chunk) => {
          accumulatedText += chunk;
          setStreamingText(accumulatedText);
        },
        onDone: (result) => {
          const assistantMsg = {
            role: 'assistant',
            content: result.final_response || accumulatedText,
            models_used: result.models_used || [],
            total_time_ms: result.total_time_ms,
            routing_time_ms: result.routing_time_ms,
            memory_rss_mb: result.memory_rss_mb,
            evaluation: result.evaluation,
            synthesis_insights: result.synthesis_insights,
            orchestration_stages: result.orchestration_stages || currentStages,
            execution_mode: result.execution_mode || (isSim ? 'simulated' : 'real'),
            simulated: result.simulated ?? isSim,
            is_simulated: result.simulated ?? isSim,
            error: false
          };

          setMessages(prev => [...prev, assistantMsg]);
          setLatestTurn(result);
          setIsGenerating(false);
          setStreamingText('');
          setStreamingStage(null);
          setActivePipeline(prev => ({ ...prev, isRunning: false }));

          fetchConversations().then(cData => {
            if (cData?.conversations) setConversations(cData.conversations);
          });
          fetchMetrics().then(mData => {
            if (mData) setMetrics(mData);
          });
        },
        onError: (err) => {
          console.warn('Inference notice from backend:', err);
          const errorTitle = err?.error || err?.detail?.error || 'Model Notice';
          const modelId = err?.model || err?.detail?.model;
          const installCmd = err?.install_command || err?.detail?.install_command;
          const suggestedInstall = err?.suggested_install || err?.detail?.suggested_install;
          let errorMessage = typeof err === 'string' ? err : (err?.message || err?.detail?.message);

          if (!errorMessage || typeof errorMessage !== 'string') {
            errorMessage = 'Ollama local models are offline or loading. Enable "Sim: ON" in the header to run in zero-install mode.';
          }

          if (suggestedInstall && Array.isArray(suggestedInstall) && suggestedInstall.length > 0) {
            errorMessage += `\n\nInstall using:\n\`\`\`bash\n${suggestedInstall.join('\n')}\n\`\`\``;
          } else if (installCmd && !errorMessage.includes('ollama pull')) {
            errorMessage += `\n\nInstall using:\n\`\`\`bash\n${installCmd}\n\`\`\``;
          }

          const assistantMsg = {
            role: 'assistant',
            error: true,
            content: `### ${errorTitle}\n\n${errorMessage}`,
            models_used: modelId ? [modelId] : [],
            simulated: false,
            execution_mode: 'real',
            orchestration_stages: []
          };

          setMessages(prev => [...prev, assistantMsg]);
          setIsGenerating(false);
          setStreamingText('');
          setStreamingStage(null);
          setActivePipeline(prev => ({ ...prev, isRunning: false }));
        }
      });
    } catch (err) {
      console.error('Fatal send message error:', err);
      setIsGenerating(false);
      setStreamingText('');
      setStreamingStage(null);
      setActivePipeline(prev => ({ ...prev, isRunning: false }));
    } finally {
      chatAbortControllerRef.current = null;
    }
  };

  const handleStopGeneration = () => {
    if (chatAbortControllerRef.current) {
      chatAbortControllerRef.current.abort();
    }
    setIsGenerating(false);
    setStreamingStage(null);
    if (streamingText) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: streamingText + '\n\n*(Generation stopped by user)*'
        }
      ]);
      setStreamingText('');
    }
  };

  return (
    <ErrorBoundary onReset={handleNewChat}>
      <div className="h-dvh w-full flex overflow-hidden bg-[#07090E] text-slate-100 font-sans relative">
        {/* Background ambient radiant glows */}
        <div className="radial-glow glow-violet w-[500px] h-[500px] -top-40 -left-40 pointer-events-none" />
        <div className="radial-glow glow-cyan w-[600px] h-[600px] -bottom-60 -right-60 pointer-events-none" />

        {/* Left Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          conversations={conversations}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          latestMetrics={metrics}
          health={health}
        />

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden relative z-10">
          <Header
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            activityOpen={activityOpen}
            setActivityOpen={setActivityOpen}
            onOpenSettings={() => setSettingsOpen(true)}
            health={health}
            settings={settings}
            onToggleSimulation={handleToggleSimulation}
            latestMetrics={metrics}
            currentView={currentView}
            setCurrentView={setCurrentView}
          />

          {currentView === 'claw' ? (
            <ClawStudio health={health} settings={settings} />
          ) : (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <ChatArea
                messages={messages}
                isGenerating={isGenerating}
                streamingStage={streamingStage}
                streamingText={streamingText}
                onSelectPrompt={handleSendMessage}
                onSendMessage={handleSendMessage}
                onStopGeneration={handleStopGeneration}
                isSimulated={settings?.allow_simulation}
                onToggleSimulation={handleToggleSimulation}
                selectedPreset={selectedPreset}
                setSelectedPreset={setSelectedPreset}
              />
            </div>
          )}
        </main>

        {/* Right Drawer: Model Activity */}
        <ModelActivityDrawer
          isOpen={activityOpen}
          onClose={() => setActivityOpen(false)}
          activePipeline={activePipeline}
          latestTurn={latestTurn}
          metrics={metrics}
          health={health}
        />

        {/* Settings Modal */}
        <SettingsModal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          settings={settings}
          onSettingsUpdated={refreshAllData}
          health={health}
        />
      </div>
    </ErrorBoundary>
  );
}
