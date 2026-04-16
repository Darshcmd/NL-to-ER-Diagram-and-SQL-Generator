import React, { useEffect, useMemo, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  securityLevel: 'loose',
  themeVariables: {
    fontFamily: 'Inter, system-ui, sans-serif',
    primaryColor: '#ecfeff',
    primaryTextColor: '#0f172a',
    primaryBorderColor: '#0f766e',
    lineColor: '#0f766e',
    secondaryColor: '#f8fafc',
    tertiaryColor: '#f8fafc',
  },
});

export function MermaidDiagram({ diagramCode }) {
  const [svgMarkup, setSvgMarkup] = useState('');
  const [error, setError] = useState(null);
  const renderId = useMemo(() => `mermaid-${Math.random().toString(36).slice(2, 10)}`, []);

  useEffect(() => {
    if (!diagramCode) {
      setSvgMarkup('');
      setError(null);
      return;
    }

    const renderDiagram = async () => {
      try {
        setError(null);
        const { svg } = await mermaid.render(renderId, diagramCode);
        setSvgMarkup(svg);
      } catch (err) {
        console.error('Mermaid rendering error:', err);
        setError(err.message);
        setSvgMarkup('');
      }
    };

    renderDiagram();
  }, [diagramCode, renderId]);

  const downloadSvg = () => {
    if (!svgMarkup) return;

    const blob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'schemaflow_diagram.svg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadPng = () => {
    if (!svgMarkup) return;

    const svgBlob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const image = new Image();
    image.onload = function () {
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const pngUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = 'schemaflow_diagram.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(pngUrl);
      });
    };
    image.src = url;
  };

  if (!diagramCode) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-8 text-center text-slate-500 shadow-sm">
        No diagram generated yet.
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Chen ER Diagram</h2>
        </div>
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
          <p className="font-semibold">Error rendering diagram</p>
          <pre className="mt-2 whitespace-pre-wrap text-sm">{error}</pre>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/90 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.10)] backdrop-blur">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-950">Chen ER Diagram</h2>
          <p className="mt-1 text-sm text-slate-600">
            Chen-style Mermaid output rendered from the clarified requirements.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={downloadSvg} className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700">
            Export SVG
          </button>
          <button onClick={downloadPng} className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500">
            Export PNG
          </button>
        </div>
      </div>

      <div className="overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4" dangerouslySetInnerHTML={{ __html: svgMarkup }} />
    </div>
  );
}
