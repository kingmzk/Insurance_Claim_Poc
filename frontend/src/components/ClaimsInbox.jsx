import React, { useState } from 'react';
import { Search, ShieldAlert, CheckCircle, Clock, AlertTriangle, FileText } from 'lucide-react';

export default function ClaimsInbox({ claims, selectedClaimId, onSelectClaim }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filteredClaims = claims.filter((c) => {
    const q = searchQuery.toLowerCase();
    const st = c.state || {};
    const intake = st.intake_data || {};
    
    const matchesSearch = 
      c.claim_id.toLowerCase().includes(q) ||
      (intake.claimant_name || '').toLowerCase().includes(q) ||
      (intake.policy_no || '').toLowerCase().includes(q) ||
      (intake.vehicle_make_model || '').toLowerCase().includes(q) ||
      (intake.loss_type || '').toLowerCase().includes(q);

    if (!matchesSearch) return false;

    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'STP') return c.status === 'SETTLED_STP' || c.status === 'SETTLED_MANUAL';
    if (statusFilter === 'PENDING') return c.status === 'PENDING_REVIEW';
    if (statusFilter === 'INFO') return c.status === 'NEEDS_INFO';
    if (statusFilter === 'SIU') return st.fraud_report?.siu_escalate;
    return true;
  });

  return (
    <div className="inbox-pane">
      <div className="inbox-header">
        <input 
          type="text"
          className="inbox-search-input"
          placeholder="Filter by Claim ID, Claimant, VIN..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <div className="filter-pills">
          {['ALL', 'STP', 'PENDING', 'INFO', 'SIU'].map((f) => (
            <button
              key={f}
              className={`filter-pill-btn ${statusFilter === f ? 'active' : ''}`}
              onClick={() => setStatusFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="inbox-list">
        {filteredClaims.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
            No claims matching filter criteria.
          </div>
        ) : (
          filteredClaims.map((c) => {
            const isSelected = selectedClaimId === c.claim_id;
            const st = c.state || {};
            const intake = st.intake_data || {};
            const fraud = st.fraud_report || {};
            const settle = st.settlement_decision || {};

            let statusTagClass = 'badge-tag-review';
            let statusLabel = c.status;
            if (c.status === 'SETTLED_STP') {
              statusTagClass = 'badge-tag-stp';
              statusLabel = 'STP Auto';
            } else if (c.status === 'SETTLED_MANUAL') {
              statusTagClass = 'badge-tag-stp';
              statusLabel = 'Approved';
            } else if (c.status === 'NEEDS_INFO') {
              statusTagClass = 'badge-tag-info';
              statusLabel = 'Needs Info';
            } else if (fraud.siu_escalate) {
              statusTagClass = 'badge-tag-siu';
              statusLabel = 'SIU Alert';
            } else if (c.status.includes('DENIED')) {
              statusTagClass = 'badge-tag-denied';
              statusLabel = 'Denied';
            }

            const fraudScore = fraud.fraud_score ?? 0;
            const fraudColor = fraudScore >= 75 ? '#f87171' : (fraudScore > 25 ? '#fbbf24' : '#34d399');

            return (
              <div 
                key={c.claim_id}
                className={`inbox-item ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectClaim(st)}
              >
                <div className="inbox-row-1">
                  <span className="inbox-claim-id">{c.claim_id}</span>
                  <span className={`badge-tag ${statusTagClass}`}>
                    {statusLabel}
                  </span>
                </div>

                <div className="inbox-row-2">
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {intake.claimant_name || 'Claimant'}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    ${(intake.claimed_amt || 0).toLocaleString()}
                  </span>
                </div>

                <div className="inbox-row-3">
                  <span>{intake.vehicle_make_model || intake.loss_type || 'Motor Claim'}</span>
                  <span style={{ color: fraudColor, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    Score: {fraudScore}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
