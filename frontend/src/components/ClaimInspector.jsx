import React, { useState } from 'react';
import { 
  FileText, 
  BookOpen, 
  AlertTriangle, 
  CheckCircle2, 
  Code, 
  Info, 
  DollarSign,
  Car,
  Calendar,
  Hash
} from 'lucide-react';

export default function ClaimInspector({ claimState }) {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!claimState) {
    return (
      <div className="glass-panel inspector-panel" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>No claim selected. Click a scenario above or select a claim from history.</p>
      </div>
    );
  }

  const {
    claim_id,
    intake_data = {},
    policy_validation = {},
    fraud_report = {},
    risk_assessment = {},
    settlement_decision = {},
    route_reason = ''
  } = claimState;

  const citations = policy_validation.citations || [];
  const flags = fraud_report.flags || [];
  const approvedEst = risk_assessment.approved_estimate || 0;
  const deductible = policy_validation.deductible || 0;
  const depreciation = risk_assessment.depreciation || 0;
  const payout = settlement_decision.net_payout ?? settlement_decision.proposed_payout ?? 0;

  return (
    <div className="glass-panel inspector-panel">
      {/* Header */}
      <div className="inspector-header">
        <div>
          <div className="claim-id-lg">
            <span>{claim_id}</span>
            <span className="badge badge-blue">{intake_data.vehicle_make_model || 'Motor Vehicle'}</span>
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Policyholder: <strong style={{ color: '#fff' }}>{intake_data.claimant_name || 'N/A'}</strong> (Policy: {intake_data.policy_no})
          </div>
        </div>

        <button 
          onClick={() => setShowRawJson(!showRawJson)}
          className="btn-secondary"
          style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
        >
          <Code size={14} />
          <span>{showRawJson ? 'View Rich UI' : 'View Raw ClaimState'}</span>
        </button>
      </div>

      {showRawJson ? (
        <pre className="raw-state-block">
          {JSON.stringify(claimState, null, 2)}
        </pre>
      ) : (
        <>
          {/* Routing Reason Alert */}
          {route_reason && (
            <div style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              fontSize: '0.85rem',
              color: '#c7d2fe'
            }}>
              <Info size={18} color="#818cf8" style={{ flexShrink: 0 }} />
              <div><strong>Route Decision:</strong> {route_reason}</div>
            </div>
          )}

          {/* Metric Cards Row */}
          <div className="metric-cards-row">
            <div className="metric-box">
              <span className="metric-label">Claimed Amount</span>
              <span className="metric-amount">${(intake_data.claimed_amt || 0).toLocaleString()}</span>
              <span className="metric-sub">Loss: {intake_data.loss_type}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">OEM Approved</span>
              <span className="metric-amount" style={{ color: '#38bdf8' }}>${approvedEst.toLocaleString()}</span>
              <span className="metric-sub">Tier: {risk_assessment.risk_tier || 'N/A'}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Deductions</span>
              <span className="metric-amount" style={{ color: '#f59e0b' }}>
                ${(deductible + depreciation).toLocaleString()}
              </span>
              <span className="metric-sub">Ded: ${deductible} • Depr: ${depreciation}</span>
            </div>

            <div className="metric-box" style={{ borderColor: 'rgba(16, 185, 129, 0.3)', background: 'rgba(16, 185, 129, 0.04)' }}>
              <span className="metric-label" style={{ color: '#34d399' }}>Proposed Payout</span>
              <span className="metric-amount" style={{ color: '#34d399' }}>${payout.toLocaleString()}</span>
              <span className="metric-sub">
                {settlement_decision.txn_ref ? `Disbursed: ${settlement_decision.txn_ref}` : 'Subject to Approval'}
              </span>
            </div>
          </div>

          {/* Financial Calculation Formula Box */}
          <div style={{
            padding: '1rem',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.82rem'
          }}>
            <div style={{ color: 'var(--text-dim)', marginBottom: '0.35rem', textTransform: 'uppercase', fontSize: '0.7rem' }}>
              Deterministic Settlement Arithmetic
            </div>
            <div style={{ color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span>max(0,</span>
              <span style={{ color: '#38bdf8' }}>Approved ${approvedEst}</span>
              <span>-</span>
              <span style={{ color: '#f59e0b' }}>Deductible ${deductible}</span>
              <span>-</span>
              <span style={{ color: '#f59e0b' }}>Depreciation ${depreciation}</span>
              <span>)</span>
              <span>=</span>
              <strong style={{ color: '#34d399', fontSize: '1rem' }}>${payout.toFixed(2)}</strong>
            </div>
          </div>

          {/* Policy RAG Evidence */}
          <div className="evidence-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, fontSize: '0.9rem' }}>
                <BookOpen size={16} color="#818cf8" />
                <span>SQLite FTS5 Policy Evidence & Citations</span>
              </div>
              <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>Keyword RAG (No Hallucinations)</span>
            </div>

            {policy_validation.coverage_explanation && (
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1', fontStyle: 'italic', padding: '0.4rem 0' }}>
                "{policy_validation.coverage_explanation}"
              </div>
            )}

            {citations.length === 0 ? (
              <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', padding: '0.5rem 0' }}>
                No matching policy clauses indexed for this query.
              </div>
            ) : (
              citations.map((c, idx) => (
                <div key={idx} className="citation-item">
                  <div className="citation-header">
                    <span>{c.section_title}</span>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>Page {c.page_number}</span>
                  </div>
                  <div style={{ color: 'var(--text-muted)' }}>{c.chunk_text}</div>
                </div>
              ))
            )}
          </div>

          {/* Fraud & Forensics Checks */}
          <div className="evidence-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, fontSize: '0.9rem' }}>
                <AlertTriangle size={16} color={fraud_report.fraud_score >= 75 ? '#fb7185' : '#34d399'} />
                <span>Forensics & Image Integrity Verification</span>
              </div>
              <span className={`badge ${fraud_report.fraud_score >= 75 ? 'badge-rose' : 'badge-green'}`} style={{ fontSize: '0.7rem' }}>
                Fraud Score: {fraud_report.fraud_score || 0} / 100
              </span>
            </div>

            {flags.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '0.3rem' }}>
                {flags.map((flag, i) => (
                  <div key={i} style={{ 
                    fontSize: '0.8rem', 
                    color: '#fb7185', 
                    background: 'rgba(244, 63, 94, 0.08)',
                    padding: '0.35rem 0.6rem',
                    borderRadius: '4px'
                  }}>
                    • {flag}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#34d399', fontSize: '0.8rem' }}>
                ✓ No duplicate image hashes or EXIF timestamp anomalies detected.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
