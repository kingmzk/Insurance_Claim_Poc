import React, { useState } from 'react';
import { 
  FileCheck, 
  ShieldCheck, 
  Search, 
  Calculator, 
  CreditCard,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Cpu
} from 'lucide-react';

export default function AgentStateCanvas({ claimState }) {
  const [expandedNode, setExpandedNode] = useState(null);

  if (!claimState) {
    return (
      <div className="graph-pane" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
          Select a claim or execute a scenario to inspect the multi-agent graph.
        </p>
      </div>
    );
  }

  const {
    completeness = 0,
    missing_fields = [],
    policy_validation = {},
    fraud_report = {},
    risk_assessment = {},
    settlement_decision = {},
    current_status = 'UNKNOWN',
    route_reason = ''
  } = claimState;

  // Determine stage visual states
  const isIntakePassed = completeness === 1.0;
  const isPolicyPassed = policy_validation.active && policy_validation.eligible;
  const isFraudHalted = fraud_report.siu_escalate;
  const isStpSettled = settlement_decision.status === 'SIMULATED_STP';

  const toggleNode = (nodeKey) => {
    setExpandedNode(expandedNode === nodeKey ? null : nodeKey);
  };

  return (
    <div className="graph-pane">
      <div className="graph-pane-header">
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Cpu size={15} color="#3b82f6" />
            <span>Multi-Agent State Graph</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: '0.15rem' }}>
            LangGraph Orchestrator • Shared <code style={{ color: '#93c5fd' }}>ClaimState</code> Contract
          </div>
        </div>

        <span className="badge-tag badge-tag-stp" style={{ fontSize: '0.65rem' }}>
          {current_status}
        </span>
      </div>

      <div className="graph-nodes-stack">
        {/* Node 1: Intake Agent */}
        <div className={`node-card ${isIntakePassed ? 'active-success' : 'active-danger'}`}>
          <div className="node-header" onClick={() => toggleNode('intake')} style={{ cursor: 'pointer' }}>
            <div className="node-title-group">
              <div className="node-icon-avatar" style={{ color: isIntakePassed ? '#10b981' : '#f59e0b' }}>
                <FileCheck size={16} />
              </div>
              <div>
                <div className="node-step-label">Node 1 • Data Extraction</div>
                <div className="node-name">Claims Intake Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge-tag ${isIntakePassed ? 'badge-tag-stp' : 'badge-tag-info'}`}>
                {isIntakePassed ? '100% COMPLETE' : 'MISSING DOCS'}
              </span>
              {expandedNode === 'intake' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </div>

          <div className="node-metric-row">
            <div className="node-metric-item">
              <span className="node-metric-k">Completeness</span>
              <span className="node-metric-v">{Math.round(completeness * 100)}%</span>
            </div>
            <div className="node-metric-item">
              <span className="node-metric-k">VIN Verification</span>
              <span className="node-metric-v" style={{ fontSize: '0.7rem' }}>
                {claimState.intake_data?.vin ? 'PASS (17-CHAR)' : 'MISSING (HALT)'}
              </span>
            </div>
          </div>

          {expandedNode === 'intake' && (
            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', background: 'var(--bg-surface-1)', padding: '0.5rem', borderRadius: '4px', color: '#94a3b8' }}>
              <div>Missing Fields: {JSON.stringify(missing_fields)}</div>
              <div>Documents Attached: {claimState.intake_data?.documents?.length || 0}</div>
            </div>
          )}
        </div>

        {/* Gate 1 Connector */}
        <div className="graph-connector">
          <span className="gate-badge">
            {completeness < 1.0 ? '⛔ Gate 1: Completeness < 1.0 ➜ Halt (NEEDS_INFO)' : '▼ Gate 1 Passed: Complete'}
          </span>
        </div>

        {/* Node 2: Policy Validation Agent */}
        <div className={`node-card ${isPolicyPassed ? 'active-success' : (policy_validation.policy_no ? 'active-warning' : '')}`}>
          <div className="node-header" onClick={() => toggleNode('policy')} style={{ cursor: 'pointer' }}>
            <div className="node-title-group">
              <div className="node-icon-avatar" style={{ color: isPolicyPassed ? '#10b981' : '#f59e0b' }}>
                <ShieldCheck size={16} />
              </div>
              <div>
                <div className="node-step-label">Node 2 • FTS5 Keyword RAG</div>
                <div className="node-name">Policy Validation Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge-tag ${isPolicyPassed ? 'badge-tag-stp' : 'badge-tag-review'}`}>
                {isPolicyPassed ? 'ACTIVE & COVERED' : (policy_validation.policy_no ? 'EXCLUSION DRAFT' : 'WAITING')}
              </span>
              {expandedNode === 'policy' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </div>

          <div className="node-metric-row">
            <div className="node-metric-item">
              <span className="node-metric-k">Authoritative PAS Status</span>
              <span className="node-metric-v">{policy_validation.active ? 'ACTIVE' : (policy_validation.policy_no ? 'LAPSED/EXCL' : '—')}</span>
            </div>
            <div className="node-metric-item">
              <span className="node-metric-k">FTS5 Retrieved Clauses</span>
              <span className="node-metric-v">{policy_validation.citations?.length || 0} cited</span>
            </div>
          </div>

          {expandedNode === 'policy' && (
            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', background: 'var(--bg-surface-1)', padding: '0.5rem', borderRadius: '4px', color: '#94a3b8' }}>
              <div>Policy Deductible: ${policy_validation.deductible}</div>
              <div>Policy Limit: ${policy_validation.policy_limit}</div>
              <div>Coverage Rationale: {policy_validation.coverage_explanation?.slice(0, 120)}...</div>
            </div>
          )}
        </div>

        {/* Gate 2 Connector */}
        <div className="graph-connector">
          <span className="gate-badge">
            {!isPolicyPassed && policy_validation.policy_no ? '⛔ Gate 2: Ineligible ➜ Fast-Track to Settlement Denial Draft' : '▼ Gate 2 Passed: Coverage Verified'}
          </span>
        </div>

        {/* Node 3: Fraud Detection Agent */}
        <div className={`node-card ${isFraudHalted ? 'active-danger' : (fraud_report.fraud_score !== undefined ? 'active-success' : '')}`}>
          <div className="node-header" onClick={() => toggleNode('fraud')} style={{ cursor: 'pointer' }}>
            <div className="node-title-group">
              <div className="node-icon-avatar" style={{ color: isFraudHalted ? '#ef4444' : '#10b981' }}>
                <Search size={16} />
              </div>
              <div>
                <div className="node-step-label">Node 3 • Forensics & pHash</div>
                <div className="node-name">Fraud Detection Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge-tag ${isFraudHalted ? 'badge-tag-siu' : 'badge-tag-stp'}`}>
                {isFraudHalted ? 'SIU FREEZE (≥75)' : (fraud_report.fraud_score !== undefined ? 'PASSED (<25)' : 'WAITING')}
              </span>
              {expandedNode === 'fraud' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </div>

          <div className="node-metric-row">
            <div className="node-metric-item">
              <span className="node-metric-k">Composite Fraud Score</span>
              <span className="node-metric-v" style={{ color: isFraudHalted ? '#f87171' : '#34d399' }}>
                {fraud_report.fraud_score !== undefined ? `${fraud_report.fraud_score} / 100` : '—'}
              </span>
            </div>
            <div className="node-metric-item">
              <span className="node-metric-k">pHash Duplicate Match</span>
              <span className="node-metric-v" style={{ color: fraud_report.duplicate_matches?.length ? '#f87171' : 'var(--text-primary)' }}>
                {fraud_report.duplicate_matches?.length ? 'MATCH: CLM-2024-1102' : 'CLEAN'}
              </span>
            </div>
          </div>

          {expandedNode === 'fraud' && (
            <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', background: 'var(--bg-surface-1)', padding: '0.5rem', borderRadius: '4px', color: '#94a3b8' }}>
              <div>EXIF Timestamp Discrepancy: {fraud_report.exif_discrepancies?.length ? 'YES (Predates loss)' : 'NO'}</div>
              <div>Forensic Flags: {JSON.stringify(fraud_report.flags)}</div>
            </div>
          )}
        </div>

        {/* Gate 3 Connector */}
        <div className="graph-connector">
          <span className="gate-badge">
            {isFraudHalted ? '⛔ Gate 3: Score ≥ 75 ➜ Halt & Refer to SIU' : '▼ Gate 3 Passed: Fraud Cleared'}
          </span>
        </div>

        {/* Node 4: Risk Assessment Agent */}
        <div className={`node-card ${risk_assessment.risk_tier ? 'active-success' : ''}`}>
          <div className="node-header" onClick={() => toggleNode('risk')} style={{ cursor: 'pointer' }}>
            <div className="node-title-group">
              <div className="node-icon-avatar">
                <Calculator size={16} />
              </div>
              <div>
                <div className="node-step-label">Node 4 • OEM Valuation</div>
                <div className="node-name">Risk Assessment Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge-tag ${risk_assessment.risk_tier === 'LOW' ? 'badge-tag-stp' : 'badge-tag-review'}`}>
                {risk_assessment.risk_tier ? `${risk_assessment.risk_tier} RISK` : 'WAITING'}
              </span>
              {expandedNode === 'risk' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </div>

          <div className="node-metric-row">
            <div className="node-metric-item">
              <span className="node-metric-k">OEM Approved Estimate</span>
              <span className="node-metric-v">
                {risk_assessment.approved_estimate ? `$${risk_assessment.approved_estimate.toLocaleString()}` : '—'}
              </span>
            </div>
            <div className="node-metric-item">
              <span className="node-metric-k">Depreciation Schedule</span>
              <span className="node-metric-v">
                {risk_assessment.depreciation ? `$${risk_assessment.depreciation.toLocaleString()}` : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Connector to Settlement */}
        <div className="graph-connector">
          <span className="gate-badge">▼ Pass to Deterministic Settlement</span>
        </div>

        {/* Node 5: Settlement Agent */}
        <div className={`node-card ${isStpSettled ? 'active-success' : (settlement_decision.status ? 'active-warning' : '')}`}>
          <div className="node-header" onClick={() => toggleNode('settle')} style={{ cursor: 'pointer' }}>
            <div className="node-title-group">
              <div className="node-icon-avatar" style={{ color: isStpSettled ? '#10b981' : '#38bdf8' }}>
                <CreditCard size={16} />
              </div>
              <div>
                <div className="node-step-label">Node 5 • Deterministic Settlement</div>
                <div className="node-name">Settlement Agent</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge-tag ${isStpSettled ? 'badge-tag-stp' : 'badge-tag-review'}`}>
                {isStpSettled ? 'STP AUTO-PAID' : (settlement_decision.status || 'WAITING')}
              </span>
              {expandedNode === 'settle' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </div>

          <div className="node-metric-row">
            <div className="node-metric-item">
              <span className="node-metric-k">Net Payout Math</span>
              <span className="node-metric-v" style={{ color: '#38bdf8' }}>
                {settlement_decision.proposed_payout !== undefined ? `$${settlement_decision.proposed_payout.toLocaleString()}` : '—'}
              </span>
            </div>
            <div className="node-metric-item">
              <span className="node-metric-k">Simulated Txn Ref</span>
              <span className="node-metric-v" style={{ fontSize: '0.7rem' }}>
                {settlement_decision.txn_ref || 'PENDING APPROVAL'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
