import React, { useState } from 'react';
import { Check, X, AlertCircle, Clock, ShieldAlert, MessageSquare } from 'lucide-react';

export default function ReviewQueue({ tasks, onRecordDecision, isSubmitting }) {
  const [decisionNotes, setDecisionNotes] = useState({});
  const [payoutOverrides, setPayoutOverrides] = useState({});

  if (!tasks || tasks.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3.5rem', textAlign: 'center' }}>
        <Check size={40} color="#10b981" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>Review Queue Clear</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          No pending adjuster or SIU approval tasks. Run Scenario 3 (Draft Denial), Scenario 4 (SIU Freeze), or Scenario 5 (High Value) to generate review items.
        </p>
      </div>
    );
  }

  const handleNoteChange = (taskId, text) => {
    setDecisionNotes(prev => ({ ...prev, [taskId]: text }));
  };

  const handlePayoutChange = (taskId, val) => {
    setPayoutOverrides(prev => ({ ...prev, [taskId]: parseFloat(val) || 0 }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
          Human Review Queue ({tasks.length} Pending Actions)
        </h3>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          Audit Trail logs every human sign-off with timestamp and reason
        </span>
      </div>

      {tasks.map((t) => {
        const isSIU = t.task_type === 'SIU_FRAUD';
        const isCoverage = t.task_type === 'COVERAGE_EXCEPTION';
        const isAdjuster = t.task_type === 'ADJUSTER_APPROVAL';
        const isNeedsInfo = t.task_type === 'NEEDS_INFO';

        const defaultPayout = t.details?.proposed_payout ?? 0;
        const currentNote = decisionNotes[t.task_id] || '';
        const currentPayout = payoutOverrides[t.task_id] ?? defaultPayout;

        return (
          <div key={t.task_id} className="review-task-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.1rem' }}>
                    {t.claim_id}
                  </span>
                  <span className={`badge ${isSIU ? 'badge-rose' : (isCoverage ? 'badge-rose' : 'badge-amber')}`}>
                    {t.task_type}
                  </span>
                  <span className="badge badge-blue">{t.priority} PRIORITY</span>
                </div>

                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Claimant: <strong style={{ color: '#fff' }}>{t.claim_state?.intake_data?.claimant_name}</strong> • 
                  Loss: {t.claim_state?.intake_data?.loss_type} • 
                  Claimed: ${(t.claim_state?.intake_data?.claimed_amt || 0).toLocaleString()}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Queued At</span>
                <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                  {new Date(t.created_at).toLocaleTimeString()}
                </div>
              </div>
            </div>

            {/* Task Context Details */}
            <div style={{
              background: 'rgba(0,0,0,0.25)',
              padding: '0.8rem 1rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.85rem'
            }}>
              {isSIU && (
                <div>
                  <strong style={{ color: '#fb7185' }}>SIU Referral Reason:</strong> Fraud Score ({t.details?.score}) exceeds threshold.
                  <ul style={{ margin: '0.3rem 0 0 1.2rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {t.details?.flags?.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}

              {isCoverage && (
                <div>
                  <strong style={{ color: '#fbbf24' }}>Coverage Exception Draft:</strong> {t.details?.reason}
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                    Cites: {t.details?.citations?.map(c => c.section_title).join(', ') || 'Policy Contract Terms'}
                  </div>
                </div>
              )}

              {isAdjuster && (
                <div>
                  <strong style={{ color: '#38bdf8' }}>Adjuster Approval:</strong> Proposed payout exceeds $5,000 authority or High Risk tier.
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    Reasons: {t.details?.reasons?.join('; ')}
                  </div>
                </div>
              )}

              {isNeedsInfo && (
                <div>
                  <strong style={{ color: '#fbbf24' }}>Missing Mandatory Information:</strong>
                  <span style={{ color: 'var(--text-muted)' }}> Missing {t.details?.missing?.join(', ')}.</span>
                </div>
              )}
            </div>

            {/* Action Inputs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 200px', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.25rem', display: 'block' }}>
                  Adjuster / Investigator Decision Notes:
                </label>
                <input 
                  type="text"
                  placeholder="e.g. Verified OEM repair quotes with certified shop..."
                  value={currentNote}
                  onChange={(e) => handleNoteChange(t.task_id, e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-color)',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    color: '#fff',
                    fontSize: '0.82rem'
                  }}
                />
              </div>

              {!isCoverage && !isNeedsInfo && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.25rem', display: 'block' }}>
                    Approved Payout ($):
                  </label>
                  <input 
                    type="number"
                    value={currentPayout}
                    onChange={(e) => handlePayoutChange(t.task_id, e.target.value)}
                    style={{
                      width: '100%',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-color)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      color: '#34d399',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              )}
            </div>

            {/* Decision Buttons */}
            <div className="review-task-actions">
              <button 
                onClick={() => onRecordDecision(t.task_id, 'APPROVED', currentNote, currentPayout)}
                className="btn-success"
                disabled={isSubmitting}
              >
                <Check size={14} />
                <span>Approve & Disburse</span>
              </button>

              <button 
                onClick={() => onRecordDecision(t.task_id, 'REJECTED', currentNote || 'Claim denied after human adjuster review.')}
                className="btn-danger"
                disabled={isSubmitting}
              >
                <X size={14} />
                <span>Confirm Denial</span>
              </button>

              <button 
                onClick={() => onRecordDecision(t.task_id, 'REQUEST_INFO', currentNote || 'Requesting additional invoices and photo clarification.')}
                className="btn-secondary"
                disabled={isSubmitting}
              >
                <MessageSquare size={14} />
                <span>Request Claimant Info</span>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
