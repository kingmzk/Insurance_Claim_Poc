import React, { useState } from 'react';
import { 
  FileCheck, 
  ShieldCheck, 
  Search, 
  Calculator, 
  CreditCard,
  ChevronDown,
  ChevronRight,
  Check, 
  X, 
  AlertTriangle, 
  Clock, 
  BookOpen, 
  ShieldAlert, 
  History, 
  MessageSquare,
  Code,
  DollarSign,
  Activity,
  ExternalLink
} from 'lucide-react';
import ClaimsInbox from '../components/ClaimsInbox';


export default function ClaimsWorkbenchView({ 
  claims, 
  selectedClaim, 
  onSelectClaim, 
  reviewTasks, 
  onRecordDecision, 
  isSubmitting 
}) {
  const [selectedAgentStep, setSelectedAgentStep] = useState(null);
  const [dossierTab, setDossierTab] = useState('adjudication');
  const [adjusterNote, setAdjusterNote] = useState('');
  const [adjustedAmount, setAdjustedAmount] = useState('');
  const [showRawJson, setShowRawJson] = useState(false);

  if (!selectedClaim) {
    return (
      <div className="workbench-layout-spacious">
        <ClaimsInbox 
          claims={claims} 
          selectedClaimId={null} 
          onSelectClaim={onSelectClaim} 
        />
        <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-tertiary)' }}>
          Select a claim from the left inbox or run a scenario from the Dashboard.
        </div>
      </div>
    );
  }

  const {
    claim_id,
    intake_data = {},
    completeness = 0,
    missing_fields = [],
    policy_validation = {},
    fraud_report = {},
    risk_assessment = {},
    settlement_decision = {},
    current_status = 'UNKNOWN',
    route_reason = '',
    audit_events = []
  } = selectedClaim;

  const approvedEst = risk_assessment.approved_estimate || 0;
  const deductible = policy_validation.deductible || 0;
  const depreciation = risk_assessment.depreciation || 0;
  const proposedPayout = settlement_decision.net_payout ?? settlement_decision.proposed_payout ?? 0;

  // Check if active review task exists
  const activeTask = reviewTasks.find(t => t.claim_id === claim_id && t.status === 'PENDING');

  const handleDecision = (decisionType) => {
    if (!activeTask) return;
    const payoutToSubmit = adjustedAmount !== '' ? parseFloat(adjustedAmount) : proposedPayout;
    onRecordDecision(activeTask.task_id, decisionType, adjusterNote, payoutToSubmit);
    setAdjusterNote('');
    setAdjustedAmount('');
  };

  // Node statuses for horizontal stepper
  const isIntakePassed = completeness === 1.0;
  const isPolicyPassed = policy_validation.active && policy_validation.eligible;
  const isFraudHalted = fraud_report.siu_escalate;
  const isStpSettled = settlement_decision.status === 'SIMULATED_STP';

  return (
    <div className="workbench-layout-spacious">
      {/* 1. Left Master Column: Claims Inbox */}
      <ClaimsInbox 
        claims={claims}
        selectedClaimId={claim_id}
        onSelectClaim={onSelectClaim}
      />

      {/* 2. Right Detail Column: Adjudication Workstation */}
      <div className="workbench-main-canvas">
        {/* Claim Summary Header */}
        <div className="workbench-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <span style={{ fontSize: '1.35rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fff' }}>
              {claim_id}
            </span>
            <span className="badge-tag badge-tag-stp" style={{ fontSize: '0.72rem' }}>
              {current_status}
            </span>
            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>•</span>
            <span style={{ color: '#fff', fontWeight: 600, fontSize: '0.9rem' }}>
              {intake_data.claimant_name || 'Claimant'}
            </span>
            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
              ({intake_data.vehicle_make_model || 'Vehicle'})
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 700 }}>
                Claimed Amount
              </span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1rem', color: '#fff' }}>
                ${(intake_data.claimed_amt || 0).toLocaleString()}
              </div>
            </div>

            <div style={{ textAlign: 'right', paddingLeft: '1rem', borderLeft: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 700 }}>
                Approved Payout
              </span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.15rem', color: '#34d399' }}>
                ${proposedPayout.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>

            {selectedClaim.trace_url ? (
              <a 
                href={selectedClaim.trace_url}
                target="_blank" 
                rel="noopener noreferrer"
                className="btn-ui"
                style={{ 
                  background: 'rgba(236, 72, 153, 0.15)', 
                  border: '1px solid rgba(236, 72, 153, 0.45)', 
                  color: '#f472b6',
                  padding: '0.35rem 0.75rem', 
                  fontSize: '0.75rem',
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontWeight: 600,
                  borderRadius: '4px'
                }}
                title={`Open Langfuse Trace ${selectedClaim.trace_id || ''} in Cloud Dashboard`}
              >
                <Activity size={13} color="#ec4899" />
                <span>Langfuse Trace</span>
                <ExternalLink size={11} color="#f472b6" />
              </a>
            ) : null}

            <button 
              onClick={() => setShowRawJson(!showRawJson)}
              className="btn-ui btn-ui-subtle"
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
            >
              <Code size={13} />
              <span>{showRawJson ? 'Hide State' : 'Raw JSON'}</span>
            </button>

          </div>
        </div>

        {/* Horizontal Multi-Agent Pipeline Stepper */}
        <div className="horizontal-pipeline-bar">
          <div className="stepper-title-row">
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 700 }}>
              Autonomous 5-Agent Execution Pipeline (LangGraph Control Plane)
            </span>
            <span style={{ fontSize: '0.72rem', color: '#818cf8', fontWeight: 600 }}>
              Click any node to inspect telemetry
            </span>
          </div>

          <div className="horizontal-stepper-grid">
            {/* Step 1: Intake */}
            <div 
              className={`stepper-node ${isIntakePassed ? 'node-pass' : 'node-halt'} ${selectedAgentStep === 'intake' ? 'node-selected' : ''}`}
              onClick={() => setSelectedAgentStep(selectedAgentStep === 'intake' ? null : 'intake')}
            >
              <div className="stepper-node-top">
                <span className="stepper-num">1</span>
                <span className="stepper-label">Intake Agent</span>
              </div>
              <div className="stepper-status-text">
                {isIntakePassed ? '100% Complete' : 'Halt (Needs Info)'}
              </div>
            </div>

            <div className="stepper-arrow">➔</div>

            {/* Step 2: Policy */}
            <div 
              className={`stepper-node ${isPolicyPassed ? 'node-pass' : (policy_validation.policy_no ? 'node-warn' : 'node-idle')} ${selectedAgentStep === 'policy' ? 'node-selected' : ''}`}
              onClick={() => setSelectedAgentStep(selectedAgentStep === 'policy' ? null : 'policy')}
            >
              <div className="stepper-node-top">
                <span className="stepper-num">2</span>
                <span className="stepper-label">Policy Agent</span>
              </div>
              <div className="stepper-status-text">
                {isPolicyPassed ? 'Coverage Confirmed' : (policy_validation.policy_no ? 'Exclusion Draft' : 'Waiting')}
              </div>
            </div>

            <div className="stepper-arrow">➔</div>

            {/* Step 3: Fraud */}
            <div 
              className={`stepper-node ${isFraudHalted ? 'node-danger' : (fraud_report.fraud_score !== undefined ? 'node-pass' : 'node-idle')} ${selectedAgentStep === 'fraud' ? 'node-selected' : ''}`}
              onClick={() => setSelectedAgentStep(selectedAgentStep === 'fraud' ? null : 'fraud')}
            >
              <div className="stepper-node-top">
                <span className="stepper-num">3</span>
                <span className="stepper-label">Fraud Agent</span>
              </div>
              <div className="stepper-status-text">
                {isFraudHalted ? 'SIU Freeze (≥75)' : (fraud_report.fraud_score !== undefined ? `Score: ${fraud_report.fraud_score}` : 'Waiting')}
              </div>
            </div>

            <div className="stepper-arrow">➔</div>

            {/* Step 4: Risk */}
            <div 
              className={`stepper-node ${risk_assessment.risk_tier ? 'node-pass' : 'node-idle'} ${selectedAgentStep === 'risk' ? 'node-selected' : ''}`}
              onClick={() => setSelectedAgentStep(selectedAgentStep === 'risk' ? null : 'risk')}
            >
              <div className="stepper-node-top">
                <span className="stepper-num">4</span>
                <span className="stepper-label">Risk Agent</span>
              </div>
              <div className="stepper-status-text">
                {risk_assessment.risk_tier ? `${risk_assessment.risk_tier} Risk Tier` : 'Waiting'}
              </div>
            </div>

            <div className="stepper-arrow">➔</div>

            {/* Step 5: Settlement */}
            <div 
              className={`stepper-node ${isStpSettled ? 'node-pass' : (settlement_decision.status ? 'node-warn' : 'node-idle')} ${selectedAgentStep === 'settle' ? 'node-selected' : ''}`}
              onClick={() => setSelectedAgentStep(selectedAgentStep === 'settle' ? null : 'settle')}
            >
              <div className="stepper-node-top">
                <span className="stepper-num">5</span>
                <span className="stepper-label">Settlement</span>
              </div>
              <div className="stepper-status-text">
                {isStpSettled ? 'STP Auto-Disbursed' : (settlement_decision.status ? 'Adjuster Queue' : 'Waiting')}
              </div>
            </div>
          </div>

          {/* Expanded Step Telemetry Panel */}
          {selectedAgentStep && (
            <div className="stepper-telemetry-drawer">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#fff' }}>
                  Node Telemetry: {selectedAgentStep.toUpperCase()}
                </span>
                <button 
                  onClick={() => setSelectedAgentStep(null)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}
                >
                  <X size={14} />
                </button>
              </div>

              {selectedAgentStep === 'intake' && (
                <div className="telemetry-grid">
                  <div><strong>Completeness:</strong> {Math.round(completeness * 100)}%</div>
                  <div><strong>VIN Extracted:</strong> {intake_data.vin || 'MISSING'}</div>
                  <div><strong>Missing Items:</strong> {missing_fields.join(', ') || 'None'}</div>
                  <div><strong>Gate 1 Exit:</strong> {completeness < 1.0 ? 'HALTED (NEEDS_INFO)' : 'PASSED'}</div>
                </div>
              )}

              {selectedAgentStep === 'policy' && (
                <div className="telemetry-grid">
                  <div><strong>PAS Status:</strong> {policy_validation.active ? 'ACTIVE' : 'LAPSED / EXCLUDED'}</div>
                  <div><strong>Standard Deductible:</strong> ${policy_validation.deductible}</div>
                  <div><strong>FTS5 Clauses Cited:</strong> {policy_validation.citations?.length || 0}</div>
                  <div><strong>Gate 2 Exit:</strong> {isPolicyPassed ? 'PASSED' : 'BYPASS TO DENIAL DRAFT'}</div>
                </div>
              )}

              {selectedAgentStep === 'fraud' && (
                <div className="telemetry-grid">
                  <div><strong>Fraud Score:</strong> {fraud_report.fraud_score} / 100</div>
                  <div><strong>pHash Match:</strong> {fraud_report.duplicate_matches?.length ? 'DUPLICATE FOUND' : 'CLEAN'}</div>
                  <div><strong>EXIF Discrepancy:</strong> {fraud_report.exif_discrepancies?.length ? 'PREDATES LOSS' : 'VERIFIED'}</div>
                  <div><strong>Gate 3 Exit:</strong> {isFraudHalted ? 'FREEZE & REFER TO SIU' : 'PASSED (<75)'}</div>
                </div>
              )}

              {selectedAgentStep === 'risk' && (
                <div className="telemetry-grid">
                  <div><strong>OEM Approved Estimate:</strong> ${approvedEst}</div>
                  <div><strong>Depreciation:</strong> ${depreciation}</div>
                  <div><strong>Assigned Tier:</strong> {risk_assessment.risk_tier}</div>
                  <div><strong>Valuation Notes:</strong> {risk_assessment.valuation_notes}</div>
                </div>
              )}

              {selectedAgentStep === 'settle' && (
                <div className="telemetry-grid">
                  <div><strong>Proposed Payout:</strong> ${proposedPayout}</div>
                  <div><strong>Authority Limit:</strong> $5,000.00</div>
                  <div><strong>Simulated Txn:</strong> {settlement_decision.txn_ref || 'PENDING'}</div>
                  <div><strong>Gate 4 Exit:</strong> {isStpSettled ? 'SIMULATED_STP (Auto-Pay)' : 'ADJUSTER_APPROVAL'}</div>
                </div>
              )}

              {selectedClaim.trace_url && (
                <div style={{ marginTop: '0.65rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem' }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    Trace ID: <code style={{ color: '#f472b6' }}>{selectedClaim.trace_id}</code>
                  </span>
                  <a 
                    href={selectedClaim.trace_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#f472b6', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}
                  >
                    <span>View Node in Langfuse</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
              )}
            </div>
          )}
        </div>


        {/* Raw State View Toggle */}
        {showRawJson ? (
          <div className="panel" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
              Canonical Shared ClaimState (JSON)
            </div>
            <pre style={{
              background: '#04070d',
              padding: '1rem',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: '#38bdf8',
              maxHeight: '450px',
              overflowY: 'auto'
            }}>
              {JSON.stringify(selectedClaim, null, 2)}
            </pre>
          </div>
        ) : (
          <>
            {/* Route Decision Summary Banner */}
            <div style={{
              background: 'var(--bg-surface-2)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '0.85rem 1.15rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <span className="badge-tag badge-tag-info" style={{ fontSize: '0.7rem' }}>
                  Route Logic
                </span>
                <span style={{ fontSize: '0.85rem', color: '#e2e8f0', fontWeight: 500 }}>
                  {route_reason}
                </span>
              </div>
              {settlement_decision.txn_ref && (
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#34d399' }}>
                  Txn Ref: {settlement_decision.txn_ref}
                </span>
              )}
            </div>

            {/* Financial Settlement Arithmetic Matrix */}
            <div className="math-matrix-box">
              <div className="math-matrix-header">
                <span>Deterministic Settlement Arithmetic Matrix</span>
                <span style={{ color: 'var(--text-tertiary)' }}>Formula: max(0, Approved - Deductible - Depreciation)</span>
              </div>

              <div className="formula-flow-grid">
                <div className="formula-item">
                  <span className="formula-lbl">OEM Benchmark</span>
                  <span className="formula-val" style={{ color: '#38bdf8' }}>${approvedEst.toLocaleString()}</span>
                </div>

                <span className="formula-op">-</span>

                <div className="formula-item">
                  <span className="formula-lbl">Policy Deductible</span>
                  <span className="formula-val" style={{ color: '#f59e0b' }}>${deductible.toLocaleString()}</span>
                </div>

                <span className="formula-op">-</span>

                <div className="formula-item">
                  <span className="formula-lbl">Age Depreciation</span>
                  <span className="formula-val" style={{ color: '#f59e0b' }}>${depreciation.toLocaleString()}</span>
                </div>

                <span className="formula-op">=</span>

                <div className="formula-item">
                  <span className="formula-lbl">Net Proposed Payout</span>
                  <span className="formula-val" style={{ color: '#34d399', fontSize: '1.3rem' }}>
                    ${proposedPayout.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>

            {/* Adjuster Action Console (When Task is Pending) */}
            {activeTask && (
              <div className="adjudication-action-console">
                <div className="console-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, fontSize: '0.85rem' }}>
                    <AlertTriangle size={15} color="#f59e0b" />
                    <span>Human Review Action Required: {activeTask.task_type}</span>
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
                    <span>Confirm Denial</span>
                  </button>

                  <button 
                    onClick={() => handleDecision('REQUEST_INFO')}
                    className="btn-ui btn-ui-subtle"
                    disabled={isSubmitting}
                  >
                    <MessageSquare size={13} />
                    <span>Request Claimant Info</span>
                  </button>
                </div>
              </div>
            )}

            {/* Dossier Tabs: Policy Evidence, Forensics, Audit Log */}
            <div className="panel" style={{ overflow: 'hidden' }}>
              <div className="dossier-tabs-nav" style={{ background: 'var(--bg-surface-2)' }}>
                <button 
                  className={`dossier-tab-btn ${dossierTab === 'policy' ? 'active' : ''}`}
                  onClick={() => setDossierTab('policy')}
                >
                  <BookOpen size={14} />
                  <span>Policy RAG Evidence ({policy_validation.citations?.length || 0})</span>
                </button>

                <button 
                  className={`dossier-tab-btn ${dossierTab === 'forensics' ? 'active' : ''}`}
                  onClick={() => setDossierTab('forensics')}
                >
                  <ShieldAlert size={14} />
                  <span>Forensics & pHash ({fraud_report.flags?.length || 0})</span>
                </button>

                <button 
                  className={`dossier-tab-btn ${dossierTab === 'audit' ? 'active' : ''}`}
                  onClick={() => setDossierTab('audit')}
                >
                  <History size={14} />
                  <span>Claim Audit Trail ({audit_events.length})</span>
                </button>
              </div>

              <div style={{ padding: '1.25rem' }}>
                {/* Sub-tab 1: Policy Evidence */}
                {dossierTab === 'policy' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', background: 'var(--bg-surface-1)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                      <div>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>PAS Policy Status</span>
                        <div style={{ fontWeight: 700, color: policy_validation.active ? '#34d399' : '#f87171' }}>
                          {policy_validation.active ? 'ACTIVE' : 'LAPSED / EXCLUDED'}
                        </div>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Standard Deductible</span>
                        <div style={{ fontWeight: 700, color: '#fff' }}>${policy_validation.deductible}</div>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Incident Coverage Limit</span>
                        <div style={{ fontWeight: 700, color: '#fff' }}>${(policy_validation.policy_limit || 0).toLocaleString()}</div>
                      </div>
                    </div>

                    {policy_validation.coverage_explanation && (
                      <div style={{
                        background: 'rgba(59, 130, 246, 0.05)',
                        border: '1px solid rgba(59, 130, 246, 0.25)',
                        padding: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8rem',
                        color: '#c7d2fe'
                      }}>
                        <strong>Gemini 2.5 Flash Grounded Determination:</strong> {policy_validation.coverage_explanation}
                      </div>
                    )}

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                      {policy_validation.citations?.map((c, i) => (
                        <div key={i} className="citation-block">
                          <div className="citation-title-row">
                            <span>{c.section_title}</span>
                            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.7rem' }}>
                              {c.source_file} • Page {c.page_number}
                            </span>
                          </div>
                          <div className="citation-body">{c.chunk_text}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Sub-tab 2: Forensics */}
                {dossierTab === 'forensics' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface-1)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                      <div>
                        <span style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>Composite Fraud Score</span>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: fraud_report.fraud_score >= 75 ? '#f87171' : '#34d399' }}>
                          {fraud_report.fraud_score} / 100
                        </div>
                      </div>
                      <span className={`badge-tag ${fraud_report.siu_escalate ? 'badge-tag-siu' : 'badge-tag-stp'}`}>
                        {fraud_report.siu_escalate ? 'GATE 3: SIU ESCALATION' : 'PASSED (LOW RISK)'}
                      </span>
                    </div>

                    {fraud_report.duplicate_matches?.length > 0 && (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Photo ID</th>
                            <th>Perceptual Hash</th>
                            <th>Prior Settled Claim</th>
                            <th>Investigation Note</th>
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
                    )}

                    {fraud_report.flags?.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                        {fraud_report.flags.map((f, i) => (
                          <div key={i} style={{ fontSize: '0.78rem', color: '#f87171', background: 'rgba(239, 68, 68, 0.08)', padding: '0.4rem 0.6rem', borderRadius: '4px' }}>
                            • {f}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Sub-tab 3: Audit Trail */}
                {dossierTab === 'audit' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    {audit_events.map((ev, i) => (
                      <div key={i} style={{ background: 'var(--bg-surface-1)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                          <span className="badge-tag badge-tag-info">{ev.stage}</span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                            {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : 'N/A'}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#e2e8f0' }}>{ev.route_reason}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
