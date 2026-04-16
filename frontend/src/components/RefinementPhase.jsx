import React, { useState } from 'react';
import { useSchema } from '../hooks/useSchema';
import { generateSQL, refineSchema } from '../utils/api';

export function RefinementPhase() {
  const [refinement, setRefinement] = useState('');
  const [selectedDialect, setSelectedDialect] = useState('PostgreSQL');
  const { state, setLoading, setError, setMermaid, setSchema, setSql, addToChat } = useSchema();

  const handleRefine = async (e) => {
    e.preventDefault();
    if (!refinement.trim() || !state.sessionId) return;

    try {
      setLoading(true);
      setError(null);

      const result = await refineSchema(state.sessionId, refinement);
      setMermaid(result.mermaid_diagram);
      if (result.updated_schema) {
        setSchema(result.updated_schema);
      }
      addToChat({ role: 'user', content: refinement });
      addToChat({ role: 'assistant', content: 'Applied schema refinement and regenerated the diagram.' });
      setRefinement('');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSQL = async () => {
    if (!state.sessionId) return;

    try {
      setLoading(true);
      setError(null);

      const result = await generateSQL(state.sessionId, selectedDialect);
      setSql(result.content);
      addToChat({ role: 'assistant', content: `Generated ${selectedDialect} SQL.` });
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-white/10 bg-white/85 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur">
        <h3 className="text-lg font-semibold text-slate-950">Refine schema</h3>
        <p className="mt-1 text-sm text-slate-600">
          Ask for targeted changes after the first diagram is generated.
        </p>

        <form onSubmit={handleRefine} className="mt-4 space-y-4">
          <textarea
            value={refinement}
            onChange={(e) => setRefinement(e.target.value)}
            placeholder="Example: add timestamps to the order table, make email unique, or split payment into a separate entity."
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15"
            rows={4}
            disabled={state.loading}
          />

          <button
            type="submit"
            disabled={!refinement.trim() || state.loading}
            className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {state.loading ? 'Refining...' : 'Apply refinement'}
          </button>
        </form>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/85 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur">
        <h3 className="text-lg font-semibold text-slate-950">Generate SQL</h3>
        <p className="mt-1 text-sm text-slate-600">Export a clean DDL script with seed inserts for your target database.</p>

        <div className="mt-4 space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Dialect</label>
            <select
              value={selectedDialect}
              onChange={(e) => setSelectedDialect(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15"
            >
              <option>PostgreSQL</option>
              <option>MySQL</option>
              <option>SQLite</option>
              <option>SQLServer</option>
              <option>Oracle</option>
            </select>
          </div>

          {state.error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
              {state.error}
            </div>
          )}

          <button
            onClick={handleGenerateSQL}
            disabled={state.loading}
            className="inline-flex w-full items-center justify-center rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {state.loading ? 'Generating SQL...' : 'Generate SQL'}
          </button>
        </div>
      </div>
    </div>
  );
}
