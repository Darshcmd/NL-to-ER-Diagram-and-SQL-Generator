import React from 'react';

export function SQLViewer({ sqlCode }) {
  const handleCopy = () => {
    navigator.clipboard.writeText(sqlCode);
  };

  const handleDownload = () => {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(sqlCode));
    element.setAttribute('download', 'schema.sql');
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  if (!sqlCode) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-8 text-center text-slate-500 shadow-sm">
        <p>No SQL generated yet.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/90 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="flex items-center justify-between bg-slate-950 px-6 py-4">
        <h3 className="text-lg font-semibold text-white">SQL DDL + Inserts</h3>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
          >
            Copy
          </button>
          <button
            onClick={handleDownload}
            className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-400"
          >
            Download
          </button>
        </div>
      </div>
      
      <pre className="overflow-x-auto bg-slate-50 p-6 text-sm text-slate-900">
        <code>{sqlCode}</code>
      </pre>
    </div>
  );
}
