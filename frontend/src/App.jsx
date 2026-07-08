import { useEffect, useRef, useState } from "react";
import "./App.css";
import RestockModal from "./RestockModal";
import DeductModal from "./DeductModal";

const API_BASE = "http://localhost:8000";

function daysUntil(dateString) {
  const today = new Date();
  const target = new Date(dateString);
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  const diffMs = target - today;
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function urgencyLevel(days) {
  if (days < 0) return "expired";
  if (days <= 3) return "critical";
  if (days <= 10) return "soon";
  return "fresh";
}

function formatDate(dateString) {
  const d = new Date(dateString);
  return d.toLocaleDateString("el-GR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function BatchRow({ batch, trackingType }) {
  const days = daysUntil(batch.expiry_date);
  const level = urgencyLevel(days);

  let daysLabel;
  if (days < 0) daysLabel = `Έληξε πριν ${Math.abs(days)}d`;
  else if (days === 0) daysLabel = "Λήγει σήμερα";
  else daysLabel = `${days}d ακόμα`;

  // Δείχνουμε γραμμάρια ή τεμάχια ανάλογα με το tracking_type
  const quantityLabel = trackingType === "weight"
    ? `${batch.grams_remaining}γρ`
    : `${batch.units_remaining} τεμ`;

  return (
    <div className={`batch-row batch-row--${level}`}>
      <div className="batch-row__grams">{quantityLabel}</div>
      <div className="batch-row__meta">
        <span className="batch-row__date">{formatDate(batch.expiry_date)}</span>
        <span className="batch-row__days">{daysLabel}</span>
      </div>
    </div>
  );
}

function VarietySection({ variety, batches }) {
  const isWeight = variety.tracking_type === "weight";

  const varietyBatches = batches
    .filter((b) => b.variety_id === variety.id)
    .filter((b) => isWeight ? b.grams_remaining > 0 : b.units_remaining > 0)
    .sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date));

  const total = isWeight
    ? varietyBatches.reduce((sum, b) => sum + b.grams_remaining, 0)
    : varietyBatches.reduce((sum, b) => sum + b.units_remaining, 0);

  const totalLabel = isWeight ? `${total}γρ σύνολο` : `${total} τεμ σύνολο`;

  return (
    <section className="variety-section">
      <div className="variety-section__header">
        <h2 className="variety-section__name">{variety.name}</h2>
        <span className="variety-section__total">{totalLabel}</span>
      </div>
      {varietyBatches.length === 0 ? (
        <div className="variety-section__empty">Δεν υπάρχει απόθεμα</div>
      ) : (
        <div className="variety-section__batches">
          {varietyBatches.map((b) => (
            <BatchRow key={b.id} batch={b} trackingType={variety.tracking_type} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [varieties, setVarieties] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [showDeductModal, setShowDeductModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [scanValue, setScanValue] = useState("");
  const [scanMessage, setScanMessage] = useState(null);
  const scanInputRef = useRef(null);

  useEffect(() => {
    scanInputRef.current?.focus();
  }, []);

  async function handleScanSubmit(e) {
    e.preventDefault();
    const barcode = scanValue.trim();
    if (!barcode) return;

    try {
      const res = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ barcode }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "Το barcode δεν βρέθηκε");
      }

      const data = await res.json();
      setScanMessage({ type: "success", text: `Αφαιρέθηκαν ${data.grams_removed}γρ` });
      loadData();
    } catch (err) {
      setScanMessage({ type: "error", text: err.message });
    } finally {
      setScanValue("");
      scanInputRef.current?.focus();
    }
  }

  async function loadData() {
    try {
      const [varietiesRes, batchesRes] = await Promise.all([
        fetch(`${API_BASE}/varieties`),
        fetch(`${API_BASE}/batches`),
      ]);

      if (!varietiesRes.ok || !batchesRes.ok) {
        throw new Error("Αποτυχία φόρτωσης δεδομένων");
      }

      const varietiesData = await varietiesRes.json();
      const batchesData = await batchesRes.json();

      setVarieties(varietiesData);
      setBatches(batchesData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();

    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredVarieties = varieties.filter((v) =>
    v.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__heading-row">
          <div>
            <h1 className="app__title">Απόθεμα</h1>
            <p className="app__subtitle">Ξηροί καρποί &amp; αποξηραμένα φρούτα</p>
          </div>
          <button
            className="app__restock-button"
            onClick={() => setShowRestockModal(true)}
          >
            + Νέα παραλαβή
          </button>
          <button
            className="app__deduct-button"
            onClick={() => setShowDeductModal(true)}
          >
            − Αφαίρεση
          </button>
        </div>
        <form className="scan-bar" onSubmit={handleScanSubmit}>
          <input
            ref={scanInputRef}
            className="scan-bar__input"
            type="text"
            placeholder="Σκανάρισμα barcode..."
            value={scanValue}
            onChange={(e) => setScanValue(e.target.value)}
            autoFocus
          />
        </form>
        {scanMessage && (
          <div className={`scan-bar__message scan-bar__message--${scanMessage.type}`}>
            {scanMessage.text}
          </div>
        )}

        <input
          className="app__search"
          type="text"
          placeholder="Αναζήτηση είδους..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </header>

      <main className="app__main">
        {loading && <div className="app__status">Φόρτωση...</div>}
        {error && <div className="app__status app__status--error">{error}</div>}
        {!loading && !error && filteredVarieties.length === 0 && (
          <div className="app__status">Δεν βρέθηκαν είδη.</div>
        )}
        {!loading &&
          !error &&
          filteredVarieties.map((v) => (
            <VarietySection key={v.id} variety={v} batches={batches} />
          ))}
      </main>

      {showRestockModal && (
        <RestockModal
          varieties={varieties}
          onClose={() => setShowRestockModal(false)}
          onSuccess={() => {
            setShowRestockModal(false);
            loadData();
          }}
        />
      )}

      {showDeductModal && (
        <DeductModal
          varieties={varieties}
          onClose={() => setShowDeductModal(false)}
          onSuccess={() => {
            setShowDeductModal(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}