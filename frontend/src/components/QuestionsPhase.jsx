import React, { useEffect, useMemo, useState } from 'react';
import { useSchema } from '../hooks/useSchema';
import { confirmAnswers } from '../utils/api';

export function QuestionsPhase() {
  const { state, setLoading, setError, setMermaid, setSchema, addToChat } = useSchema();
  const [answers, setAnswers] = useState({});

  useEffect(() => {
    setAnswers((current) => {
      const nextAnswers = {};
      state.clarifyingQuestions.forEach((question) => {
        nextAnswers[question.id] = current[question.id] || '';
      });
      return nextAnswers;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.clarifyingQuestions]);

  const allAnswered = useMemo(
    () => state.clarifyingQuestions.length > 0 && state.clarifyingQuestions.every((question) => Boolean((answers[question.id] || '').trim())),
    [answers, state.clarifyingQuestions],
  );

  const handleAnswerSubmit = async (e) => {
    e.preventDefault();
    if (!state.sessionId || !state.clarifyingQuestions.length) return;

    const summary = state.clarifyingQuestions
      .map((question, index) => {
        const answer = (answers[question.id] || '').trim() || 'No answer provided';
        return `Q${index + 1}: ${question.question}\nA${index + 1}: ${answer}`;
      })
      .join('\n\n');

    try {
      setLoading(true);
      setError(null);

      const result = await confirmAnswers(state.sessionId, summary);
      setMermaid(result.mermaid_diagram);
      if (result.updated_schema) {
        setSchema(result.updated_schema);
      }

      addToChat({ role: 'user', content: summary });
      addToChat({ role: 'assistant', content: 'Generated the Chen ER diagram from the clarified requirements.' });
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!state.clarifyingQuestions.length) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-6 text-slate-600 shadow-sm">
        No clarifying questions yet.
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/85 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.10)] backdrop-blur">
      <div className="mb-5">
        <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Clarify the schema</h2>
        <p className="mt-2 text-sm text-slate-600">
          These questions are targeted to resolve ambiguity before we generate the Chen ER diagram.
        </p>
      </div>

      <form onSubmit={handleAnswerSubmit} className="space-y-4">
        <div className="space-y-4">
          {state.clarifyingQuestions.map((question, index) => (
            <div key={question.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {index + 1}
                </div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">{question.focus}</p>
                  <p className="mt-1 text-base font-medium text-slate-900">{question.question}</p>
                </div>
              </div>

              <textarea
                value={answers[question.id] || ''}
                onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
                placeholder={question.example_answer || 'Type your answer here'}
                className="mt-4 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15"
                rows={3}
                disabled={state.loading}
              />
            </div>
          ))}
        </div>

        {state.error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
            {state.error}
          </div>
        )}

        <button
          type="submit"
          disabled={!allAnswered || state.loading}
          className="inline-flex w-full items-center justify-center rounded-2xl bg-emerald-600 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {state.loading ? 'Building Chen ER diagram...' : 'Generate Chen ER diagram'}
        </button>
      </form>
    </div>
  );
}
