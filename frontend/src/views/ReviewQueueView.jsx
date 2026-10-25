import React, { useState } from 'react';
import { 
  UserCheck, 
  Check, 
  X, 
  MessageSquare, 
  AlertTriangle, 
  Clock, 
  ShieldAlert, 
  ArrowRight,
  ExternalLink
} from 'lucide-react';

export default function ReviewQueueView({ 
  tasks, 
  onRecordDecision, 
  isSubmitting, 
  onOpenClaimInWorkbench 
}) {
  const [taskFilter, setTaskFilter] = useState('ALL');
  const [decisionNotes, setDecisionNotes] = useState({});
  const [payoutOverrides, setPayoutOverrides] = useState({});

  const filteredTasks = tasks.filter((t) => {
    if (taskFilter === 'ALL') return true;
    if (taskFilter === 'SIU') return t.task_type === 'SIU_FRAUD';
    if (taskFilter === 'COVERAGE') return t.task_type === 'COVERAGE_EXCEPTION';
    if (taskFilter === 'ADJUSTER') return t.task_type === 'ADJUSTER_APPROVAL';
    if (taskFilter === 'INFO') return t.task_type === 'NEEDS_INFO';
    return true;
  });

  const handleNoteChange = (taskId, text) => {
    setDecisionNotes(prev => ({ ...prev, [taskId]: text }));
  };

  const handlePayoutChange = (taskId, val) => {
    setPayoutOverrides(prev => ({ ...prev, [taskId]: parseFloat(val) || 0 }));
  };

  return (
    <div className="view-container">
      <div className="view-section">
        <div className="section-title-row">
          <div>
            <h2 className="section-heading">Human Review & Adjudication Queue</h2>
            <p className="section-subheading">
              Dedicated queue for claims paused at Gate 1 (Incomplete), Gate 2 (Coverage Exception), Gate 3 (SIU Freeze), or Gate 4 (Over-Authority).
            </p>
          </div>

          <div className="filter-pills">
            {['ALL', 'SIU', 'COVERAGE', 'ADJUSTER', 'INFO'].map((f) => (
              <button
                key={f}
                className={`filter-pill-btn ${taskFilter === f ? 'active' : ''}`}
                onClick={() => setTaskFilter(f)}
              >
                {f === 'ALL' ? `ALL (${tasks.length})` : f}
              </button>
            ))}
          </div>
        </div>

        {filteredTasks.length === 0 ? (
          <div className="panel" style={{ padding: '3.5rem', textAlign: 'center' }}>
            <UserCheck size={36} color="var(--emerald)" style={{ margin: '0 auto 0.75rem auto' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '0.25rem' }}>Review Queue Clear</h3>
            <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
              No claims currently awaiting human review. Run Scenario 3 (Track Racing), Scenario 4 (Duplicate Photo), or Scenario 5 (Audi RS6) from Dashboard to generate review tasks.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {filteredTasks.map((t) => {
              const isSIU = t.task_type === 'SIU_FRAUD';
              const isCoverage = t.task_type === 'COVERAGE_EXCEPTION';
              const isAdjuster = t.task_type === 'ADJUSTER_APPROVAL';
              const isNeedsInfo = t.task_type === 'NEEDS_INFO';

              const defaultPayout = t.details?.proposed_payout ?? 0;
              const currentNote = decisionNotes[t.task_id] || '';
              const currentPayout = payoutOverrides[t.task_id] ?? defaultPayout;
              const claimState = t.claim_state || {};
              const intake = claimState.intake_data || {};

              let tagClass = 'badge-tag-review';
              if (isSIU) tagClass = 'badge-tag-siu';
              else if (isCoverage) tagClass = 'badge-tag-denied';
              else if (isNeedsInfo) tagClass = 'badge-tag-info';

              return (
                <div key={t.task_id} className="panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                          {t.claim_id}
                        </span>
                        <span className={`badge-tag ${tagClass}`}>
                          {t.task_type}
                        </span>
                        <span className="badge-tag badge-tag-info">
                          {t.priority} PRIORITY
                        </span>
                      </div>

                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                        Policyholder: <strong style={{ color: '#fff' }}>{intake.claimant_name || 'N/A'}</strong> • 
                        Vehicle: {intake.vehicle_make_model || 'Motor Vehicle'} • 
                        Claimed: ${(intake.claimed_amt || 0).toLocaleString()} • 
                        Policy: {intake.policy_no}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <button 
                        onClick={() => onOpenClaimInWorkbench(claimState)}
                        className="btn-ui btn-ui-subtle"
                        style={{ fontSize: '0.75rem' }}
                      >
                        <span>Open in Workbench</span>
                        <ExternalLink size={12} />
                      </button>
                    </div>
                  </div>

                  {/* Task Context Details */}
                  <div style={{
                    background: 'var(--bg-surface-1)',
                    border: '1px solid var(--border-subtle)',
                    padding: '0.75rem 1rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.82rem'
                  }}>
                    {isSIU && (
                      <div>
                        <strong style={{ color: '#f87171' }}>SIU Referral Reason:</strong> Composite Fraud Score ({t.details?.score}) ≥ 75.
                        <ul style={{ margin: '0.25rem 0 0 1.25rem', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                          {t.details?.flags?.map((f, i) => <li key={i}>{f}</li>)}
                        </ul>
                      </div>
                    )}

                    {isCoverage && (
                      <div>
                        <strong style={{ color: '#fbbf24' }}>Coverage Exception Draft:</strong> {t.details?.reason}
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.2rem' }}>
                          Cited Section: {t.details?.citations?.map(c => c.section_title).join(', ') || 'Section 8.3 General Exclusions'}
                        </div>
                      </div>
                    )}

                    {isAdjuster && (
                      <div>
                        <strong style={{ color: '#38bdf8' }}>Adjuster Approval Trigger:</strong> Proposed payout exceeds $5,000 authority limit or High Risk Tier.
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                          Reasons: {t.details?.reasons?.join('; ')}
                        </div>
                      </div>
                    )}

                    {isNeedsInfo && (
                      <div>
                        <strong style={{ color: '#38bdf8' }}>Missing Mandatory Information:</strong>
                        <span style={{ color: 'var(--text-secondary)' }}> Missing {t.details?.missing?.join(', ')}.</span>
                      </div>
                    )}
                  </div>

                  {/* Action Inputs */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: '0.75rem' }}>
                    <div>
                      <label style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '0.25rem' }}>
                        Adjuster Decision Rationale (Logged to SQLite Audit Trail):
                      </label>
                      <input 
                        type="text"
                        className="inbox-search-input"
                        placeholder="e.g. Verified certified repair quote and confirmed deductible..."
                        value={currentNote}
                        onChange={(e) => handleNoteChange(t.task_id, e.target.value)}
                      />
                    </div>

                    {!isCoverage && !isNeedsInfo && (
                      <div>
                        <label style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '0.25rem' }}>
                          Approved Payout ($):
                        </label>
                        <input 
                          type="number"
                          className="inbox-search-input"
                          value={currentPayout}
                          onChange={(e) => handlePayoutChange(t.task_id, e.target.value)}
                          style={{ color: '#34d399', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
                        />
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div style={{ display: 'flex', gap: '0.65rem' }}>
                    <button 
                      onClick={() => onRecordDecision(t.task_id, 'APPROVED', currentNote, currentPayout)}
                      className="btn-ui btn-ui-success"
                      disabled={isSubmitting}
                    >
                      <Check size={13} />
                      <span>Approve & Disburse (ACH)</span>
                    </button>

                    <button 
                      onClick={() => onRecordDecision(t.task_id, 'REJECTED', currentNote || 'Claim denied after adjuster review.')}
                      className="btn-ui btn-ui-danger"
                      disabled={isSubmitting}
                    >
                      <X size={13} />
                      <span>Confirm Coverage Denial</span>
                    </button>

                    <button 
                      onClick={() => onRecordDecision(t.task_id, 'REQUEST_INFO', currentNote || 'Requesting additional photo and estimate documentation.')}
                      className="btn-ui btn-ui-subtle"
                      disabled={isSubmitting}
                    >
                      <MessageSquare size={13} />
                      <span>Request Supplemental Info</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
