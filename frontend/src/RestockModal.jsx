import { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function RestockModal({ varieties, onClose, onSuccess }) {
  const [varietyId, setVarietyId] = useState("");
  const [grams, setGrams] = useState("");
  const [units, setUnits] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Βρίσκουμε το tracking_type του επιλεγμένου variety
  // Το .find() επιστρέφει το πρώτο στοιχείο που ταιριάζει με τη συνθήκη
  // Παρόμοιο με το .filter(...).first() στο SQLAlchemy
  const selectedVariety = varieties.find((v) => v.id === Number(varietyId));
  const isWeightBased = selectedVariety?.tracking_type === "weight";
  const isUnitBased = selectedVariety?.tracking_type === "units";

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!varietyId || !expiryDate) {
      setError("Συμπλήρωσε όλα τα πεδία.");
      return;
    }

    if (isWeightBased && !grams) {
      setError("Συμπλήρωσε τα γραμμάρια.");
      return;
    }

    if (isUnitBased && !units) {
      setError("Συμπλήρωσε τα τεμάχια.");
      return;
    }

    setSubmitting(true);
    try {
      const body = {
        variety_id: Number(varietyId),
        expiry_date: expiryDate,
        // Ανάλογα με το tracking_type, στέλνουμε το σωστό field
        // Το άλλο μένει null (Optional στο Pydantic schema)
        grams_remaining: isWeightBased ? Number(grams) : null,
        units_remaining: isUnitBased ? Number(units) : null,
      };

      const res = await fetch(`${API_BASE}/batches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error("Η αποθήκευση απέτυχε");

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
          <h2 className="modal__title">Νέα παραλαβή</h2>
          <button className="modal__close" onClick={onClose}>×</button>
        </div>

        <form className="modal__form" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field__label">Είδος</span>
            <select
              className="field__input"
              value={varietyId}
              onChange={(e) => setVarietyId(e.target.value)}
            >
              <option value="">Επιλέξτε είδος...</option>
              {varieties.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.tracking_type === "weight" ? "γρ" : "τεμ"})
                </option>
              ))}
            </select>
          </label>

          {/* Δείχνουμε το σωστό field ανάλογα με το tracking_type */}
          {isWeightBased && (
            <label className="field">
              <span className="field__label">Γραμμάρια</span>
              <input
                className="field__input"
                type="number"
                min="1"
                value={grams}
                onChange={(e) => setGrams(e.target.value)}
                placeholder="π.χ. 10000"
              />
            </label>
          )}

          {isUnitBased && (
            <label className="field">
              <span className="field__label">Τεμάχια</span>
              <input
                className="field__input"
                type="number"
                min="1"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
                placeholder="π.χ. 24"
              />
            </label>
          )}

          <label className="field">
            <span className="field__label">Ημερομηνία λήξης</span>
            <input
              className="field__input"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
            />
          </label>

          {error && <div className="modal__error">{error}</div>}

          <button className="modal__submit" type="submit" disabled={submitting || !varietyId}>
            {submitting ? "Αποθήκευση..." : "Καταχώρηση"}
          </button>
        </form>
      </div>
    </div>
  );
}