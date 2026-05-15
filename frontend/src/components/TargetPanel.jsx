import Editor from '@monaco-editor/react';
import toast from 'react-hot-toast';
import { useStore } from '../store';

export default function TargetPanel() {
  const { renderedConfig, targetVendor, parsedConfig } = useStore();

  const handleDownload = () => {
    if (!renderedConfig) return;
    const hostname = parsedConfig?.hostname || 'olt';
    const blob = new Blob([renderedConfig], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${hostname}-${targetVendor}.cfg`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Download iniciado.');
  };

  const handleCopy = async () => {
    if (!renderedConfig) return;
    await navigator.clipboard.writeText(renderedConfig);
    toast.success('Copiado para a área de transferência.');
  };

  return (
    <section className="panel flex-1 min-w-0">
      <header className="panel-header">
        <div className="flex items-center gap-2">
          <span>📤 Configuração convertida</span>
          <span className="pill-green uppercase">{targetVendor}</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost" onClick={handleCopy} disabled={!renderedConfig}>
            Copiar
          </button>
          <button className="btn-primary" onClick={handleDownload} disabled={!renderedConfig}>
            💾 Download
          </button>
        </div>
      </header>
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="ini"
          value={renderedConfig}
          theme="vs-dark"
          options={{
            readOnly: true,
            fontFamily: 'JetBrains Mono, Menlo, monospace',
            fontSize: 12,
            minimap: { enabled: false },
            wordWrap: 'off',
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
          }}
        />
      </div>
    </section>
  );
}
