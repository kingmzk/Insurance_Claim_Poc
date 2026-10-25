import React, { useState } from 'react';
import { 
  Calculator, 
  BookOpen, 
  ShieldAlert, 
  History, 
  Check, 
  X, 
  MessageSquare, 
  AlertTriangle,
  Info,
  DollarSign,
  Calendar,
  ExternalLink
} from 'lucide-react';

export default function DossierStudio({ claimState, reviewTasks, onRecordDecision, isSubmitting }) {
  const [activeTab, setActiveTab] = useState('adjudication');
  const [adjusterNote, setAdjusterNote] = useState('');
  const [adjustedAmount, setAdjustedAmount] = useState('');

  if (!claimState) {
    return (
      <div className="dossier-pane" style={{ justifyContent: 'center', alignItems: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>Select a claim to open the Adjudication Dossier.</p>
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
    current_status = 'UNKNOWN',
    route_reason = '',
    audit_events = []
  } = claimState;

  const approvedEst = risk_assessment.approved_estimate || 0;
  const deductible = policy_validation.deductible || 0;
  const depreciation = risk_assessment.depreciation || 0;
  const proposedPayout = settlement_decision.net_payout ?? settlement_decision.proposed_payout ?? 0;

  // Find if this claim has an active review task
  const activeTask = reviewTasks.find(t => t.claim_id === claim_id && t.status === 'PENDING');

  const handleDecision = (decisionType) => {
    if (!activeTask) return;
    const payoutToSubmit = adjustedAmount !== '' ? parseFloat(adjustedAmount) : proposedPayout;
    onRecordDecision(activeTask.task_id, decisionType, adjusterNote, payoutToSubmit);
    setAdjusterNote('');
    setAdjustedAmount('');
  };

  return (
    <div className="dossier-pane">
      {/* Dossier Tabs */}
      <div className="dossier-tabs-nav">
        <button 
          className={`dossier-tab-btn ${activeTab === 'adjudication' ? 'active' : ''}`}
          onClick={() => setActiveTab('adjudication')}
        >
          <Calculator size={14} />
          <span>Adjudication & Settlement</span>
        </button>

        <button 
          className={`dossier-tab-btn ${activeTab === 'policy' ? 'active' : ''}`}
          onClick={() => setActiveTab('policy')}
        >
          <BookOpen size={14} />
          <span>Policy RAG Citations</span>
          {policy_validation.citations?.length > 0 && (
            <span style={{ fontSize: '0.68rem', color: '#818cf8', fontWeight: 700 }}>
              ({policy_validation.citations.length})
            </span>
          )}
        </button>

        <button 
          className={`dossier-tab-btn ${activeTab === 'forensics' ? 'active' : ''}`}
          onClick={() => setActiveTab('forensics')}
        >
          <ShieldAlert size={14} />
          <span>Forensic Lab</span>
          {fraud_report.flags?.length > 0 && (
            <span style={{ fontSize: '0.68rem', color: '#f87171', fontWeight: 700 }}>
              ({fraud_report.flags.length})
            </span>
          )}
        </button>

        <button 
          className={`dossier-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          <History size={14} />
          <span>Audit Stream ({audit_events.length})</span>
        </button>
      </div>

      <div className="dossier-content">
        {/* TAB 1: Adjudication & Settlement */}
        {activeTab === 'adjudication' && (
          <>
            {/* Route Decision Banner */}
            <div style={{
              background: 'var(--bg-surface-2)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 700 }}>
                  Automated Decision Brief
                </span>
                <span className="badge-tag badge-tag-stp" style={{ fontSize: '0.68rem' }}>
                  {current_status}
                </span>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#e2e8f0', fontWeight: 500 }}>
                {route_reason}
              </div>
            </div>

            {/* Financial Settlement Matrix */}
            <div className="math-matrix-box">
              <div className="math-matrix-header">
                <span>Deterministic Settlement Arithmetic</span>
                <span style={{ color: 'var(--text-tertiary)' }}>Currency: USD ($)</span>
              </div>

              <div className="formula-flow-grid">
                <div className="formula-item">
                  <span className="formula-lbl">OEM Estimate</span>
                  <span className="formula-val" style={{ color: '#38bdf8' }}>${approvedEst.toLocaleString()}</span>
                </div>

                <span className="formula-op">-</span>

                <div className="formula-item">
                  <span className="formula-lbl">Deductible</span>
                  <span className="formula-val" style={{ color: '#f59e0b' }}>${deductible.toLocaleString()}</span>
                </div>

                <span className="formula-op">-</span>

                <div className="formula-item">
                  <span className="formula-lbl">Depreciation</span>
                  <span className="formula-val" style={{ color: '#f59e0b' }}>${depreciation.toLocaleString()}</span>
                </div>

                <span className="formula-op">=</span>

                <div className="formula-item">
                  <span className="formula-lbl">Net Proposed Payout</span>
                  <span className="formula-val" style={{ color: '#34d399', fontSize: '1.25rem' }}>
                    ${proposedPayout.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-tertiary)', paddingTop: '0.25rem' }}>
                <span>Demo Authority Ceiling: <strong>$5,000.00</strong></span>
                {settlement_decision.txn_ref ? (
                  <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                    Ledger Ref: {settlement_decision.txn_ref}
                  </span>
                ) : (
                  <span style={{ color: '#f59e0b' }}>Requires Adjuster Sign-Off</span>
                )}
              </div>
            </div>

            {/* Adjuster Action Console (When in Review) */}
            {activeTask ? (
              <div className="adjudication-action-console">
                <div className="console-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, fontSize: '0.85rem' }}>
                    <AlertTriangle size={15} color="#f59e0b" />
                    <span>Human Adjuster Sign-Off Required ({activeTask.task_type})</span>
                  </div>
                  <span className="badge-tag badge-tag-review">{activeTask.priority} Priority</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: '0.75rem' }}>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '0.25rem' }}>
                      Adjuster Notes & Audit Rationale:
                    </label>
                    <input 
                      type="text"
                      className="inbox-search-input"
                      placeholder="e.g. Verified body shop OEM labor rate and confirmed coverage..."
                      value={adjusterNote}
                      onChange={(e) => setAdjusterNote(e.target.value)}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '0.25rem' }}>
                      Approved Payout ($):
                    </label>
                    <input 
                      type="number"
                      className="inbox-search-input"
                      placeholder={proposedPayout.toString()}
                      value={adjustedAmount}
                      onChange={(e) => setAdjustedAmount(e.target.value)}
                      style={{ color: '#34d399', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
                    />
                  </div>
                </div>

                <div className="console-actions-row">
                  <button 
                    onClick={() => handleDecision('APPROVED')}
                    className="btn-ui btn-ui-success"
                    disabled={isSubmitting}
                  >
                    <Check size={13} />
                    <span>Approve & Disburse (ACH)</span>
                  </button>

                  <button 
                    onClick={() => handleDecision('REJECTED')}
                    className="btn-ui btn-ui-danger"
                    disabled={isSubmitting}
                  >
                    <X size={13} />
                    <span>Confirm Coverage Denial</span>
                  </button>

                  <button 
                    onClick={() => handleDecision('REQUEST_INFO')}
                    className="btn-ui btn-ui-subtle"
                    disabled={isSubmitting}
                  >
                    <MessageSquare size={13} />
                    <span>Request Supplemental Info</span>
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                background: 'rgba(16, 185, 129, 0.04)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                borderRadius: 'var(--radius-md)',
                padding: '0.9rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                fontSize: '0.8rem',
                color: '#34d399'
              }}>
                <Check size={16} />
                <span>
                  {current_status === 'SETTLED_STP' 
                    ? `Adjudicated automatically via Straight-Through Processing (Txn ${settlement_decision.txn_ref}). No adjuster intervention required.`
                    : (current_status === 'SETTLED_MANUAL' 
                        ? 'Settled and confirmed by Adjuster. Disbursement posted to ledger.'
                        : 'No pending manual review task for this claim.')}
                </span>
              </div>
            )}

            {/* Claim Profile & Vehicle Data Table */}
            <div className="panel" style={{ padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '0.65rem' }}>
                Claimant & Insured Vehicle Profile
              </div>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td>Policyholder</td>
                    <td style={{ color: '#fff', fontWeight: 600 }}>{intake_data.claimant_name || 'N/A'}</td>
                    <td>Policy Number</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{intake_data.policy_no}</td>
                  </tr>
                  <tr>
                    <td>Insured Vehicle</td>
                    <td style={{ color: '#fff' }}>{intake_data.vehicle_make_model || 'N/A'}</td>
                    <td>Vehicle VIN</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{intake_data.vin || 'MISSING (Flagged)'}</td>
                  </tr>
                  <tr>
                    <td>Date of Incident</td>
                    <td>{intake_data.loss_date || 'N/A'}</td>
                    <td>Incident Peril</td>
                    <td>{intake_data.loss_type || 'Collision'}</td>
                  </tr>
                  <tr>
                    <td>Reported Narrative</td>
                    <td colSpan={3} style={{ color: '#cbd5e1', fontStyle: 'italic' }}>
                      "{intake_data.incident_description || 'No description provided.'}"
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* TAB 2: Policy RAG & Clause Citations */}
        {activeTab === 'policy' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Authoritative PAS Card */}
            <div className="panel" style={{ padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                  Authoritative Policy Administration System (PAS) Record
                </span>
                <span className={`badge-tag ${policy_validation.active ? 'badge-tag-stp' : 'badge-tag-denied'}`}>
                  {policy_validation.active ? 'STATUS: ACTIVE' : 'STATUS: LAPSED / INACTIVE'}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', fontSize: '0.78rem' }}>
                <div>
                  <span style={{ color: 'var(--text-tertiary)', display: 'block' }}>Standard Deductible:</span>
                  <strong style={{ color: '#fff' }}>${policy_validation.deductible || 0}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-tertiary)', display: 'block' }}>Incident Limit:</span>
                  <strong style={{ color: '#fff' }}>${(policy_validation.policy_limit || 0).toLocaleString()}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-tertiary)', display: 'block' }}>Coverage Eligibility:</span>
                  <strong style={{ color: policy_validation.eligible ? '#34d399' : '#f87171' }}>
                    {policy_validation.eligible ? 'ELIGIBLE' : 'EXCLUDED / EXCEPTION'}
                  </strong>
                </div>
              </div>
            </div>

            {/* Gemini Coverage Rationale */}
            {policy_validation.coverage_explanation && (
              <div style={{
                background: 'rgba(59, 130, 246, 0.05)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.85rem 1rem',
                fontSize: '0.82rem',
                color: '#c7d2fe'
              }}>
                <div style={{ fontWeight: 700, marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Info size={14} color="#3b82f6" />
                  <span>AI Coverage Determination Rationale (Gemini 2.5 Flash Grounded)</span>
                </div>
                {policy_validation.coverage_explanation}
              </div>
            )}

            {/* FTS5 Cited Clauses */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                Retrieved Policy Contract Evidence (SQLite FTS5)
              </span>

              {policy_validation.citations?.length === 0 ? (
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>
                  No matching policy clauses indexed for this query.
                </div>
              ) : (
                policy_validation.citations?.map((c, i) => (
                  <div key={i} className="citation-block">
                    <div className="citation-title-row">
                      <span>{c.section_title}</span>
                      <span style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>
                        Source: {c.source_file || 'Policy PDF'} • Page {c.page_number}
                      </span>
                    </div>
                    <div className="citation-body">
                      {c.chunk_text}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 3: Forensic Lab & Image Analysis */}
        {activeTab === 'forensics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Fraud Gauge Card */}
            <div className="panel" style={{ padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                    Forensics & Fraud Anomaly Screening
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    Automated perceptual hashing (pHash) & EXIF timestamp integrity analysis
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Fraud Risk Score</span>
                  <div style={{
                    fontSize: '1.4rem',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                    color: fraud_report.fraud_score >= 75 ? '#f87171' : (fraud_report.fraud_score > 25 ? '#fbbf24' : '#34d399')
                  }}>
                    {fraud_report.fraud_score || 0} / 100
                  </div>
                </div>
              </div>
            </div>

            {/* Perceptual Hash Duplicates */}
            <div className="panel" style={{ padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
                Perceptual Hash Duplicate Photo Detection (pHash Database)
              </div>
              {fraud_report.duplicate_matches?.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Submitted Photo</th>
                      <th>Perceptual Hash</th>
                      <th>Matched Prior Claim</th>
                      <th>Investigation Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fraud_report.duplicate_matches.map((m, i) => (
                      <tr key={i}>
                        <td style={{ color: '#fff' }}>{m.photo_id}</td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>{m.matched_hash}</td>
                        <td style={{ color: '#f87171', fontWeight: 700 }}>{m.prior_claim_id}</td>
                        <td>{m.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: '#34d399', fontSize: '0.8rem', padding: '0.5rem 0' }}>
                  ✓ No perceptual hash matches found across historical claims database.
                </div>
              )}
            </div>

            {/* EXIF Timestamp Analysis */}
            <div className="panel" style={{ padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
                EXIF Timestamp Chronological Timeline Analysis
              </div>
              {fraud_report.exif_discrepancies?.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Photo ID</th>
                      <th>EXIF Camera Date</th>
                      <th>Reported Loss Date</th>
                      <th>Discrepancy Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fraud_report.exif_discrepancies.map((d, i) => (
                      <tr key={i}>
                        <td style={{ color: '#fff' }}>{d.photo_id}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{d.exif_date}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{d.loss_date}</td>
                        <td style={{ color: '#f87171', fontWeight: 700 }}>Photo predates incident by {d.days_prior} days</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: '#34d399', fontSize: '0.8rem', padding: '0.5rem 0' }}>
                  ✓ All attached photo EXIF timestamps match reported loss timestamp within tolerance.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: Audit Stream & Event Timeline */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
              Immutable SQLite Audit Trail ({audit_events.length} Telemetry Events)
            </span>

            {audit_events.map((ev, i) => (
              <div key={i} className="panel" style={{ padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="badge-tag badge-tag-info">{ev.stage}</span>
                    <strong style={{ fontSize: '0.85rem', color: '#fff' }}>{ev.event_type}</strong>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                  {ev.route_reason}
                </div>
                {ev.evidence && (
                  <pre style={{
                    fontSize: '0.7rem',
                    fontFamily: 'var(--font-mono)',
                    background: 'var(--bg-surface-1)',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '4px',
                    color: '#93c5fd',
                    overflowX: 'auto'
                  }}>
                    {typeof ev.evidence === 'string' ? ev.evidence : JSON.stringify(ev.evidence, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
