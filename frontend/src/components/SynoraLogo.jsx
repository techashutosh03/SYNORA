import React from 'react';

export default function SynoraLogo({ size = 'md', showTagline = true, className = '' }) {
  const isSm = size === 'sm';
  const isLg = size === 'lg';

  const iconDim = isSm ? 28 : isLg ? 48 : 36;

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Radiant Nexus Icon */}
      <div className="relative flex items-center justify-center shrink-0">
        <div
          className={`absolute inset-0 rounded-full bg-gradient-to-tr from-purple-600 via-blue-500 to-cyan-400 blur-md opacity-60 animate-pulse-subtle`}
          style={{ width: iconDim, height: iconDim }}
        />
        <svg
          width={iconDim}
          height={iconDim}
          viewBox="0 0 100 100"
          className="relative z-10 drop-shadow-lg"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="synoraGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#A855F7" />
              <stop offset="50%" stopColor="#3B82F6" />
              <stop offset="100%" stopColor="#06B6D4" />
            </linearGradient>
            <radialGradient id="centerGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="40%" stopColor="#38BDF8" />
              <stop offset="100%" stopColor="#6366F1" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Outer Ring */}
          <circle cx="50" cy="50" r="44" stroke="url(#synoraGrad)" strokeWidth="2.5" strokeOpacity="0.75" />

          {/* Connected Neural Links */}
          <line x1="50" y1="26" x2="28" y2="68" stroke="url(#synoraGrad)" strokeWidth="2.5" strokeDasharray="3 3" />
          <line x1="50" y1="26" x2="72" y2="68" stroke="url(#synoraGrad)" strokeWidth="2.5" strokeDasharray="3 3" />
          <line x1="28" y1="68" x2="72" y2="68" stroke="url(#synoraGrad)" strokeWidth="2.5" strokeDasharray="3 3" />

          {/* Model Node 1: Specialist (Violet) */}
          <circle cx="50" cy="26" r="10" fill="#8B5CF6" />
          <circle cx="50" cy="26" r="5" fill="#DDD6FE" />

          {/* Model Node 2: Reviewer (Cyan) */}
          <circle cx="28" cy="68" r="9" fill="#06B6D4" />
          <circle cx="28" cy="68" r="4.5" fill="#CFFAFE" />

          {/* Model Node 3: Synthesizer (Blue) */}
          <circle cx="72" cy="68" r="9" fill="#3B82F6" />
          <circle cx="72" cy="68" r="4.5" fill="#DBEAFE" />

          {/* Central Synthesis Intelligence Core */}
          <circle cx="50" cy="54" r="8" fill="url(#centerGlow)" className="animate-ping" style={{ transformOrigin: '50px 54px', animationDuration: '3s' }} />
          <circle cx="50" cy="54" r="6" fill="#FFFFFF" />
        </svg>
      </div>

      {/* Brand Text */}
      <div className="flex flex-col">
        <div className="flex items-center gap-1.5">
          <span className={`font-black tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent ${
            isSm ? 'text-base' : isLg ? 'text-2xl tracking-wider' : 'text-lg tracking-wide'
          }`}>
            SYNORA
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-300 border border-purple-500/30">
            AI
          </span>
        </div>
        {showTagline && (
          <span className={`text-slate-400 font-medium ${isSm ? 'text-[10px]' : isLg ? 'text-xs' : 'text-[11px]'}`}>
            Many Minds. One Intelligence.
          </span>
        )}
      </div>
    </div>
  );
}
