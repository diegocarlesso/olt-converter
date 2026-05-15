import { useState } from 'react';
import { useStore } from '../store';

function Collapsible({ title, count, children, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="border-b border-bg-border">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-4 py-2 flex justify-between items-center hover:bg-bg-elevated text-sm"
      >
        <span className="flex items-center gap-2">
          <span>{open ? '▼' : '▶'}</span>
          <span className="font-medium">{title}</span>
        </span>
        <span className="pill-blue">{count}</span>
      </button>
      {open && <div className="px-4 py-2 text-xs space-y-1">{children}</div>}
    </div>
  );
}

function Row({ children }) {
  return <div className="font-mono text-slate-300 truncate">{children}</div>;
}

export default function StructurePanel() {
  const { parsedConfig, validation, warnings, unparsedLines } = useStore();

  if (!parsedConfig) {
    return (
      <section className="panel w-[28rem]">
        <header className="panel-header">🧬 Estrutura interna</header>
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm p-6 text-center">
          Faça <strong className="text-slate-300">Upload</strong> e clique em{' '}
          <strong className="text-slate-300">Parse</strong> para visualizar a estrutura.
        </div>
      </section>
    );
  }

  const cfg = parsedConfig;
  return (
    <section className="panel w-[28rem]">
      <header className="panel-header">
        <span>🧬 {cfg.hostname}</span>
        <span className="pill-green uppercase">{cfg.vendor}</span>
      </header>

      <div className="flex-1 overflow-auto">
        {validation && (
          <div className="px-4 py-3 border-b border-bg-border bg-bg-elevated text-xs">
            <div className="flex gap-2">
              <span className={validation.ok ? 'pill-green' : 'pill-red'}>
                {validation.ok ? 'OK' : 'ERROS'}
              </span>
              <span className="pill-red">err {validation.summary.error}</span>
              <span className="pill-yellow">warn {validation.summary.warning}</span>
              <span className="pill-blue">info {validation.summary.info}</span>
            </div>
            {validation.issues?.slice(0, 6).map((i, idx) => (
              <div key={idx} className="mt-1 text-[11px] text-slate-400 truncate">
                <span className="uppercase">{i.severity}</span> · {i.code} · {i.message}
              </div>
            ))}
          </div>
        )}

        <Collapsible title="VLANs" count={cfg.vlans?.length || 0} defaultOpen>
          {(cfg.vlans || []).slice(0, 50).map((v, i) => (
            <Row key={i}>
              vlan {v.id} {v.name && <span className="text-slate-500">— {v.name}</span>}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="Uplinks" count={cfg.uplinks?.length || 0}>
          {(cfg.uplinks || []).slice(0, 50).map((u, i) => (
            <Row key={i}>
              {u.interface} {u.description && <span className="text-slate-500">— {u.description}</span>}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="PONs" count={cfg.pons?.length || 0}>
          {(cfg.pons || []).slice(0, 50).map((p, i) => (
            <Row key={i}>
              {p.interface} <span className="text-slate-500">(onus: {p.onus?.length || 0})</span>
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="ONUs" count={cfg.onus?.length || 0}>
          {(cfg.onus || []).slice(0, 50).map((o, i) => (
            <Row key={i}>
              {o.pon_interface}:{o.onu_id} {o.serial_number}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="service-port" count={cfg.service_ports?.length || 0}>
          {(cfg.service_ports || []).slice(0, 50).map((s, i) => (
            <Row key={i}>
              #{s.service_port_id} vlan {s.match_vlan} → {s.target_vlan} on {s.pon_interface}:{s.onu_id}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="DBA profiles" count={cfg.dba_profiles?.length || 0}>
          {(cfg.dba_profiles || []).slice(0, 30).map((d, i) => (
            <Row key={i}>
              id {d.profile_id} · {d.name} · {d.type}{' '}
              {d.max_bandwidth && <span className="text-slate-500">max {d.max_bandwidth}</span>}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="Service profiles" count={cfg.service_profiles?.length || 0}>
          {(cfg.service_profiles || []).slice(0, 30).map((p, i) => (
            <Row key={i}>
              id {p.profile_id} · {p.name}
            </Row>
          ))}
        </Collapsible>

        <Collapsible title="Linhas não-parseadas" count={unparsedLines?.length || 0}>
          {(unparsedLines || []).slice(0, 30).map((l, i) => (
            <Row key={i}>
              <span className="text-rose-300">{l}</span>
            </Row>
          ))}
        </Collapsible>
      </div>
    </section>
  );
}
