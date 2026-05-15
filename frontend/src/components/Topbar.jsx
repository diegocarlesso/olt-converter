import { useRef } from 'react';
import { useStore } from '../store';

const VENDORS = ['fiberhome', 'zte', 'huawei', 'datacom'];

export default function Topbar({ onUpload, onParse, onConvert, onOpenDiff, onOpenLogs }) {
  const fileRef = useRef(null);
  const { sourceVendor, targetVendor, setTargetVendor, loading, stats } = useStore();

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-bg-border bg-bg-elevated">
      <div className="flex items-center gap-3">
        <div className="text-brand font-bold text-lg tracking-tight">
          OLT <span className="text-slate-200">Config Converter</span>
        </div>
        <span className="pill-blue">v0.1</span>
      </div>

      <div className="flex items-center gap-2">
        <input
          ref={fileRef}
          type="file"
          accept=".cfg,.txt,.conf,.log"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) onUpload(e.target.files[0]);
            e.target.value = '';
          }}
        />
        <button className="btn-ghost" onClick={() => fileRef.current?.click()} disabled={loading}>
          📂 Upload
        </button>

        <span className="text-xs text-slate-500">Origem:</span>
        <span className="pill-yellow uppercase">{sourceVendor || 'auto'}</span>

        <span className="text-xs text-slate-500 ml-2">Destino:</span>
        <select
          value={targetVendor}
          onChange={(e) => setTargetVendor(e.target.value)}
          className="bg-bg-panel border border-bg-border rounded-md text-sm py-1 px-2"
        >
          {VENDORS.map((v) => (
            <option key={v} value={v}>
              {v.toUpperCase()}
            </option>
          ))}
        </select>

        <button className="btn-ghost" onClick={onParse} disabled={loading}>
          🔍 Parse
        </button>
        <button className="btn-primary" onClick={onConvert} disabled={loading}>
          ⚙️ Converter
        </button>
        <button className="btn-ghost" onClick={onOpenDiff} disabled={loading}>
          🆚 Diff
        </button>
        <button className="btn-ghost" onClick={onOpenLogs}>
          📜 Logs
        </button>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-500">
        {Object.entries(stats).map(([k, v]) => (
          <span key={k} className="pill-blue">
            {k}: {v}
          </span>
        ))}
      </div>
    </header>
  );
}
