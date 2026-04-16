import React from 'react';
import { useSchema } from '../hooks/useSchema';

export function ChatHistory() {
  const { state } = useSchema();

  if (state.chatHistory.length === 0) {
    return null;
  }

  return (
    <div className="max-h-[34rem] overflow-y-auto rounded-3xl border border-white/10 bg-white/85 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <h3 className="text-lg font-semibold text-slate-950">Conversation</h3>

      <div className="mt-4 space-y-4">
        {state.chatHistory.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}
            >
              <p className="text-sm leading-6 whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
