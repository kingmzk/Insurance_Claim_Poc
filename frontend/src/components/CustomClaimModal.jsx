import React, { useState } from 'react';
import { X, Send, FilePlus, FileText, ShieldAlert, AlertCircle, Loader2 } from 'lucide-react';

const POLICY_PRESETS = {
  'POL-AUTO-99201': {
    name: 'POL-AUTO-99201 (Active Comprehensive - $500 Ded)',
    claimant: 'John Doe',
    vehicle: '2023 Honda Accord',
    vin: '1HGCR2F83HA001234',
    defaultAmt: 3500.00,
    lossType: 'collision',
    description: 'Front passenger fender scratched and dented by parking pillar during turn.'
  },
  'POL-AUTO-88104': {
    name: 'POL-AUTO-88104 (Luxury $1k Ded - Marcus Vance)',
    claimant: 'Marcus Vance',
    vehicle: '2024 Audi RS6 Avant',
    vin: 'WAUZZZF28HA009876',
    defaultAmt: 7800.00,
    lossType: 'collision',
    description: 'Cracked carbon fiber front bumper and sensor housing from road debris.'
  },
  'POL-AUTO-77002': {
    name: 'POL-AUTO-77002 (Lapsed Policy - Sarah Jenkins)',
    claimant: 'Sarah Jenkins',
    vehicle: '2022 Toyota Prius',
    vin: 'JTDKN3DU5E1005544',
    defaultAmt: 2100.00,
    lossType: 'collision',
    description: 'Rear bumper scratch in grocery parking lot.'
  }
};

export default function CustomClaimModal({ isOpen, onClose, onSubmitCustom, isSubmitting }) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    policy_no: 'POL-AUTO-99201',
    claimant_name: 'John Doe',
    loss_date: new Date().toISOString().slice(0, 10),
    loss_type: 'collision',
    claimed_amt: 3500.00,
    vin: '1HGCR2F83HA001234',
    vehicle_make_model: '2023 Honda Accord',
    incident_description: 'Front passenger fender scratched and dented by parking pillar during turn.',
    include_estimate: true,
    simulate_fraud: false
  });

  const handlePolicyChange = (policyNo) => {
    const preset = POLICY_PRESETS[policyNo];
    if (preset) {
      setFormData(prev => ({
        ...prev,
        policy_no: policyNo,
        claimant_name: preset.claimant,
        vehicle_make_model: preset.vehicle,
        vin: preset.vin,
        claimed_amt: preset.defaultAmt,
        loss_type: preset.lossType,
        incident_description: preset.description
      }));
    } else {
      setFormData(prev => ({ ...prev, policy_no: policyNo }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const documents = [];
    if (formData.include_estimate) {
      documents.push({
        doc_type: 'repair_estimate',
        filename: `${formData.claimant_name.toLowerCase().replace(/\s+/g, '_')}_repair_estimate.pdf`
      });
    }

    const photos = [];
    if (formData.simulate_fraud) {
      photos.push({
        photo_id: 'custom_fraud_photo',
        filename: 'custom_damage_fraud.jpg',
        phash: 'a8b4c9e1f203d456', // Matches duplicate registry hash in forensics
        exif_timestamp: '2025-10-01T08:00:00',
        reported_incident_timestamp: `${formData.loss_date}T10:00:00`,
        is_tampered: true
      });
    } else {
      photos.push({
        photo_id: 'custom_clean_photo',
        filename: 'custom_clean_damage.jpg',
        phash: '778899aabbccdde0',
        exif_timestamp: `${formData.loss_date}T10:30:00`,
        reported_incident_timestamp: `${formData.loss_date}T10:00:00`,
        is_tampered: false
      });
    }

    const payload = {
      policy_no: formData.policy_no,
      claimant_name: formData.claimant_name,
      loss_date: formData.loss_date,
      loss_type: formData.loss_type,
      claimed_amt: parseFloat(formData.claimed_amt) || 0,
      vin: formData.vin ? formData.vin.trim() : null,
      vehicle_make_model: formData.vehicle_make_model,
      incident_description: formData.incident_description,
      documents,
      photos
    };

    onSubmitCustom(payload);
  };

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget && !isSubmitting) onClose(); }}>
      <div className="modal-card">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge">
              <FilePlus size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <h3 className="modal-title">Submit Custom Test Claim</h3>
                <span className="modal-badge">Live Pipeline Harness</span>
              </div>
            </div>
          </div>
          <button 
            type="button"
            onClick={onClose}
            className="modal-close-btn"
            disabled={isSubmitting}
            title="Close (Esc)"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Row 1: Policy Selection & Claimant */}
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">
                  <span>Authoritative Policy</span>
                  <span className="form-label-required">*</span>
                </label>
                <select 
                  className="form-select"
                  value={formData.policy_no}
                  onChange={(e) => handlePolicyChange(e.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="POL-AUTO-99201">POL-AUTO-99201 (Active Comprehensive • $500 Ded)</option>
                  <option value="POL-AUTO-88104">POL-AUTO-88104 (Luxury $1k Ded • Marcus Vance)</option>
                  <option value="POL-AUTO-77002">POL-AUTO-77002 (Lapsed Policy • Sarah Jenkins)</option>
                  <option value="POL-CUSTOM-99999">POL-CUSTOM-99999 (Unregistered / Invalid Policy)</option>
                </select>
                <span className="form-hint">PAS registry match verifies active coverage & limits</span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  <span>Claimant Full Name</span>
                  <span className="form-label-required">*</span>
                </label>
                <input 
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. John Doe"
                  value={formData.claimant_name}
                  onChange={(e) => setFormData({ ...formData, claimant_name: e.target.value })}
                  disabled={isSubmitting}
                />
                <span className="form-hint">Used for claimant identity and settlement routing</span>
              </div>
            </div>

            {/* Row 2: Claimed Cost & Loss Type */}
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">
                  <span>Claimed Repair Amount ($)</span>
                  <span className="form-label-required">*</span>
                </label>
                <input 
                  type="number"
                  step="0.01"
                  min="0"
                  className="form-input"
                  required
                  style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#34d399' }}
                  value={formData.claimed_amt}
                  onChange={(e) => setFormData({ ...formData, claimed_amt: e.target.value })}
                  disabled={isSubmitting}
                />
                <span className="form-hint">Values &gt; $5,000 exceed STP limit and require human approval</span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  <span>Loss Category</span>
                  <span className="form-label-required">*</span>
                </label>
                <select 
                  className="form-select"
                  value={formData.loss_type}
                  onChange={(e) => setFormData({ ...formData, loss_type: e.target.value })}
                  disabled={isSubmitting}
                >
                  <option value="collision">Collision (Standard)</option>
                  <option value="rear_collision">Rear Impact Collision</option>
                  <option value="front_impact">Frontal Crash / Structural</option>
                  <option value="side_impact">Side-swipe Collision</option>
                  <option value="weather">Weather / Storm Damage</option>
                  <option value="theft">Theft / Break-in</option>
                </select>
                <span className="form-hint">RAG index retrieves specific exclusion clauses</span>
              </div>
            </div>

            {/* Row 3: Vehicle VIN & Model */}
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">
                  <span>Vehicle VIN</span>
                </label>
                <input 
                  type="text"
                  className="form-input"
                  placeholder="Leave empty to simulate Missing VIN routing"
                  value={formData.vin || ''}
                  onChange={(e) => setFormData({ ...formData, vin: e.target.value })}
                  disabled={isSubmitting}
                />
                <span className="form-hint">Empty VIN routes claim directly to Human Adjuster Review</span>
              </div>

              <div className="form-group">
                <label className="form-label">
                  <span>Make & Model</span>
                  <span className="form-label-required">*</span>
                </label>
                <input 
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. 2023 Honda Accord"
                  value={formData.vehicle_make_model}
                  onChange={(e) => setFormData({ ...formData, vehicle_make_model: e.target.value })}
                  disabled={isSubmitting}
                />
                <span className="form-hint">Cross-referenced with OEM repair database</span>
              </div>
            </div>

            {/* Row 4: Narrative Description */}
            <div className="form-group">
              <label className="form-label">
                <span>Incident Description (Narrative)</span>
                <span className="form-label-required">*</span>
              </label>
              <textarea 
                className="form-textarea"
                rows={3}
                required
                placeholder="Describe what occurred, impact direction, and damage sustained..."
                value={formData.incident_description}
                onChange={(e) => setFormData({ ...formData, incident_description: e.target.value })}
                disabled={isSubmitting}
              />
              <span className="form-hint">Evaluated by Intake & Cost Estimator agents for claim scope</span>
            </div>

            {/* Row 5: Simulation Modifiers (Toggle Cards) */}
            <div className="form-toggle-grid">
              <label className={`toggle-card ${formData.include_estimate ? 'active' : ''}`}>
                <input 
                  type="checkbox"
                  className="toggle-checkbox"
                  checked={formData.include_estimate}
                  onChange={(e) => setFormData({ ...formData, include_estimate: e.target.checked })}
                  disabled={isSubmitting}
                />
                <div className="toggle-card-content">
                  <div className="toggle-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <FileText size={14} color="#60a5fa" />
                    <span>Attach Repair Estimate Quote</span>
                  </div>
                  <div className="toggle-card-desc">
                    Generates itemized OEM parts & labor documentation for the Cost Estimator.
                  </div>
                </div>
              </label>

              <label className={`toggle-card ${formData.simulate_fraud ? 'active fraud-active' : ''}`}>
                <input 
                  type="checkbox"
                  className="toggle-checkbox fraud-checkbox"
                  checked={formData.simulate_fraud}
                  onChange={(e) => setFormData({ ...formData, simulate_fraud: e.target.checked })}
                  disabled={isSubmitting}
                />
                <div className="toggle-card-content">
                  <div className="toggle-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: formData.simulate_fraud ? '#f87171' : 'inherit' }}>
                    <ShieldAlert size={14} color={formData.simulate_fraud ? '#f87171' : '#94a3b8'} />
                    <span>Simulate Image Fraud (SIU)</span>
                  </div>
                  <div className="toggle-card-desc">
                    Injects duplicate pHash image collision to force Fraud Score &ge; 75 &amp; SIU referral.
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="modal-footer">
            <button 
              type="button" 
              onClick={onClose}
              className="btn-ui btn-ui-subtle"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-ui btn-ui-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={15} className="spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Send size={15} />
                  <span>Run Autonomous Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
