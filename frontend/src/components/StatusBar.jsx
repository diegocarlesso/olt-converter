import { useQuery } from '@tanstack/react-query';
import { useStore } from '../store';
import { listVendors, getProjection } from '../api';

export default function StatusBar() {
  const sessionId = useStore((s) => s.sessionId);
  const resetSession = useStore((s) => s.resetSession);

  const { data: vendors } = useQuery({
    queryKey: ['vendors'],
    queryFn: listVendors,
    staleTime: Infinity,
  });

  const { data: proj } = useQuery({
    queryKey: ['projection', sessionId],
    queryFn: () => getProjection(sessionId),
    enabled: !!sessionId,
  });

  const v = proj?.validation || {};
  const errors = v.error || 0;
  const warnings = v.warning || 0;

  return (
    <div className="h-9 border-b border-bg-border bg-bg-elevated flex items-center px-3 text-xs font-mono select-none">
      <div className="flex items-center gap-3">
        <span className="font-semibold text-brand-light">OLT • SEMANTIC WORKSTATION</span>
        <span className="text-slate-500">|</span>
        <span className="text-slate-400">
          engine: <span className="text-accent-green">ready</span>
        </span>
        <span className="text-slate-500">|</span>
        <span className="text-slate-400">
          parsers: <span className="text-slate-200">{vendors?.filter((v) => v.has_parser).length ?? '—'}</span>
          {' / '}
          renderers: <span className="text-slate-200">{vendors?.filter((v) => v.has_renderer).length ?? '—'}</span>
        </span>
      </div>
      {sessionId && proj && (
        <>
          <span className="mx-3 text-slate-500">|</span>
          <span className="text-slate-300">
            <span className="text-slate-500">session</span>{' '}
            <span className="text-brand-light">{sessionId}</span>
          </span>
          <span className="mx-3 text-slate-500">|</span>
          <span className="text-slate-300">
            <span className="text-slate-500">vendor</span>{' '}
            <span className="text-slate-200">{proj.source_vendor}</span>
          </span>
          <span className="mx-3 text-slate-500">|</span>
          <span className="text-slate-300">
            <span className="text-slate-500">hostname</span>{' '}
            <span className="text-slate-200">{proj.hostname || 'unnamed'}</span>
          </span>
          <span className="mx-3 text-slate-500">|</span>
          <span className="text-slate-300">
            <span className="text-slate-500">onus</span>{' '}
            <span className="text-slate-200">{proj.stats?.onus ?? 0}</span>
          </span>
          <span className="mx-3 text-slate-500">|</span>
          <span className={errors > 0 ? 'text-accent-red' : 'text-slate-400'}>
            {errors}e
          </span>
          {' / '}
          <span className={warnings > 0 ? 'text-accent-yellow' : 'text-slate-400'}>
            {warnings}w
          </span>
          {proj.dirty_entities?.length > 0 && (
            <>
              <span className="mx-3 text-slate-500">|</span>
              <span className="text-accent-yellow">
                dirty: {proj.dirty_entities.length}
              </span>
            </>
          )}
        </>
      )}
      <div className="flex-1" />
      {sessionId && (
        <button
          onClick={resetSession}
          className="text-slate-400 hover:text-slate-200 px-2 py-0.5 border border-bg-border rounded"
        >
          close session
        </button>
      )}
    </div>
  );
}
