import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import clsx from 'clsx';
import { useStore } from '../store';
import { getValidation } from '../api';

export default function ValidationPanel() {
  const sessionId = useStore((s) => s.sessionId);
  const setSelection = useStore((s) => s.setSelection);
  const [collapsed, setCollapsed] = useState(false);
  const [severityFilter, setSeverityFilter] = useState('all');

  const { data } = useQuery({
    queryKey: ['validation', sessionId],
    queryFn: () => getValidation(sessionId),
    enabled: !!sessionId,
  });

  const summary = data?.summary || {};
  const issues = (data?.issues || []).filter(
    (i) => severityFilter === 'all' || i.severity === severityFilter,
  );

  return (
    <div className={clsx(
      'border-t border-bg-border bg-bg-panel flex flex-col',
      collapsed ? 'h-9' : 'h-64 flex-shrink-0',
    )}>
      <div className="h-9 px-3 flex items-center border-b border-bg-border text-xs font-mono">
        <span className="text-[10px] uppercase tracking-wider text-slate-500">Validation</span>
        <span className="ml-3 text-accent-red">{summary.error || 0}e</span>
        <span className="ml-2 text-accent-yellow">{summary.warning || 0}w</span>
        <span className="ml-2 text-slate-500">{summary.info || 0}i</span>
        <div className="ml-auto flex gap-2 items-center">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-bg-elevated border border-bg-border rounded px-1 py-0.5 text-[10px] text-slate-300"
          >
            <option value="all">all</option>
            <option value="error">errors</option>
            <option value="warning">warnings</option>
            <option value="info">info</option>
          </select>
          <button onClick={() => setCollapsed((v) => !v)} className="text-slate-500 hover:text-slate-300">
            {collapsed ? '▴' : '▾'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto font-mono text-xs">
          {issues.length === 0 ? (
            <div className="p-3 text-slate-500">no issues at this severity.</div>
          ) : (
            issues.slice(0, 500).map((i, idx) => (
              <div
                key={idx}
                onClick={() => {
                  // Try to derive entity from location: e.g. "ONU pon-1/1/3:12"
                  if (i.location) {
                    const m = i.location.match(/^(\w+)\s+(.+)$/);
                    if (m) setSelection({ entity_type: m[1], entity_id: m[2] });
                  }
                }}
                className={clsx(
                  'px-3 py-1 border-b border-bg-border/40 cursor-pointer hover:bg-bg-elevated/60 flex gap-2',
                  i.severity === 'error' ? 'text-accent-red' :
                  i.severity === 'warning' ? 'text-accent-yellow' : 'text-slate-400',
                )}
              >
                <span className="w-12 uppercase text-[10px] flex-shrink-0">{i.severity}</span>
                <span className="w-44 text-slate-500 flex-shrink-0 truncate">{i.code}</span>
                <span className="flex-1 truncate">{i.message}</span>
                {i.location && <span className="text-slate-600 ml-2 truncate max-w-[200px]">{i.location}</span>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
