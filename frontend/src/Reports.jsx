import { useEffect, useState } from "react";

const API_BASE = "";

// One entry per report endpoint. `columns` maps the JSON keys the API returns
// to a header label and an optional formatter, so adding a report is one entry.
const REPORTS = [
  {
    key: "stock",
    title: "Stock per variety",
    path: "/reports/stock-per-variety",
    columns: [
      { key: "name", label: "Variety" },
      { key: "remaining", label: "Remaining", format: (v, row) => `${v}${row.tracking_type === "weight" ? "g" : " units"}` },
      { key: "active_batches", label: "Active batches" },
    ],
  },
  {
    key: "fefo",
    title: "Next batch to use (FEFO)",
    path: "/reports/fefo-next",
    columns: [
      { key: "name", label: "Variety" },
      { key: "min_expiry", label: "Expires", format: formatDate },
      { key: "remaining", label: "Remaining" },
    ],
  },
  {
    key: "last7",
    title: "Movements, last 7 days",
    path: "/reports/last7",
    columns: [
      { key: "timestamp", label: "When", format: formatDateTime },
      { key: "name", label: "Variety", format: (v) => v ?? "—" },
      { key: "direction", label: "Direction" },
      { key: "stock", label: "Qty" },
    ],
  },
];

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function ReportTable({ report }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}${report.path}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${report.title}`);
        return res.json();
      })
      .then((data) => { if (!cancelled) setRows(data); })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [report]);

  return (
    <section className="report">
      <h2 className="report__title">{report.title}</h2>
      {error && <div className="app__status app__status--error">{error}</div>}
      {!error && rows === null && <div className="app__status">Loading...</div>}
      {rows && rows.length === 0 && <div className="app__status">No rows.</div>}
      {rows && rows.length > 0 && (
        <div className="report__scroll">
          <table className="report__table">
            <thead>
              <tr>
                {report.columns.map((c) => <th key={c.key}>{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {report.columns.map((c) => (
                    <td key={c.key}>{c.format ? c.format(row[c.key], row) : row[c.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function Reports() {
  return (
    <div className="reports">
      {REPORTS.map((r) => <ReportTable key={r.key} report={r} />)}
    </div>
  );
}
