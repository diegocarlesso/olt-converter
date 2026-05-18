import { useMemo, useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Editor, DiffEditor } from '@monaco-editor/react';
import { useStore } from '../store';
import { renderTarget, listVendors } from '../api';

export default function CliPreview() {
  const sessionId = useStore((s) => s.sessionId);
  const targetVendor = useStore((s) => s.targetVendor);
  const setTargetVendor = useStore((s) => s.setTargetVendor);
  const previewMode = useStore((s) => s.previewMode);
  const setPreviewMode = useStore((s) => s.setPreviewMode);
  const prevRenderRef = useRef('');

  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: listVendors });

  const { data, isFetching } = useQuery({
    queryKey: ['render', sessionId, targetVendor],
    queryFn: () => renderTarget(sessionId, targetVendor),
    enabled: !!sessionId,
  });

  // Save previous render for diff mode
  useEffect(() => {
    if (data?.rendered && data.rendered !== prevRenderRef.current && previewMode === 'cli') {
      prevRenderRef.current = data.rendered;
    }
  }, [data, previewMode]);

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-bg-border px-3 py-2 flex items-center gap-2 text-xs">
        <span className="text-[10px] uppercase tracking-wider text-slate-500">CLI Preview</span>
        <select
          value={targetVendor}
          onChange={(e) => setTargetVendor(e.target.value)}
          className="bg-bg-elevated border border-bg-border rounded px-2 py-0.5 text-slate-300 font-mono"
        >
          {(vendors || []).filter((v) => v.has_renderer).map((v) => (
            <option key={v.vendor} value={v.vendor}>{v.vendor}</option>
          ))}
        </select>

        <div className="flex border border-bg-border rounded overflow-hidden">
          <button
            onClick={() => setPreviewMode('cli')}
            className={`px-2 py-0.5 ${previewMode === 'cli' ? 'bg-bg-elevated text-slate-200' : 'text-slate-500'}`}
          >CLI</button>
          <button
            onClick={() => setPreviewMode('diff')}
            className={`px-2 py-0.5 ${previewMode === 'diff' ? 'bg-bg-elevated text-slate-200' : 'text-slate-500'}`}
          >Diff</button>
        </div>

        {isFetching && <span className="text-slate-500 font-mono text-[10px]">rendering…</span>}
        {data?.cached && <span className="text-slate-500 font-mono text-[10px]">cached</span>}
        <span className="ml-auto text-slate-500 font-mono text-[10px]">{data?.rendered?.length ?? 0} chars</span>
      </div>

      <div className="flex-1 min-h-0">
        {previewMode === 'cli' ? (
          <Editor
            theme="vs-dark"
            language="ini"
            value={data?.rendered || ''}
            options={{
              readOnly: true, fontSize: 12, lineNumbers: 'on',
              minimap: { enabled: true }, scrollBeyondLastLine: false,
              wordWrap: 'off', renderLineHighlight: 'none',
              fontFamily: 'JetBrains Mono, Menlo, monospace',
            }}
          />
        ) : (
          <DiffEditor
            theme="vs-dark"
            language="ini"
            original={prevRenderRef.current}
            modified={data?.rendered || ''}
            options={{
              readOnly: true, fontSize: 12, renderSideBySide: true,
              minimap: { enabled: false }, fontFamily: 'JetBrains Mono, Menlo, monospace',
            }}
          />
        )}
      </div>
    </div>
  );
}
