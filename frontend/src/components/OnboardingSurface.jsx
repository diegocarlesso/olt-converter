import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { useStore } from '../store';
import { createSession, listVendors } from '../api';

export default function OnboardingSurface() {
  const setSessionId = useStore((s) => s.setSessionId);
  const recentSessions = useStore((s) => s.recentSessions);
  const pushRecent = useStore((s) => s.pushRecent);
  const [pasted, setPasted] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: listVendors });

  const mut = useMutation({
    mutationFn: ({ text }) => createSession(text),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      pushRecent({
        session_id: data.session_id,
        vendor: data.source_vendor,
        hostname: data.hostname,
        onus: data.stats?.onus ?? 0,
        ts: Date.now(),
      });
      toast.success(`session ${data.session_id} • ${data.source_vendor} • ${data.stats?.onus ?? 0} ONUs`);
    },
    onError: (e) => toast.error(`session failed: ${e?.response?.data?.detail || e.message}`),
  });

  const onFile = useCallback(async (file) => {
    const text = await file.text();
    mut.mutate({ text });
  }, [mut]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  }, [onFile]);

  return (
    <div className="h-full grid grid-cols-12 gap-px bg-bg-border text-sm">
      {/* esquerda — vendors + engine */}
      <aside className="col-span-3 bg-bg-panel p-4 overflow-y-auto">
        <h3 className="text-xs uppercase tracking-wider text-slate-500 mb-2">vendors</h3>
        <div className="space-y-1.5 font-mono text-xs">
          {(vendors || []).map((v) => (
            <div key={v.vendor} className="flex items-center justify-between border border-bg-border rounded px-2 py-1.5">
              <span className="text-slate-200">{v.vendor}</span>
              <span className="flex gap-1 text-slate-400">
                <span className={v.has_parser ? 'text-accent-green' : 'text-slate-600'}>P</span>
                <span className={v.has_renderer ? 'text-accent-green' : 'text-slate-600'}>R</span>
              </span>
            </div>
          ))}
        </div>

        <h3 className="text-xs uppercase tracking-wider text-slate-500 mt-6 mb-2">engine</h3>
        <ul className="text-xs font-mono text-slate-400 space-y-1">
          <li>semantic runtime <span className="text-accent-green">frozen</span></li>
          <li>L9 promotion <span className="text-accent-green">enabled</span></li>
          <li>provenance graph <span className="text-accent-green">active</span></li>
          <li>cross-binding integrity <span className="text-accent-green">100%</span></li>
        </ul>
      </aside>

      {/* centro — semantic onboarding surface */}
      <section className="col-span-6 bg-bg-panel flex flex-col">
        <div className="p-6 border-b border-bg-border">
          <h2 className="text-lg font-semibold text-slate-100">No active session</h2>
          <p className="text-xs text-slate-500 mt-1 font-mono">
            Load a backup to materialize the OLTConfig in a backend session runtime.
            The workstation operates on projections — the full model never leaves the server.
          </p>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={
            'flex-1 m-6 border-2 border-dashed rounded-lg flex flex-col items-center justify-center text-center transition ' +
            (dragOver ? 'border-brand bg-bg-elevated' : 'border-bg-border')
          }
        >
          {mut.isPending ? (
            <div className="text-slate-400 font-mono">parsing • inferring • synthesizing • promoting…</div>
          ) : (
            <>
              <div className="text-slate-300 font-medium">drop .txt backup here</div>
              <div className="text-slate-500 text-xs mt-1">or use the picker below</div>
              <input
                type="file"
                accept=".txt,.cfg"
                onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
                className="mt-4 text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-brand-dark file:text-slate-100 hover:file:bg-brand"
              />

              <div className="mt-6 w-3/4 max-w-md text-left">
                <div className="text-xs uppercase tracking-wider text-slate-500 mb-1">or paste CLI</div>
                <textarea
                  value={pasted}
                  onChange={(e) => setPasted(e.target.value)}
                  placeholder="paste a fragment to detect vendor + create session"
                  className="w-full h-24 bg-bg-elevated border border-bg-border rounded p-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-brand"
                />
                <button
                  disabled={!pasted.trim() || mut.isPending}
                  onClick={() => mut.mutate({ text: pasted })}
                  className="mt-2 px-3 py-1.5 text-xs bg-brand-dark hover:bg-brand text-slate-100 rounded disabled:opacity-40"
                >
                  create session
                </button>
              </div>
            </>
          )}
        </div>
      </section>

      {/* direita — recent sessions */}
      <aside className="col-span-3 bg-bg-panel p-4 overflow-y-auto">
        <h3 className="text-xs uppercase tracking-wider text-slate-500 mb-2">recent</h3>
        {recentSessions.length === 0 ? (
          <div className="text-xs text-slate-600 font-mono">no recent sessions</div>
        ) : (
          <div className="space-y-1.5 font-mono text-xs">
            {recentSessions.map((r) => (
              <button
                key={r.session_id}
                onClick={() => setSessionId(r.session_id)}
                className="block w-full text-left border border-bg-border rounded px-2 py-1.5 hover:border-brand"
              >
                <div className="text-slate-200">{r.hostname || r.session_id}</div>
                <div className="text-slate-500">{r.vendor} • {r.onus} ONUs</div>
              </button>
            ))}
          </div>
        )}

        <h3 className="text-xs uppercase tracking-wider text-slate-500 mt-6 mb-2">shortcuts</h3>
        <ul className="text-xs font-mono text-slate-500 space-y-1">
          <li><kbd className="text-slate-400">⌘K</kbd> command palette (soon)</li>
          <li><kbd className="text-slate-400">⌘Z</kbd> undo (in session)</li>
          <li><kbd className="text-slate-400">⌘⇧Z</kbd> redo (in session)</li>
        </ul>
      </aside>
    </div>
  );
}
