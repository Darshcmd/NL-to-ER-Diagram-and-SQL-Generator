import React from 'react';
import { useSchema } from '../hooks/useSchema';
import { InputPhase } from './InputPhase';
import { QuestionsPhase } from './QuestionsPhase';
import { MermaidDiagram } from './MermaidDiagram';
import { RefinementPhase } from './RefinementPhase';
import { SQLViewer } from './SQLViewer';
import { ChatHistory } from './ChatHistory';
import { ValidationPanel } from './ValidationPanel';

function StepBadge({ active, index, label }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
        active ? 'border-emerald-300 bg-emerald-50 text-emerald-900' : 'border-slate-200 bg-white/70 text-slate-500'
      }`}
    >
      <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${active ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'}`}>
        {index}
      </div>
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

export function MainApp() {
  const { state, reset } = useSchema();

  const hasSession = Boolean(state.sessionId);
  const hasQuestions = state.clarifyingQuestions.length > 0;
  const hasDiagram = Boolean(state.currentMermaid);
  const hasSql = Boolean(state.sqlCode);

  if (!hasSession) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.14),_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_100%)] px-4 py-10">
        <InputPhase />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.10),_transparent_28%),linear-gradient(135deg,_#f8fafc_0%,_#eef2ff_100%)]">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/70 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-700">SchemaFlow</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Multi-stage schema builder</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Requirement parsing, clarification, Chen ER generation, validation, and SQL export in one flow.
            </p>
          </div>
          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-full bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            New project
          </button>
        </div>

        <div className="mb-6 grid gap-3 md:grid-cols-4">
          <StepBadge index={1} label="Input" active={!hasQuestions && !hasDiagram} />
          <StepBadge index={2} label="Clarify" active={hasQuestions && !hasDiagram} />
          <StepBadge index={3} label="Diagram" active={hasDiagram && !hasSql} />
          <StepBadge index={4} label="SQL" active={hasSql} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-6">
            {!hasQuestions ? <QuestionsPhase /> : <MermaidDiagram diagramCode={state.currentMermaid} />}

            {state.currentSchema && <ValidationPanel />}

            {hasSql && <SQLViewer sqlCode={state.sqlCode} />}
          </div>

          <div className="space-y-6">
            {hasQuestions && !hasDiagram ? (
              <QuestionsPhase />
            ) : (
              <RefinementPhase />
            )}

            {state.currentSchema && (
              <div className="rounded-3xl border border-white/10 bg-slate-950 p-6 text-white shadow-[0_20px_80px_rgba(15,23,42,0.18)]">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300">Schema summary</p>
                <p className="mt-3 text-sm leading-6 text-slate-200">{state.currentSchema.summary}</p>
                <div className="mt-4 text-sm text-slate-300">
                  <div><span className="font-semibold text-white">Domain:</span> {state.currentSchema.domain}</div>
                  <div><span className="font-semibold text-white">Entities:</span> {state.currentSchema.entities?.length || 0}</div>
                  <div><span className="font-semibold text-white">Relationships:</span> {state.currentSchema.relationships?.length || 0}</div>
                </div>
              </div>
            )}

            <ChatHistory />
          </div>
        </div>
      </div>
    </div>
  );
}
