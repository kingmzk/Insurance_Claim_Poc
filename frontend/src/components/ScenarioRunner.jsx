import React from 'react';
import { Play, CheckCircle2, AlertOctagon, ShieldAlert, FileQuestion, ArrowUpRight } from 'lucide-react';

const SCENARIOS = [
  {
    key: "routine_stp",
    number: "01",
    tag: "STP FAST-TRACK",
    tagClass: "badge-green",
    title: "Routine Motor Collision",
    claimId: "CLM-DEMO-001",
    desc: "Clean submission, active policy, low fraud (12), OEM benchmark $2,950. Triggers simulated ACH payout ($2,240).",
    icon: CheckCircle2
  },
  {
    key: "missing_info",
    number: "02",
    tag: "NEEDS INFO",
    tagClass: "badge-amber",
    title: "Incomplete Submission",
    claimId: "CLM-DEMO-002",
    desc: "Missing VIN & repair estimate. Gate 1 pauses downstream graph and triggers document request.",
    icon: FileQuestion
  },
  {
    key: "excluded_policy",
    number: "03",
    tag: "DRAFT DENIAL",
    tagClass: "badge-rose",
    title: "Excluded Track Racing",
    claimId: "CLM-DEMO-003",
    desc: "Racing damage excluded under Section 8.3. Bypasses fraud/risk to draft denial for human adjuster review.",
    icon: AlertOctagon
  },
  {
    key: "fraud_freeze",
    number: "04",
    tag: "SIU ESCALATION",
    tagClass: "badge-rose",
    title: "Duplicate Photo & EXIF Mismatch",
    claimId: "CLM-DEMO-004",
    desc: "Perceptual photo hash matches prior claim CLM-2024-1102. Fraud score 80 triggers SIU freeze.",
    icon: ShieldAlert
  },
  {
    key: "high_estimate",
    number: "05",
    tag: "ADJUSTER REVIEW",
    tagClass: "badge-blue",
    title: "High-Value Audi RS6 ($14k)",
    claimId: "CLM-DEMO-005",
    desc: "Claim exceeds $5,000 demo STP limit and High Risk Tier. Routed to Adjuster Approval Queue.",
    icon: ArrowUpRight
  }
];

export default function ScenarioRunner({ activeScenario, onRunScenario, loadingScenario }) {
  return (
    <section className="scenario-section">
      <div className="section-label">
        <span>Synthetic Demo Scenarios (1-Click Run)</span>
        <span style={{ fontSize: '0.75rem', color: '#818cf8' }}>Demonstrating 4 Routing Gates</span>
      </div>

      <div className="scenarios-grid">
        {SCENARIOS.map((sc) => {
          const Icon = sc.icon;
          const isCurrent = activeScenario === sc.key;
          const isLoading = loadingScenario === sc.key;

          return (
            <div 
              key={sc.key}
              className={`scenario-card ${isCurrent ? 'active' : ''}`}
              onClick={() => onRunScenario(sc.key)}
            >
              <div className="scenario-card-header">
                <span className="scenario-num">{sc.number}</span>
                <span className={`badge ${sc.tagClass}`} style={{ fontSize: '0.68rem', padding: '0.2rem 0.55rem' }}>
                  {sc.tag}
                </span>
              </div>

              <div className="scenario-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Icon size={15} color={isCurrent ? '#818cf8' : '#94a3b8'} />
                <span>{sc.title}</span>
              </div>

              <div className="scenario-desc">{sc.desc}</div>

              <button className="scenario-btn-trigger">
                {isLoading ? (
                  <>
                    <div className="spinner" style={{ width: '13px', height: '13px' }} />
                    <span>Orchestrating...</span>
                  </>
                ) : (
                  <>
                    <Play size={12} />
                    <span>Run Scenario</span>
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
