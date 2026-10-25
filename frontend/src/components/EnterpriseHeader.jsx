import React from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  Layers, 
  UserCheck, 
  History, 
  Plus, 
  RotateCcw,
  Zap,
  Database,
  Cpu,
  Activity
} from 'lucide-react';


export default function EnterpriseHeader({ 
  currentView, 
  onViewChange, 
  pendingCount, 
  onNewClaim, 
  onResetDb, 
  isResetting 
}) {
  return (
    <header className="top-nav">
      <div className="top-nav-brand">
        <div className="brand-shield">
          <Shield size={18} color="#ffffff" />
        </div>
        <div>
          <div className="brand-text">
            <span>AegisFlow</span>
            <span className="brand-tag">Claims Intelligence</span>
          </div>
        </div>
      </div>

      {/* Main Navigation Views */}
      <nav className="nav-links-group">
        <button 
          className={`nav-tab-btn ${currentView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onViewChange('dashboard')}
        >
          <LayoutDashboard size={15} />
          <span>Dashboard</span>
        </button>

        <button 
          className={`nav-tab-btn ${currentView === 'workbench' ? 'active' : ''}`}
          onClick={() => onViewChange('workbench')}
        >
          <Layers size={15} />
          <span>Claims Workbench</span>
        </button>

        <button 
          className={`nav-tab-btn ${currentView === 'reviews' ? 'active' : ''}`}
          onClick={() => onViewChange('reviews')}
        >
          <UserCheck size={15} />
          <span>Review Queue</span>
          {pendingCount > 0 && (
            <span className="nav-badge-count">{pendingCount}</span>
          )}
        </button>

        <button 
          className={`nav-tab-btn ${currentView === 'audit' ? 'active' : ''}`}
          onClick={() => onViewChange('audit')}
        >
          <History size={15} />
          <span>Audit Log</span>
        </button>
      </nav>

      {/* System Status & Actions */}
      <div className="system-status-pills">
        <div className="status-pill">
          <div className="status-dot-pulse" />
          <span>Core :8000</span>
        </div>

        <div className="status-pill" style={{ color: '#818cf8' }}>
          <Zap size={12} color="#818cf8" />
          <span>Gemini 2.5</span>
        </div>

        <div className="status-pill" style={{ color: '#fbbf24' }}>
          <Database size={12} color="#fbbf24" />
          <span>FTS5 RAG</span>
        </div>

        <a 
          href="https://us.cloud.langfuse.com" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="status-pill" 
          style={{ color: '#ec4899', textDecoration: 'none', border: '1px solid rgba(236, 72, 153, 0.3)', background: 'rgba(236, 72, 153, 0.08)' }}
          title="Open Langfuse Tracing Dashboard in Cloud"
        >
          <Activity size={12} color="#ec4899" />
          <span>Langfuse Live</span>
        </a>

        <div 
          className="status-pill" 
          style={{ color: '#06b6d4', border: '1px solid rgba(6, 182, 212, 0.3)', background: 'rgba(6, 182, 212, 0.08)' }}
          title="OpenTelemetry Distributed Tracing & Metric Instruments Active"
        >
          <Cpu size={12} color="#06b6d4" />
          <span>OTel Active</span>
        </div>


        <button 
          onClick={onResetDb}
          className="btn-ui btn-ui-subtle"
          title="Reset demo claims to clean state"
          disabled={isResetting}
          style={{ padding: '0.35rem 0.7rem', fontSize: '0.72rem' }}
        >
          <RotateCcw size={12} />
          <span>{isResetting ? 'Resetting...' : 'Reset DB'}</span>
        </button>

        <button 
          onClick={onNewClaim}
          className="btn-ui btn-ui-primary"
          style={{ padding: '0.35rem 0.8rem', fontSize: '0.75rem' }}
        >
          <Plus size={13} />
          <span>Submit Claim</span>
        </button>
      </div>
    </header>
  );
}
