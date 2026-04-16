import React, { useState } from 'react';
import { useSchema } from '../hooks/useSchema';
import { initializeSession, uploadFile } from '../utils/api';

export function InputPhase() {
  const [inputText, setInputText] = useState('');
  const [selectedFileName, setSelectedFileName] = useState('');
  const { state, setSessionId, setInput, setFileContext, setQuestions, setLoading, setError, addToChat } = useSchema();

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true);
      setError(null);

      const result = await uploadFile(file);
      setSelectedFileName(result.filename);
      setFileContext(result.extracted_text);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      setLoading(true);
      setError(null);

      const requestText = inputText.trim();
      const requestFileContext = state.fileContext.trim() || null;
      const displayText = requestText || requestFileContext || 'No text or file provided. Using a generic schema scaffold.';

      const result = await initializeSession(requestText, requestFileContext);

      setSessionId(result.session_id);
      setInput(displayText);
      setQuestions(result.questions || []);
      addToChat({ role: 'user', content: displayText });
      addToChat({
        role: 'assistant',
        content: `Generated ${result.questions?.length || 0} clarification questions to tighten the schema.`,
      });
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl rounded-3xl border border-white/10 bg-white/80 p-8 shadow-[0_20px_80px_rgba(15,23,42,0.12)] backdrop-blur">
      <div className="mb-8">
        <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300">
          Multi-stage schema pipeline
        </span>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Natural Language to ER diagram and SQL Generation
        </h1>
        <p className="mt-3 max-w-2xl text-base text-slate-600">
          Paste a requirement, upload a PDF, or skip both and start from a generic scaffold. We’ll extract the structure, ask targeted clarifications, and generate a cleaner database design.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Requirement brief</label>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Example: Customers place orders containing multiple products. Each order needs a payment record and shipping details."
            className="min-h-40 w-full rounded-2xl border border-slate-200 bg-white px-4 py-4 text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15"
            rows={7}
            disabled={state.loading}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-[1.4fr_0.6fr]">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Upload supporting file</label>
            <input
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.csv,.txt,.docx"
              className="block w-full rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600 file:mr-4 file:rounded-full file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-slate-800"
              disabled={state.loading}
            />
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            <div className="font-medium text-slate-800">Current context</div>
            <div className="mt-2 break-words">
              {selectedFileName ? `File: ${selectedFileName}` : 'No file uploaded'}
            </div>
            <div className="mt-1">
              {state.fileContext ? `Extracted text loaded (${state.fileContext.length} chars)` : 'No extracted text yet'}
            </div>
          </div>
        </div>

        {state.error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
            {state.error}
          </div>
        )}

        <button
          type="submit"
          disabled={state.loading}
          className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state.loading ? 'Analyzing input...' : 'Start pipeline'}
        </button>
      </form>
    </div>
  );
}
