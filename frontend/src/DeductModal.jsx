import { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function DeductModal({ varieties, onClose, onSuccess }) {
  const [varietyId, setVarietyId] = useState("");
  const [grams, setGrams] = useState("");
  const [units, setUnits] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);


  const selectedVariety = varieties.find((v) => v.id === Number(varietyId));
  const isWeightBased = selectedVariety?.tracking_type === "weight";
  const isUnitBased = selectedVariety?.tracking_type === "units";

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!varietyId) {
      setError("Select a product.");
      return;
    }

    if (isWeightBased && !grams) {
      setError("Enter the grams.");
      return;
    }

    if (isUnitBased && !units) {
      setError("Enter the units.");
      return;
    }

    setSubmitting(true);
    try {
      const body = {
        variety_id: Number(varietyId),
        grams: isWeightBased ? Number(grams) : null,
        units: isUnitBased ? Number(units) : null,
      };

      const res = await fetch(`${API_BASE}/deduct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Removal failed");
      }

      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2 className="modal__title">Manual Removal</h2>
          <button className="modal__close" onClick={onClose}>×</button>
        </div>

        <form className="modal__form" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field__label">Product</span>
            <select
              className="field__input"
              value={varietyId}
              onChange={(e) => setVarietyId(e.target.value)}
            >
              <option value="">Select a product...</option>
              {varieties.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.tracking_type === "weight" ? "g" : "units"})
                </option>
              ))}
            </select>
          </label>

          {isWeightBased && (
            <label className="field">
              <span className="field__label">Grams to remove</span>
              <input
                className="field__input"
                type="number"
                min="1"
                value={grams}
                onChange={(e) => setGrams(e.target.value)}
                placeholder="e.g. 500"
              />
            </label>
          )}

          {isUnitBased && (
            <label className="field">
              <span className="field__label">Units to remove</span>
              <input
                className="field__input"
                type="number"
                min="1"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
                placeholder="e.g. 2"
              />
            </label>
          )}

          {error && <div className="modal__error">{error}</div>}

          <button
            className="modal__submit modal__submit--deduct"
            type="submit"
            disabled={submitting || !varietyId}
          >
            {submitting ? "Removing..." : "Remove"}
          </button>
        </form>
      </div>
    </div>
  );
}