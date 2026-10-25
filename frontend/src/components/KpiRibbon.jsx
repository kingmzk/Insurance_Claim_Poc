import React from 'react';
import { Activity, Zap, DollarSign, ShieldAlert, Users } from 'lucide-react';

export default function KpiRibbon({ claims, reviewTasks }) {
  const totalClaims = claims.length;
  const stpClaims = claims.filter(c => c.status === 'SETTLED_STP').length;
  const stpRate = totalClaims > 0 ? Math.round((stpClaims / totalClaims) * 100) : 0;
  
  const totalDisbursed = claims.reduce((acc, c) => {
    if (c.status === 'SETTLED_STP' || c.status === 'SETTLED_MANUAL') {
      const payout = c.state?.settlement_decision?.net_payout ?? c.state?.settlement_decision?.proposed_payout ?? 0;
      return acc + payout;
    }
    return acc;
  }, 0);

  const siuCount = claims.filter(c => c.state?.fraud_report?.siu_escalate).length;
  const pendingReviews = reviewTasks.filter(t => t.status === 'PENDING').length;

  return (
    <div className="kpi-strip">
      <div className="kpi-cell">
        <span className="kpi-label">Claims Intake Volume</span>
        <div className="kpi-value-row">
          <span className="kpi-num">{totalClaims}</span>
          <span className="kpi-sub" style={{ color: 'var(--text-tertiary)' }}>Live FNOL</span>
        </div>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">STP Automation Rate</span>
        <div className="kpi-value-row">
          <span className="kpi-num" style={{ color: stpRate >= 40 ? '#34d399' : '#38bdf8' }}>
            {stpRate}%
          </span>
          <span className="kpi-sub" style={{ color: stpRate >= 40 ? '#34d399' : '#94a3b8' }}>
            Target: ≥ 40%
          </span>
        </div>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Simulated Capital Disbursed</span>
        <div className="kpi-value-row">
          <span className="kpi-num" style={{ color: '#38bdf8' }}>
            ${totalDisbursed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span className="kpi-sub" style={{ color: 'var(--text-tertiary)' }}>Idempotent ACH</span>
        </div>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">SIU Hard-Fraud Freezes</span>
        <div className="kpi-value-row">
          <span className="kpi-num" style={{ color: siuCount > 0 ? '#f87171' : 'var(--text-primary)' }}>
            {siuCount}
          </span>
          <span className="kpi-sub" style={{ color: siuCount > 0 ? '#f87171' : 'var(--text-tertiary)' }}>
            Score ≥ 75 Gate
          </span>
        </div>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Human Review Queue</span>
        <div className="kpi-value-row">
          <span className="kpi-num" style={{ color: pendingReviews > 0 ? '#fbbf24' : 'var(--text-primary)' }}>
            {pendingReviews}
          </span>
          <span className="kpi-sub" style={{ color: pendingReviews > 0 ? '#fbbf24' : 'var(--text-tertiary)' }}>
            Pending Adjuster
          </span>
        </div>
      </div>
    </div>
  );
}
