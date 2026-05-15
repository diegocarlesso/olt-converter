import { useStore } from '../store';

const LEVEL_COLORS = {
  info: 'pill-blue',
  success: 'pill-green',
  warning: 'pill-yellow',
  error: 'pill-red',
};

export default function LogsDrawer({ open, onClose }) {
  const { logs, clearLogs } = useStore();
  if (!open) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-[28rem] bg-bg-panel border-l border-bg-border shadow-2xl flex flex-col">
      <header className="panel-header">
        <span>📜 Logs ({logs.length})</span>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={clearLogs}>
            Limpar
          </button>
          <button className="btn-ghost" onClick={onClose}>
            ✕
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-auto p-3 space-y-2 text-xs">
        {logs.length === 0 && <div className="text-slate-500 text-center py-10">Sem logs ainda.</div>}
        {logs.map((l) => (
          <div key={l.id} className="bg-bg-elevated rounded p-2">
            <div className="flex gap-2 items-center mb-1">
              <span className={LEVEL_COLORS[l.level] || 'pill-blue'}>{l.level}</span>
              <span className="text-slate-500">{new Date(l.at).toLocaleTimeString()}</span>
            </div>
            <div className="text-slate-300 break-words">{l.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
