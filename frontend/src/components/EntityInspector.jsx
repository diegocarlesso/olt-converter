import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { useStore } from '../store';
import { getEntity, patchEntity, undoSession, redoSession } from '../api';

const EDITABLE_TYPES_AND_FIELDS = {
  VLAN: ['name', 'description', 'is_management'],
  ONU: ['description', 'admin_state', 'native_vlan', 'user_vlan', 'wifi_enabled', 'voip_enabled', 'catv_enabled'],
  ServicePort: ['match_vlan', 'target_vlan', 'user_vlan'],
  Uplink: ['description', 'native_vlan'],
  DBAProfile: ['name', 'max_bandwidth', 'assured_bandwidth', 'fix_bandwidth'],
  TrafficProfile: ['name', 'cir', 'pir', 'cbs', 'pbs'],
};

function Field({ k, v, onChange, editable }) {
  const isNumber = typeof v === 'number';
  const isBool = typeof v === 'boolean';
  const [val, setVal] = useState(v);
  useEffect(() => setVal(v), [v]);

  if (!editable) {
    return (
      <div className="flex items-baseline border-b border-bg-border/50 py-1">
        <span className="w-44 text-slate-500 text-xs font-mono">{k}</span>
        <span className="text-slate-300 text-xs font-mono truncate">{JSON.stringify(v)}</span>
      </div>
    );
  }

  return (
    <div className="flex items-baseline border-b border-bg-border/50 py-1">
      <span className="w-44 text-slate-400 text-xs font-mono">{k}</span>
      {isBool ? (
        <input type="checkbox" checked={!!val} onChange={(e) => { setVal(e.target.checked); onChange(e.target.checked); }} />
      ) : (
        <input
          value={val ?? ''}
          onChange={(e) => setVal(isNumber ? Number(e.target.value) : e.target.value)}
          onBlur={() => onChange(val)}
          onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
          className="bg-bg-elevated border border-bg-border rounded px-2 py-0.5 text-xs font-mono text-slate-200 flex-1 focus:outline-none focus:border-brand"
        />
      )}
    </div>
  );
}

function ProvenancePanel({ data }) {
  const p = data?.provenance;
  if (!p) return null;
  return (
    <div className="border-t border-bg-border pt-2 mt-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Provenance</div>
      <div className="space-y-0.5 text-xs font-mono">
        <div><span className="text-slate-500">source:</span> <span className="text-slate-300">{p.source}</span></div>
        <div><span className="text-slate-500">confidence:</span> <span className="text-slate-300">{Math.round((p.confidence ?? 1) * 100)}%</span></div>
        {p.needs_review && <div className="text-amber-400">needs_review = true</div>}
        {p.reason && <div className="text-slate-400 mt-1">{p.reason}</div>}
        {Array.isArray(p.signals) && p.signals.length > 0 && (
          <ul className="text-slate-500 list-disc pl-4 mt-1 space-y-0.5">
            {p.signals.slice(0, 6).map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        )}
      </div>
    </div>
  );
}

function BindingsPanel({ bindings }) {
  if (!bindings || Object.keys(bindings).length === 0) return null;
  return (
    <div className="border-t border-bg-border pt-2 mt-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Cross-bindings</div>
      {Object.entries(bindings).map(([key, items]) => (
        <div key={key} className="mb-2">
          <div className="text-xs text-slate-400 font-mono">{key} <span className="text-slate-600">({items.length})</span></div>
          <div className="pl-3 space-y-0.5">
            {items.slice(0, 12).map((it, i) => (
              <div key={i} className="text-xs font-mono text-slate-500">→ <span className="text-slate-300">{it.label}</span></div>
            ))}
            {items.length > 12 && <div className="text-[10px] text-slate-600">…and {items.length - 12} more</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function EntityInspector() {
  const sessionId = useStore((s) => s.sessionId);
  const selection = useStore((s) => s.selection);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['entity', sessionId, selection?.entity_type, selection?.entity_id],
    queryFn: () => getEntity(sessionId, selection.entity_type, selection.entity_id),
    enabled: !!sessionId && !!selection,
  });

  const patchMut = useMutation({
    mutationFn: (patch) => patchEntity(sessionId, patch),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['entity', sessionId] });
      qc.invalidateQueries({ queryKey: ['projection', sessionId] });
      qc.invalidateQueries({ queryKey: ['render', sessionId] });
      qc.invalidateQueries({ queryKey: ['validation', sessionId] });
      toast.success(`${res.audit_entry?.entity_type}.${res.audit_entry?.field} applied`);
    },
    onError: (e) => toast.error(`patch failed: ${e?.response?.data?.detail || e.message}`),
  });

  const onUndo = async () => {
    const r = await undoSession(sessionId);
    if (r.ok) {
      toast(`undo: ${r.restored_label}`);
      qc.invalidateQueries({ queryKey: ['projection', sessionId] });
      qc.invalidateQueries({ queryKey: ['render', sessionId] });
      qc.invalidateQueries({ queryKey: ['validation', sessionId] });
      qc.invalidateQueries({ queryKey: ['entity', sessionId] });
    } else toast(r.error);
  };
  const onRedo = async () => {
    const r = await redoSession(sessionId);
    if (r.ok) {
      qc.invalidateQueries({ queryKey: ['projection', sessionId] });
      qc.invalidateQueries({ queryKey: ['render', sessionId] });
      qc.invalidateQueries({ queryKey: ['validation', sessionId] });
      qc.invalidateQueries({ queryKey: ['entity', sessionId] });
    } else toast(r.error);
  };

  if (!selection) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500 text-xs font-mono">
        select an entity in the Runtime Explorer
      </div>
    );
  }
  if (isLoading) {
    return <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">loading…</div>;
  }
  if (!data) {
    return <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">entity not found</div>;
  }

  const editableFields = EDITABLE_TYPES_AND_FIELDS[selection.entity_type] || [];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="border-b border-bg-border px-3 py-2 flex items-center">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Entity Inspector</div>
          <div className="text-sm font-mono text-slate-200">
            <span className="text-slate-500">{selection.entity_type}</span>{' '}
            <span>{selection.entity_id}</span>
            {data.dirty && <span className="ml-2 text-accent-yellow">●</span>}
          </div>
        </div>
        <div className="ml-auto flex gap-1">
          <button onClick={onUndo} className="text-xs px-2 py-1 border border-bg-border rounded hover:border-brand text-slate-400">undo</button>
          <button onClick={onRedo} className="text-xs px-2 py-1 border border-bg-border rounded hover:border-brand text-slate-400">redo</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <div className="grid grid-cols-1 gap-px">
          {Object.entries(data.data || {})
            .filter(([k]) => !['provenance', 'extra_vendor', 'tconts', 'gemports', 'eth_ports',
                                'radios', 'ssids', 'bridge_groups', 'lan_services',
                                'wan_bindings', 'multicast_bindings', 'port_routes', 'stb',
                                'onus'].includes(k))
            .map(([k, v]) => (
              <Field
                key={k}
                k={k}
                v={v}
                editable={editableFields.includes(k)}
                onChange={(newVal) => {
                  if (newVal === v) return;
                  patchMut.mutate({
                    op: 'update',
                    entity_type: selection.entity_type,
                    entity_id: selection.entity_id,
                    field: k,
                    value: newVal,
                  });
                }}
              />
            ))}
        </div>

        <BindingsPanel bindings={data.bindings} />
        <ProvenancePanel data={data.data} />

        {data.validation_issues?.length > 0 && (
          <div className="border-t border-bg-border pt-2 mt-2">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Validation</div>
            <ul className="text-xs font-mono space-y-1">
              {data.validation_issues.map((i, idx) => (
                <li key={idx} className={clsx('flex gap-2',
                  i.severity === 'error' ? 'text-accent-red' : i.severity === 'warning' ? 'text-accent-yellow' : 'text-slate-400')}>
                  <span className="text-[10px] uppercase w-12">{i.severity}</span>
                  <span className="flex-1">{i.message}</span>
                  <span className="text-slate-600">{i.code}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
