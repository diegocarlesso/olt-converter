import { useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useStore } from '../store';
import { getProjection } from '../api';
import clsx from 'clsx';

/**
 * Provenance source -> color + short label
 */
const SRC_BADGE = {
  parser: { c: 'text-slate-400 border-slate-700', l: 'P' },
  inference: { c: 'text-yellow-300 border-yellow-700', l: 'I' },
  synthesis: { c: 'text-cyan-300 border-cyan-700', l: 'S' },
  promotion: { c: 'text-violet-300 border-violet-700', l: 'L9' },
  manual: { c: 'text-pink-300 border-pink-700', l: 'M' },
  default: { c: 'text-red-300 border-red-700', l: 'D' },
  import: { c: 'text-slate-400 border-slate-700', l: 'IM' },
};

function ProvBadge({ p }) {
  if (!p) return null;
  const s = SRC_BADGE[p.source] || SRC_BADGE.parser;
  const conf = Math.round((p.confidence ?? 1) * 100);
  return (
    <span
      className={clsx(
        'text-[9px] font-mono px-1 py-px border rounded',
        s.c,
        p.needs_review && 'ring-1 ring-amber-500/50',
      )}
      title={`source=${p.source} confidence=${conf}%${p.needs_review ? ' • needs review' : ''}`}
    >
      {s.l}{conf < 100 ? `·${conf}` : ''}
    </span>
  );
}

/**
 * Flatten the projection tree into a single linear list of rows so the
 * virtualizer can render only viewport-visible entries.
 */
function flattenProjection(proj, expandedGroups, expandedPons, filter, filterSource, filterNeedsReview) {
  if (!proj) return [];
  const rows = [];
  const f = filter.trim().toLowerCase();
  const matches = (e) => {
    if (filterSource !== 'all' && e?.provenance?.source !== filterSource) return false;
    if (filterNeedsReview && !e?.provenance?.needs_review) return false;
    if (!f) return true;
    return JSON.stringify(e).toLowerCase().includes(f);
  };

  for (const group of proj.tree || []) {
    rows.push({ kind: 'group', key: group.key, label: group.label, count: group.count, depth: 0 });
    if (!expandedGroups[group.key]) continue;

    if (group.key === 'pons') {
      for (const pon of group.children) {
        rows.push({ kind: 'pon', depth: 1, ...pon, expanded: !!expandedPons[pon.id] });
        if (!expandedPons[pon.id]) continue;
        for (const onu of pon.children) {
          if (matches(onu)) rows.push({ kind: 'entity', depth: 2, ...onu });
        }
      }
    } else {
      for (const e of group.children) {
        if (matches(e)) rows.push({ kind: 'entity', depth: 1, ...e });
      }
    }
  }
  return rows;
}

function CountsLine({ counts }) {
  if (!counts) return null;
  const parts = [
    ['eth', counts.eth], ['wan', counts.wan], ['ssid', counts.ssid],
    ['radio', counts.radio], ['bg', counts.bg], ['pr', counts.pr],
  ].filter(([, n]) => n > 0);
  if (parts.length === 0) return null;
  return (
    <span className="text-[10px] text-slate-500 font-mono ml-2">
      {parts.map(([k, n]) => `${k}=${n}`).join(' ')}
    </span>
  );
}

export default function RuntimeExplorer() {
  const sessionId = useStore((s) => s.sessionId);
  const expandedGroups = useStore((s) => s.expandedGroups);
  const toggleGroup = useStore((s) => s.toggleGroup);
  const expandedPons = useStore((s) => s.expandedPons);
  const togglePon = useStore((s) => s.togglePon);
  const selection = useStore((s) => s.selection);
  const setSelection = useStore((s) => s.setSelection);
  const filter = useStore((s) => s.filter);
  const setFilter = useStore((s) => s.setFilter);
  const filterSource = useStore((s) => s.filterSource);
  const setFilterSource = useStore((s) => s.setFilterSource);
  const filterNeedsReview = useStore((s) => s.filterNeedsReview);
  const setFilterNeedsReview = useStore((s) => s.setFilterNeedsReview);

  const { data: proj } = useQuery({
    queryKey: ['projection', sessionId],
    queryFn: () => getProjection(sessionId),
    enabled: !!sessionId,
  });

  const rows = useMemo(
    () => flattenProjection(proj, expandedGroups, expandedPons, filter, filterSource, filterNeedsReview),
    [proj, expandedGroups, expandedPons, filter, filterSource, filterNeedsReview],
  );

  const parentRef = useRef(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 24,
    overscan: 16,
  });

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-bg-border px-3 py-2">
        <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Runtime Explorer</div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="filter entities…"
          className="w-full bg-bg-elevated border border-bg-border rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-brand font-mono"
        />
        <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500 font-mono">
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="bg-bg-elevated border border-bg-border rounded px-1 py-0.5 text-slate-300"
          >
            <option value="all">all sources</option>
            <option value="parser">parser</option>
            <option value="inference">inference</option>
            <option value="synthesis">synthesis</option>
            <option value="promotion">promotion</option>
            <option value="manual">manual</option>
            <option value="default">default</option>
          </select>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={filterNeedsReview} onChange={(e) => setFilterNeedsReview(e.target.checked)} />
            needs review
          </label>
          <span className="ml-auto">{rows.length} rows</span>
        </div>
      </div>

      <div ref={parentRef} className="flex-1 overflow-auto font-mono text-xs">
        <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
          {virtualizer.getVirtualItems().map((vr) => {
            const r = rows[vr.index];
            const isSel = selection && r.id === selection.entity_id && r.type === selection.entity_type;
            return (
              <div
                key={vr.key}
                style={{
                  position: 'absolute', top: 0, left: 0, right: 0,
                  height: vr.size, transform: `translateY(${vr.start}px)`,
                }}
                className={clsx(
                  'flex items-center px-2 cursor-pointer border-l-2',
                  isSel ? 'bg-bg-elevated border-brand text-slate-100' : 'border-transparent hover:bg-bg-elevated/60 text-slate-300',
                )}
                onClick={() => {
                  if (r.kind === 'group') toggleGroup(r.key);
                  else if (r.kind === 'pon') togglePon(r.id);
                  else if (r.kind === 'entity') setSelection({ entity_type: r.type, entity_id: r.id });
                }}
              >
                <span style={{ paddingLeft: r.depth * 12 }} />
                {r.kind === 'group' && (
                  <>
                    <span className="text-slate-500 mr-1">{expandedGroups[r.key] ? '▾' : '▸'}</span>
                    <span className="font-semibold text-slate-200 uppercase tracking-wider text-[10px]">{r.label}</span>
                    <span className="ml-auto text-slate-500">{r.count}</span>
                  </>
                )}
                {r.kind === 'pon' && (
                  <>
                    <span className="text-slate-500 mr-1">{expandedPons[r.id] ? '▾' : '▸'}</span>
                    <span className="text-cyan-300">{r.label}</span>
                    <span className="ml-2 text-slate-500">{r.count} ONUs</span>
                  </>
                )}
                {r.kind === 'entity' && (
                  <>
                    <span className="text-[10px] text-slate-600 mr-1.5 w-8 inline-block truncate">{r.type}</span>
                    <span className="text-slate-200 truncate flex-1">{r.label}</span>
                    {r.subtitle && (
                      <span className="ml-1 text-slate-500 truncate flex-shrink min-w-0">{r.subtitle}</span>
                    )}
                    <CountsLine counts={r.counts} />
                    <span className="ml-2"><ProvBadge p={r.provenance} /></span>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
