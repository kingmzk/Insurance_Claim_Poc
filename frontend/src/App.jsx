import React, { useState, useEffect } from 'react';
import EnterpriseHeader from './components/EnterpriseHeader';
import DashboardView from './views/DashboardView';
import ClaimsWorkbenchView from './views/ClaimsWorkbenchView';
import ReviewQueueView from './views/ReviewQueueView';
import AuditView from './views/AuditView';
import CustomClaimModal from './components/CustomClaimModal';
import { CheckCircle, AlertTriangle } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'workbench' | 'reviews' | 'audit'
  const [claims, setClaims] = useState([]);
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [reviewTasks, setReviewTasks] = useState([]);
  const [activeScenario, setActiveScenario] = useState('routine_stp');
  const [loadingScenario, setLoadingScenario] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch claims and review tasks
  const refreshData = async () => {
    try {
      const [claimsRes, reviewsRes] = await Promise.all([
        fetch('/api/claims'),
        fetch('/api/reviews?status=PENDING')
      ]);

      if (claimsRes.ok) {
        const claimsData = await claimsRes.json();
        setClaims(claimsData);
        if (claimsData.length > 0 && !selectedClaim) {
          setSelectedClaim(claimsData[0].state);
        } else if (selectedClaim) {
          const updated = claimsData.find(c => c.claim_id === selectedClaim.claim_id);
          if (updated) setSelectedClaim(updated.state);
        }
      }

      if (reviewsRes.ok) {
        const reviewsData = await reviewsRes.json();
        setReviewTasks(reviewsData);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleSelectClaim = (state) => {
    setSelectedClaim(state);
  };

  const handleOpenClaimInWorkbench = (state) => {
    setSelectedClaim(state);
    setCurrentView('workbench');
  };

  // Run Scenario
  const handleRunScenario = async (scenarioKey) => {
    setLoadingScenario(scenarioKey);
    setActiveScenario(scenarioKey);

    try {
      const res = await fetch(`/api/scenarios/run/${scenarioKey}`, { method: 'POST' });
      if (!res.ok) throw new Error('Scenario execution failed');

      const finalState = await res.json();
      setSelectedClaim(finalState);
      await refreshData();

      if (finalState.current_status === 'SETTLED_STP') {
        showToast(`Scenario 1: STP Auto-Disbursement approved ($${finalState.settlement_decision?.net_payout?.toLocaleString()})! Txn: ${finalState.settlement_decision?.txn_ref}`, 'success');
      } else if (finalState.current_status === 'NEEDS_INFO') {
        showToast(`Scenario 2: Incomplete FNOL halted at Gate 1 (Missing ${finalState.missing_fields?.join(', ')})`, 'warning');
      } else if (finalState.current_status === 'PENDING_REVIEW') {
        showToast(`Scenario Queued for Review: ${finalState.route_reason}`, 'warning');
      }

      // Automatically open the executed claim in Workbench so user sees the decision immediately
      setCurrentView('workbench');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingScenario(null);
    }
  };

  // Submit custom claim
  const handleSubmitCustom = async (payload) => {
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/claims/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Submission failed');

      const finalState = await res.json();
      setSelectedClaim(finalState);
      await refreshData();
      setIsModalOpen(false);
      showToast(`Custom Claim ${finalState.claim_id} orchestrated! Status: ${finalState.current_status}`, 'success');
      setCurrentView('workbench');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Adjuster decision on review task
  const handleRecordDecision = async (taskId, decision, notes, adjustedPayout) => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/reviews/${taskId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          notes,
          adjusted_payout: adjustedPayout,
          reviewer_id: 'senior_adjuster_01'
        })
      });
      if (!res.ok) throw new Error('Review decision failed');

      const data = await res.json();
      setSelectedClaim(data.claim_state);
      await refreshData();
      showToast(`Adjudication recorded as ${decision}! Status: ${data.updated_claim_status}`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset Demo Database
  const handleResetDb = async () => {
    if (!window.confirm('Reset all demo claims, review tasks, and audit logs to clean state?')) return;
    setIsResetting(true);
    try {
      const res = await fetch('/api/database/reset', { method: 'POST' });
      if (res.ok) {
        setSelectedClaim(null);
        await refreshData();
        showToast('Demo database cleared successfully. Ready for clean scenario execution.', 'success');
      }
    } catch (err) {
      showToast('Failed to reset database', 'error');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* 1. Top Enterprise Nav */}
      <EnterpriseHeader 
        currentView={currentView}
        onViewChange={setCurrentView}
        pendingCount={reviewTasks.length}
        onNewClaim={() => setIsModalOpen(true)}
        onResetDb={handleResetDb}
        isResetting={isResetting}
      />

      {/* Floating Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '65px',
          right: '20px',
          zIndex: 999,
          background: toast.type === 'success' ? '#065f46' : (toast.type === 'warning' ? '#78350f' : '#881337'),
          color: '#fff',
          padding: '0.65rem 1rem',
          borderRadius: 'var(--radius-sm)',
          boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
          fontSize: '0.8rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          border: '1px solid rgba(255,255,255,0.2)',
          fontFamily: 'var(--font-sans)',
          animation: 'fadeIn 0.2s ease'
        }}>
          {toast.type === 'success' ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* 2. Primary Views */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {currentView === 'dashboard' && (
          <DashboardView 
            claims={claims}
            reviewTasks={reviewTasks}
            onRunScenario={handleRunScenario}
            loadingScenario={loadingScenario}
            onOpenClaimInWorkbench={handleOpenClaimInWorkbench}
          />
        )}

        {currentView === 'workbench' && (
          <ClaimsWorkbenchView 
            claims={claims}
            selectedClaim={selectedClaim}
            onSelectClaim={handleSelectClaim}
            reviewTasks={reviewTasks}
            onRecordDecision={handleRecordDecision}
            isSubmitting={isSubmitting}
          />
        )}

        {currentView === 'reviews' && (
          <ReviewQueueView 
            tasks={reviewTasks}
            onRecordDecision={handleRecordDecision}
            isSubmitting={isSubmitting}
            onOpenClaimInWorkbench={handleOpenClaimInWorkbench}
          />
        )}

        {currentView === 'audit' && (
          <AuditView 
            claims={claims}
            onOpenClaimInWorkbench={handleOpenClaimInWorkbench}
          />
        )}
      </main>

      {/* Custom Claim Modal */}
      <CustomClaimModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmitCustom={handleSubmitCustom}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
