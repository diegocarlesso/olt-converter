import { DiffEditor } from '@monaco-editor/react';
import { useStore } from '../store';

export default function DiffDrawer({ open, onClose }) {
  const { sourceText, renderedConfig, sourceVendor, targetVendor } = useStore();
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-bg/80 backdrop-blur flex items-center justify-center p-6">
      <div className="bg-bg-panel border border-bg-border rounded-lg w-full max-w-7xl h-[85vh] flex flex-col">
        <header className="panel-header">
          <span>
            🆚 Diff —{' '}
            <span className="pill-yellow uppercase">{sourceVendor || 'origem'}</span> →{' '}
            <span className="pill-green uppercase">{targetVendor}</span>
          </span>
          <button className="btn-ghost" onClick={onClose}>
            ✕ Fechar
          </button>
        </header>
        <div className="flex-1">
          <DiffEditor
            height="100%"
            language="ini"
            theme="vs-dark"
            original={sourceText}
            modified={renderedConfig}
            options={{
              renderSideBySide: true,
              fontFamily: 'JetBrains Mono, Menlo, monospace',
              fontSize: 12,
              minimap: { enabled: false },
              readOnly: true,
            }}
          />
        </div>
      </div>
    </div>
  );
}
