import React, { useMemo } from 'react';
import { useSchema } from '../hooks/useSchema';

function getDerivedIssues(schema) {
  const issues = [];

  if (!schema) {
    return issues;
  }

  const entities = schema.entities || [];
  const relationships = schema.relationships || [];
  const nameSet = new Set(entities.map((entity) => entity.name));

  entities.forEach((entity) => {
    const hasPrimaryKey = entity.attributes?.some((attribute) => attribute.pk);
    if (!hasPrimaryKey) {
      issues.push(`Entity ${entity.label || entity.name} has no primary key.`);
    }
  });

  relationships.forEach((relationship) => {
    if (relationship.cardinality === 'M:N') {
      const bridge = relationship.bridge_entity;
      if (!bridge) {
        issues.push(`Many-to-many relation ${relationship.from_entity} to ${relationship.to_entity} should use a bridge table.`);
      } else if (!nameSet.has(bridge)) {
        issues.push(`Bridge entity ${bridge} is referenced but missing from the schema.`);
      }
    }
  });

  if (schema.domain === 'generic' && entities.length <= 3) {
    issues.push('Input signal was weak, so the schema used a generic fallback structure.');
  }

  if (relationships.length === 0) {
    issues.push('No relationships were inferred. Add more context or answer the clarification questions in more detail.');
  }

  return issues;
}

export function ValidationPanel() {
  const { state } = useSchema();

  const findings = useMemo(() => getDerivedIssues(state.currentSchema), [state.currentSchema]);
  const notes = state.currentSchema?.validation_notes || [];

  if (!state.currentSchema) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-6 text-sm text-slate-500 shadow-sm">
        Validation will appear here after the schema is generated.
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/85 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">Validation</h3>
          <p className="mt-1 text-sm text-slate-600">Normalization and structural checks for the generated schema.</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">
          {findings.length + notes.length} checks
        </span>
      </div>

      <div className="mt-4 space-y-4">
        {notes.length > 0 && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <div className="text-sm font-semibold text-emerald-900">Validation notes from the generator</div>
            <ul className="mt-2 space-y-1 text-sm text-emerald-900">
              {notes.map((note, index) => (
                <li key={index}>• {note}</li>
              ))}
            </ul>
          </div>
        )}

        {findings.length > 0 ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
            <div className="text-sm font-semibold text-amber-900">Findings</div>
            <ul className="mt-2 space-y-1 text-sm text-amber-900">
              {findings.map((finding, index) => (
                <li key={index}>• {finding}</li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            No structural issues detected.
          </div>
        )}
      </div>
    </div>
  );
}
