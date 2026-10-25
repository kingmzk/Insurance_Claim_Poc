import React from 'react';
import { 
  FileCheck, 
  ShieldCheck, 
  Search, 
  Calculator, 
  CreditCard,
  Check, 
  AlertTriangle, 
  XOctagon, 
  Clock 
} from 'lucide-react';

export default function PipelineVisualizer({ claimState }) {
  if (!claimState) {
    return (
      <div className="glass-panel pipeline-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Select or execute a scenario to inspect the multi-agent graph in real-time.</p>
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
    current_status = 'UNKNOWN'
  } = claimState;

  // Determine stage visual status
  const intakeStatus = completeness === 1.0 ? 'passed' : 'flagged';
  const policyStatus = !policy_validation.active || !policy_validation.eligible 
    ? (policy_validation.policy_no ? 'review' : 'idle') 
    : 'passed';
  const fraudStatus = fraud_report.siu_escalate 
    ? 'flagged' 
    : (fraud_report.fraud_score !== undefined ? 'passed' : 'idle');
  const riskStatus = risk_assessment.risk_tier 
    ? (risk_assessment.risk_tier === 'HIGH' ? 'review' : 'passed') 
    : 'idle';
  const settlementStatus = settlement_decision.status === 'SIMULATED_STP' 
    ? 'passed' 
    : (settlement_decision.status ? 'review' : 'idle');

  return (
    <div className="glass-panel pipeline-container">
      <div className="pipeline-header">
        <div className="pipeline-title">
          <span>Active Orchestration Flow</span>
          <span className="badge badge-blue" style={{ fontFamily: 'var(--font-mono)' }}>
            {claimState.claim_id}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Pipeline Outcome:</span>
          {current_status === 'SETTLED_STP' && (
            <span className="badge badge-green">
              <Check size={13} />
              <span>STP Auto-Disbursed</span>
            </span>
          )}
          {current_status === 'SETTLED_MANUAL' && (
            <span className="badge badge-green">
              <Check size={13} />
              <span>Settled by Adjuster</span>
            </span>
          )}
          {current_status === 'NEEDS_INFO' && (
            <span className="badge badge-amber">
              <AlertTriangle size={13} />
              <span>Gate 1: Needs Info</span>
            </span>
          )}
          {current_status === 'PENDING_REVIEW' && (
            <span className="badge badge-amber">
              <Clock size={13} />
              <span>HITL Review Required</span>
            </span>
          )}
          {current_status === 'DENIED_BY_ADJUSTER' && (
            <span className="badge badge-rose">
              <XOctagon size={13} />
              <span>Claim Denied</span>
            </span>
          )}
        </div>
      </div>

      <div className="pipeline-grid">
        {/* Node 1: Intake Agent */}
        <div className={`agent-node status-${intakeStatus}`}>
          <div className="agent-node-header">
            <div>
              <div className="agent-stage-sub">Stage 1</div>
              <div className="agent-name">Claims Intake</div>
            </div>
            <div className="agent-icon-box">
              <FileCheck size={18} />
            </div>
          </div>
          <div className="agent-details">
            <div className="agent-metric">
              <span>Completeness</span>
              <span className="agent-metric-val">{Math.round(completeness * 100)}%</span>
            </div>
            <div className="agent-metric">
              <span>VIN Extracted</span>
              <span className="agent-metric-val">{claimState.intake_data?.vin ? 'Verified' : 'Missing'}</span>
            </div>
            <div className="agent-metric">
              <span>Gate 1</span>
              <span className="agent-metric-val" style={{ color: completeness === 1.0 ? '#34d399' : '#f59e0b' }}>
                {completeness === 1.0 ? 'PASSED' : 'HALT (INFO)'}
              </span>
            </div>
          </div>
        </div>

        {/* Node 2: Policy Agent */}
        <div className={`agent-node status-${policyStatus}`}>
          <div className="agent-node-header">
            <div>
              <div className="agent-stage-sub">Stage 2</div>
              <div className="agent-name">Policy Validation</div>
            </div>
            <div className="agent-icon-box">
              <ShieldCheck size={18} />
            </div>
          </div>
          <div className="agent-details">
            <div className="agent-metric">
              <span>Policy Status</span>
              <span className="agent-metric-val">{policy_validation.active ? 'ACTIVE' : (policy_validation.policy_no ? 'LAPSED/EXCL' : '—')}</span>
            </div>
            <div className="agent-metric">
              <span>Deductible</span>
              <span className="agent-metric-val">${policy_validation.deductible || 0}</span>
            </div>
            <div className="agent-metric">
              <span>FTS5 Citations</span>
              <span className="agent-metric-val">{policy_validation.citations?.length || 0} clauses</span>
            </div>
          </div>
        </div>

        {/* Node 3: Fraud Agent */}
        <div className={`agent-node status-${fraudStatus}`}>
          <div className="agent-node-header">
            <div>
              <div className="agent-stage-sub">Stage 3</div>
              <div className="agent-name">Fraud Detection</div>
            </div>
            <div className="agent-icon-box">
              <Search size={18} />
            </div>
          </div>
          <div className="agent-details">
            <div className="agent-metric">
              <span>Fraud Score</span>
              <span className="agent-metric-val" style={{ color: fraud_report.fraud_score >= 75 ? '#fb7185' : '#34d399' }}>
                {fraud_report.fraud_score !== undefined ? `${fraud_report.fraud_score} / 100` : '—'}
              </span>
            </div>
            <div className="agent-metric">
              <span>Duplicates</span>
              <span className="agent-metric-val">{fraud_report.duplicate_matches?.length || 0} found</span>
            </div>
            <div className="agent-metric">
              <span>Gate 3</span>
              <span className="agent-metric-val" style={{ color: fraud_report.siu_escalate ? '#fb7185' : '#34d399' }}>
                {fraud_report.siu_escalate ? 'SIU FREEZE' : (fraud_report.fraud_score !== undefined ? 'PASSED' : '—')}
              </span>
            </div>
          </div>
        </div>

        {/* Node 4: Risk Agent */}
        <div className={`agent-node status-${riskStatus}`}>
          <div className="agent-node-header">
            <div>
              <div className="agent-stage-sub">Stage 4</div>
              <div className="agent-name">Risk Assessment</div>
            </div>
            <div className="agent-icon-box">
              <Calculator size={18} />
            </div>
          </div>
          <div className="agent-details">
            <div className="agent-metric">
              <span>OEM Approved</span>
              <span className="agent-metric-val">
                {risk_assessment.approved_estimate ? `$${risk_assessment.approved_estimate.toLocaleString()}` : '—'}
              </span>
            </div>
            <div className="agent-metric">
              <span>Depreciation</span>
              <span className="agent-metric-val">
                {risk_assessment.depreciation ? `$${risk_assessment.depreciation.toLocaleString()}` : '—'}
              </span>
            </div>
            <div className="agent-metric">
              <span>Risk Tier</span>
              <span className="agent-metric-val" style={{ color: risk_assessment.risk_tier === 'LOW' ? '#34d399' : '#fbbf24' }}>
                {risk_assessment.risk_tier || '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Node 5: Settlement Agent */}
        <div className={`agent-node status-${settlementStatus}`}>
          <div className="agent-node-header">
            <div>
              <div className="agent-stage-sub">Stage 5</div>
              <div className="agent-name">Settlement</div>
            </div>
            <div className="agent-icon-box">
              <CreditCard size={18} />
            </div>
          </div>
          <div className="agent-details">
            <div className="agent-metric">
              <span>Proposed Net</span>
              <span className="agent-metric-val" style={{ color: '#38bdf8' }}>
                {settlement_decision.proposed_payout !== undefined ? `$${settlement_decision.proposed_payout.toLocaleString()}` : '—'}
              </span>
            </div>
            <div className="agent-metric">
              <span>STP Gate 4</span>
              <span className="agent-metric-val">
                {settlement_decision.status === 'SIMULATED_STP' ? 'AUTO-PAY' : (settlement_decision.status ? 'ADJUSTER' : '—')}
              </span>
            </div>
            <div className="agent-metric">
              <span>Txn Ref</span>
              <span className="agent-metric-val" style={{ fontSize: '0.72rem' }}>
                {settlement_decision.txn_ref || 'PENDING'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
