import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Check, Database, FileWarning, UploadCloud, X } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

const SOURCES = [
  {
    type: "SAP_FUEL",
    title: "SAP Fuel & Procurement",
    description: "MB51-style export with German headers, plant lookup, and fuel unit normalization.",
  },
  {
    type: "UTILITY_ELECTRICITY",
    title: "Utility Electricity",
    description: "Portal billing export with meters, billing periods, kWh, supplier, and tariff data.",
  },
  {
    type: "CORPORATE_TRAVEL",
    title: "Corporate Travel",
    description: "Concur/Navan-style travel expenses with route handling and category emissions.",
  },
];

const FILTERS = [
  { key: "", label: "All" },
  { key: "PENDING", label: "Pending" },
  { key: "FLAGGED", label: "Flagged" },
  { key: "APPROVED", label: "Approved" },
  { key: "REJECTED", label: "Rejected" },
];

function currency(value) {
  return Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function App() {
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [filter, setFilter] = useState("");
  const [status, setStatus] = useState({});
  const [refreshToken, setRefreshToken] = useState(0);

  const recordsUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (filter === "FLAGGED") params.set("flagged", "true");
    if (["PENDING", "APPROVED", "REJECTED"].includes(filter)) {
      params.set("review_status", filter);
    }
    return `${API_BASE}/records/?${params.toString()}`;
  }, [filter]);

  useEffect(() => {
    fetch(recordsUrl)
      .then((res) => res.json())
      .then(setRecords)
      .catch(() => setRecords([]));
  }, [recordsUrl, refreshToken]);

  useEffect(() => {
    fetch(`${API_BASE}/batches/`)
      .then((res) => res.json())
      .then(setBatches)
      .catch(() => setBatches([]));
  }, [refreshToken]);

  async function uploadFile(sourceType, file) {
    const body = new FormData();
    body.append("source_type", sourceType);
    body.append("file", file);
    body.append("uploaded_by", "demo.analyst");
    setStatus((prev) => ({ ...prev, [sourceType]: "Uploading..." }));

    const response = await fetch(`${API_BASE}/upload/`, { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) {
      setStatus((prev) => ({ ...prev, [sourceType]: payload.detail || "Upload failed" }));
      return;
    }
    setStatus((prev) => ({
      ...prev,
      [sourceType]: `${payload.summary.total_rows} rows, ${payload.summary.suspicious_rows} flagged`,
    }));
    setRefreshToken((value) => value + 1);
  }

  async function review(id, reviewStatus) {
    await fetch(`${API_BASE}/records/${id}/review/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        review_status: reviewStatus,
        reviewed_by: "demo.analyst",
        note: `Marked ${reviewStatus.toLowerCase()} during analyst review.`,
      }),
    });
    setRefreshToken((value) => value + 1);
  }

  const totals = records.reduce(
    (acc, record) => {
      acc.emissions += Number(record.emissions_kg_co2e || 0);
      if (record.suspicious) acc.flagged += 1;
      if (record.review_status === "PENDING") acc.pending += 1;
      return acc;
    },
    { emissions: 0, flagged: 0, pending: 0 }
  );

  return (
    <main className="min-h-screen bg-field text-ink">
      <section className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-mint">Breathe ESG</p>
            <h1 className="mt-2 text-3xl font-semibold">Enterprise data ingestion review</h1>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Metric label="Pending" value={totals.pending} />
            <Metric label="Flagged" value={totals.flagged} />
            <Metric label="kg CO2e" value={currency(totals.emissions)} />
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6">
        <section>
          <div className="mb-3 flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-mint" />
            <h2 className="text-lg font-semibold">Upload source exports</h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {SOURCES.map((source) => (
              <UploadCard
                key={source.type}
                source={source}
                status={status[source.type]}
                onUpload={uploadFile}
              />
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="overflow-hidden rounded-lg border border-line bg-white">
            <div className="flex flex-col gap-3 border-b border-line px-4 py-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-mint" />
                <h2 className="text-lg font-semibold">Analyst review queue</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {FILTERS.map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setFilter(item.key)}
                    className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
                      filter === item.key
                        ? "border-mint bg-mint text-white"
                        : "border-line bg-white text-ink hover:bg-field"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <RecordsTable records={records} onReview={review} />
          </div>
          <BatchPanel batches={batches} />
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-line bg-field px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}

function UploadCard({ source, status, onUpload }) {
  return (
    <label className="block rounded-lg border border-line bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{source.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{source.description}</p>
        </div>
        <UploadCloud className="h-5 w-5 shrink-0 text-slate-500" />
      </div>
      <input
        type="file"
        accept=".csv,text/csv"
        className="mt-4 block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-mint file:px-3 file:py-2 file:font-medium file:text-white"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(source.type, file);
          event.target.value = "";
        }}
      />
      <p className="mt-3 min-h-5 text-sm font-medium text-slate-700">{status}</p>
    </label>
  );
}

function RecordsTable({ records, onReview }) {
  if (!records.length) {
    return <div className="px-4 py-12 text-center text-sm text-slate-500">No records in this view.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-line text-sm">
        <thead className="bg-field text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Source</th>
            <th className="px-4 py-3">Record</th>
            <th className="px-4 py-3">Scope</th>
            <th className="px-4 py-3">Category</th>
            <th className="px-4 py-3">Activity</th>
            <th className="px-4 py-3 text-right">kg CO2e</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Flags</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {records.map((record) => (
            <tr key={record.id} className={record.suspicious ? "bg-amber-50" : "bg-white"}>
              <td className="px-4 py-3 font-medium">{record.source_type}</td>
              <td className="px-4 py-3">{record.source_record_id || `#${record.id}`}</td>
              <td className="px-4 py-3">{record.scope}</td>
              <td className="px-4 py-3">{record.category}</td>
              <td className="px-4 py-3">{record.activity_date || "-"}</td>
              <td className="px-4 py-3 text-right font-medium">{currency(record.emissions_kg_co2e)}</td>
              <td className="px-4 py-3">
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold">
                  {record.locked_for_audit ? "LOCKED" : record.review_status}
                </span>
              </td>
              <td className="max-w-xs px-4 py-3 text-xs text-slate-600">
                {[...record.flags, ...record.validation_errors].join(", ") || "-"}
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  <button
                    aria-label="Approve record"
                    title="Approve"
                    onClick={() => onReview(record.id, "APPROVED")}
                    className="rounded-md border border-line p-2 text-mint hover:bg-field"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                  <button
                    aria-label="Reject record"
                    title="Reject"
                    onClick={() => onReview(record.id, "REJECTED")}
                    className="rounded-md border border-line p-2 text-red-700 hover:bg-field"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BatchPanel({ batches }) {
  return (
    <aside className="rounded-lg border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <FileWarning className="h-5 w-5 text-amber" />
          <h2 className="text-lg font-semibold">Recent batches</h2>
        </div>
      </div>
      <div className="divide-y divide-line">
        {batches.length === 0 && <p className="px-4 py-6 text-sm text-slate-500">No uploads yet.</p>}
        {batches.map((batch) => (
          <div key={batch.id} className="px-4 py-3 text-sm">
            <div className="font-semibold">{batch.data_source.source_type}</div>
            <div className="mt-1 text-slate-600">{batch.original_filename}</div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <Metric label="Rows" value={batch.total_rows} />
              <Metric label="Flags" value={batch.suspicious_rows} />
              <Metric label="Errors" value={batch.rejected_rows} />
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

createRoot(document.getElementById("root")).render(<App />);
