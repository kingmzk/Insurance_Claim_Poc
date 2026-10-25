import React from 'react';
import { History, Shield, CheckCircle, AlertTriangle, FileText, ArrowRight } from 'lucide-react';

export default function AuditTrail({ auditEvents, claimId }) {
  if (!auditEvents || auditEvents.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <History size={36} color="var(--text-dim)" style={{ margin: '0 auto 0.75rem auto' }} />
        <p style={{ color: 'var(--text-muted)' }}>
          No audit history records available for claim {claimId || 'selected'}.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <History size={18} color="#818cf8" />
          <span>Immutable Audit Log & Evidence Trail</span>
        </h3>
        <span className="badge badge-blue" style={{ fontFamily: 'var(--font-mono)' }}>
          {claimId} • {auditEvents.length} Events
        </span>
      </div>

      <div className="audit-timeline">
        {auditEvents.map((ev, index) => {
          let badgeColor = 'badge-blue';
          if (ev.event_type.includes('PASSED') || ev.event_type.includes('DISBURSED') || ev.event_type.includes('COMPLETED')) {
            badgeColor = 'badge-green';
          } else if (ev.event_type.includes('NEEDS_INFO') || ev.event_type.includes('REVIEW')) {
            badgeColor = 'badge-amber';
          } else if (ev.event_type.includes('EXCEPTION') || ev.event_type.includes('ESCALATION') || ev.event_type.includes('DENIAL')) {
            badgeColor = 'badge-rose';
          }

          let evidenceParsed = null;
          if (ev.evidence_json) {
            try {
              evidenceParsed = typeof ev.evidence_json === 'string' ? JSON.parse(ev.evidence_json) : ev.evidence_json;
            } catch (e) {
              evidenceParsed = ev.evidence_json;
            }
          }

          return (
            <div key={ev.event_id || index} className="timeline-item">
              <div className="timeline-dot" />

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                <span className={`badge ${badgeColor}`} style={{ fontSize: '0.72rem' }}>
                  {ev.stage}
                </span>
                <strong style={{ fontSize: '0.9rem', color: '#f8fafc' }}>{ev.event_type}</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>
                  {new Date(ev.created_at).toLocaleTimeString()}
                </span>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
                {ev.route_reason}
              </div>

              {evidenceParsed && Object.keys(evidenceParsed).length > 0 && (
                <div style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  color: '#94a3b8',
                  marginTop: '0.35rem'
                }}>
                  {JSON.stringify(evidenceParsed)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
