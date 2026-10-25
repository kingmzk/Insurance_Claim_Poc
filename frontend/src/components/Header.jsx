import React from 'react';
import { Shield, Cpu, Database, CheckCircle, Zap } from 'lucide-react';

export default function Header({ stats, onNewClaimClick }) {
  return (
    <header className="app-header">
      <div className="logo-group">
        <div className="brand-badge">
          <Shield size={24} color="#ffffff" />
        </div>
        <div>
          <div className="brand-title">AegisFlow Claims AI</div>
          <div className="brand-subtitle">
            <span>Autonomous Multi-Agent Motor Claims</span>
            <span>•</span>
            <span style={{ color: '#818cf8', fontWeight: 600 }}>LangGraph + FTS5</span>
          </div>
        </div>
      </div>

      <div className="system-badges">
        <div className="badge badge-green">
          <div className="pulse-dot" />
          <span>FastAPI Online</span>
        </div>
        <div className="badge badge-blue">
          <Zap size={13} />
          <span>Gemini 2.5 Flash</span>
        </div>
        <div className="badge badge-amber">
          <Database size={13} />
          <span>SQLite FTS5 RAG</span>
        </div>
        <div className="badge badge-rose" style={{ background: 'rgba(255,255,255,0.05)', color: '#94a3b8', borderColor: 'rgba(255,255,255,0.1)' }}>
          <Cpu size={13} />
          <span>No MCP (Native Mocks)</span>
        </div>

        <button 
          onClick={onNewClaimClick}
          className="btn-primary"
          style={{ marginLeft: '1rem', padding: '0.45rem 1rem' }}
        >
          + Submit Claim
        </button>
      </div>
    </header>
  );
}
