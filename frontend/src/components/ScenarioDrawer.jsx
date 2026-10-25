import React from 'react';
import { Play, CheckCircle2, AlertOctagon, ShieldAlert, FileQuestion, ArrowUpRight } from 'lucide-react';

const SCENARIOS = [
  {
    key: "routine_stp",
    code: "SC-01",
    tag: "STP AUTO-PAY",
    title: "Routine Rear Impact ($2.2k)",
    badgeColor: "#34d399",
    icon: CheckCircle2
  },
  {
    key: "missing_info",
    code: "SC-02",
    tag: "GATE 1 PAUSE",
    title: "Missing VIN / Estimate",
    badgeColor: "#38bdf8",
    icon: FileQuestion
  },
  {
    key: "excluded_policy",
    code: "SC-03",
    tag: "GATE 2 EXCL",
    title: "Track Racing (Sec 8.3)",
    badgeColor: "#fbbf24",
    icon: AlertOctagon
  },
  {
    key: "fraud_freeze",
    code: "SC-04",
    tag: "GATE 3 SIU",
    title: "Duplicate Photo & EXIF",
    badgeColor: "#f87171",
    icon: ShieldAlert
  },
  {
    key: "high_estimate",
    code: "SC-05",
    tag: "GATE 4 AUTH",
    title: "Audi RS6 Front ($14k)",
    badgeColor: "#818cf8",
    icon: ArrowUpRight
  }
];

export default function ScenarioDrawer({ activeScenario, onRunScenario, loadingScenario }) {
  return (
    <div className="scenario-bar">
      <div className="scenario-bar-title">Demo Scenarios:</div>
      <div className="scenario-chips-wrapper">
        {SCENARIOS.map((sc) => {
          const Icon = sc.icon;
          const isSelected = activeScenario === sc.key;
          const isLoading = loadingScenario === sc.key;

          return (
            <div 
              key={sc.key}
              className={`scenario-chip ${isSelected ? 'selected' : ''}`}
              onClick={() => onRunScenario(sc.key)}
              title={`Execute ${sc.title}`}
            >
              <span className="scenario-code">{sc.code}</span>
              <Icon size={14} color={sc.badgeColor} />
              <span>{sc.title}</span>
              {isLoading ? (
                <div className="spinner" style={{ width: '11px', height: '11px', marginLeft: '0.25rem' }} />
              ) : (
                <span style={{ fontSize: '0.65rem', color: sc.badgeColor, fontWeight: 700 }}>
                  [{sc.tag}]
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
