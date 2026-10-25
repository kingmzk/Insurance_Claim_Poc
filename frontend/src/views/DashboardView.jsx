import React from 'react';
import { 
  Play, 
  CheckCircle2, 
  AlertOctagon, 
  ShieldAlert, 
  FileQuestion, 
  ArrowUpRight,
  Cpu,
  ChevronRight,
  TrendingUp,
  Layers
} from 'lucide-react';
import KpiRibbon from '../components/KpiRibbon';

const SCENARIOS = [
  {
    key: "routine_stp",
    code: "SC-01",
    tag: "STP AUTO-PAY",
    badgeClass: "badge-tag-stp",
    title: "Routine Motor Collision",
    claimId: "CLM-DEMO-001",
    desc: "Clean submission, active policy, low fraud (12), OEM benchmark $2,950. Triggers simulated ACH payout ($2,240.00).",
    icon: CheckCircle2,
    badgeColor: "#34d399"
  },
  {
    key: "missing_info",
    code: "SC-02",
    tag: "GATE 1 PAUSE",
    badgeClass: "badge-tag-info",
    title: "Incomplete Submission (Needs Info)",
    claimId: "CLM-DEMO-002",
    desc: "Missing vehicle VIN & repair estimate. Gate 1 pauses downstream graph and triggers claimant document request.",
    icon: FileQuestion,
    badgeColor: "#38bdf8"
  },
  {
    key: "excluded_policy",
    code: "SC-03",
    tag: "GATE 2 EXCL",
    badgeClass: "badge-tag-review",
    title: "Excluded Activity (Track Racing)",
    claimId: "CLM-DEMO-003",
    desc: "Racing damage excluded under Section 8.3. Bypasses fraud/risk to draft denial for human adjuster review.",
    icon: AlertOctagon,
    badgeColor: "#fbbf24"
  },
  {
    key: "fraud_freeze",
    code: "SC-04",
    tag: "GATE 3 SIU",
    badgeClass: "badge-tag-siu",
    title: "Duplicate Photo & EXIF Mismatch",
    claimId: "CLM-DEMO-004",
    desc: "Photo perceptual hash matches prior claim CLM-2024-1102. Fraud score 85 triggers immediate SIU freeze.",
    icon: ShieldAlert,
    badgeColor: "#f87171"
  },
  {
    key: "high_estimate",
    code: "SC-05",
    tag: "GATE 4 AUTH",
    badgeClass: "badge-tag-review",
    title: "High-Value Audi RS6 ($14k)",
    claimId: "CLM-DEMO-005",
    desc: "Claim exceeds $5,000 demo STP limit and High Risk Tier. Routed to Adjuster Approval Queue.",
    icon: ArrowUpRight,
    badgeColor: "#818cf8"
  }
];

export default function DashboardView({ 
  claims, 
  reviewTasks, 
  onRunScenario, 
  loadingScenario, 
  onOpenClaimInWorkbench 
}) {
  return (
    <div className="view-container">
      {/* 1. Operational KPI Ribbon */}
      <KpiRibbon claims={claims} reviewTasks={reviewTasks} />

      {/* 2. Simulation & Scenario Testing Center */}
      <div className="view-section">
        <div className="section-title-row">
          <div>
            <h2 className="section-heading">Demo Scenarios & Simulation Testbench</h2>
            <p className="section-subheading">
              Execute test claims representing the 4 conditional routing gates in the PoC blueprint.
            </p>
          </div>
          <span className="badge-tag badge-tag-info" style={{ fontFamily: 'var(--font-mono)' }}>
            4 Routing Gates • Deterministic Math
          </span>
        </div>

        <div className="scenarios-grid">
          {SCENARIOS.map((sc) => {
            const Icon = sc.icon;
            const isLoading = loadingScenario === sc.key;

            return (
              <div key={sc.key} className="scenario-card-lg">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-tertiary)', fontWeight: 700 }}>
                    {sc.code} • {sc.claimId}
                  </span>
                  <span className={`badge-tag ${sc.badgeClass}`}>
                    {sc.tag}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', color: '#fff', marginBottom: '0.35rem' }}>
                  <Icon size={16} color={sc.badgeColor} />
                  <span>{sc.title}</span>
                </div>

                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, flex: 1, marginBottom: '0.85rem' }}>
                  {sc.desc}
                </p>

                <button 
                  onClick={() => onRunScenario(sc.key)}
                  className="btn-ui btn-ui-primary"
                  disabled={isLoading}
                  style={{ width: '100%' }}
                >
                  {isLoading ? (
                    <>
                      <div className="spinner" style={{ width: '12px', height: '12px' }} />
                      <span>Orchestrating...</span>
                    </>
                  ) : (
                    <>
                      <Play size={13} />
                      <span>Execute Scenario</span>
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Recent Claims Activity Table */}
      <div className="view-section">
        <div className="section-title-row">
          <div>
            <h2 className="section-heading">Recent Adjudication Activity</h2>
            <p className="section-subheading">
              Live claims processed through the 5-agent LangGraph state machine. Click any claim to inspect in workbench.
            </p>
          </div>
        </div>

        <div className="panel" style={{ overflow: 'hidden' }}>
          {claims.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              No claims processed yet. Click any scenario above to execute.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Status</th>
                  <th>Claimant Name</th>
                  <th>Insured Vehicle</th>
                  <th>Loss Peril</th>
                  <th>Claimed Amount</th>
                  <th>Net Payout</th>
                  <th>Fraud Score</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {claims.slice(0, 8).map((c) => {
                  const st = c.state || {};
                  const intake = st.intake_data || {};
                  const fraud = st.fraud_report || {};
                  const settle = st.settlement_decision || {};

                  let tagClass = 'badge-tag-review';
                  if (c.status === 'SETTLED_STP' || c.status === 'SETTLED_MANUAL') tagClass = 'badge-tag-stp';
                  else if (c.status === 'NEEDS_INFO') tagClass = 'badge-tag-info';
                  else if (fraud.siu_escalate) tagClass = 'badge-tag-siu';
                  else if (c.status.includes('DENIED')) tagClass = 'badge-tag-denied';

                  const payout = settle.net_payout ?? settle.proposed_payout ?? 0;
                  const fraudScore = fraud.fraud_score ?? 0;
                  const fraudColor = fraudScore >= 75 ? '#f87171' : (fraudScore > 25 ? '#fbbf24' : '#34d399');

                  return (
                    <tr key={c.claim_id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fff' }}>
                        {c.claim_id}
                      </td>
                      <td>
                        <span className={`badge-tag ${tagClass}`}>
                          {c.status}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600, color: '#fff' }}>
                        {intake.claimant_name || 'Claimant'}
                      </td>
                      <td>{intake.vehicle_make_model || 'Motor Vehicle'}</td>
                      <td>{intake.loss_type}</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        ${(intake.claimed_amt || 0).toLocaleString()}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38bdf8' }}>
                        ${payout.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: fraudColor }}>
                        {fraudScore} / 100
                      </td>
                      <td>
                        <button 
                          onClick={() => onOpenClaimInWorkbench(st)}
                          className="btn-ui btn-ui-subtle"
                          style={{ padding: '0.25rem 0.55rem', fontSize: '0.72rem' }}
                        >
                          <span>Open Brief</span>
                          <ChevronRight size={12} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
