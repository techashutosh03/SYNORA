import React from 'react';
import { AlertTriangle, RefreshCw, MessageSquare, Terminal } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('SYNORA UI ErrorBoundary caught an unhandled render error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const errorMsg = this.state.error?.message || String(this.state.error || 'Unknown UI runtime exception');
      const componentStack = this.state.errorInfo?.componentStack || '';

      return (
        <div className="min-h-screen w-full bg-[#07090E] text-slate-100 flex items-center justify-center p-4 font-sans relative overflow-hidden">
          {/* Ambient Glows */}
          <div className="absolute top-1/4 -left-20 w-96 h-96 bg-rose-600/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

          <div className="max-w-xl w-full bg-slate-900/90 border border-rose-500/30 rounded-2xl p-6 md:p-8 shadow-2xl relative z-10 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-6 h-6 text-rose-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  UI Runtime Shield Activated
                </h2>
                <p className="text-slate-400 text-xs mt-0.5">
                  SYNORA gracefully caught an unexpected component error without crashing.
                </p>
              </div>
            </div>

            {/* Error Message Box */}
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="text-xs font-semibold text-rose-400 font-mono">
                {errorMsg}
              </div>
              {componentStack && (
                <details className="text-[11px] text-slate-500 mt-2">
                  <summary className="cursor-pointer hover:text-slate-300 transition-colors font-mono">
                    View Component Stack
                  </summary>
                  <pre className="mt-2 p-2 bg-slate-900/80 rounded font-mono text-[10px] overflow-x-auto whitespace-pre-wrap max-h-40 leading-relaxed text-slate-400">
                    {componentStack}
                  </pre>
                </details>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="flex-1 min-w-[140px] px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:brightness-110 text-white rounded-xl font-medium text-xs shadow-lg shadow-purple-900/30 flex items-center justify-center gap-2 transition-all active:scale-95"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Recover Interface</span>
              </button>

              <button
                onClick={this.handleReload}
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl font-medium text-xs border border-slate-700 transition-colors flex items-center justify-center gap-2"
              >
                <span>Reload Application</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
