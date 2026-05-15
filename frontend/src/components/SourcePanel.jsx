import Editor from '@monaco-editor/react';
import { useStore } from '../store';

export default function SourcePanel() {
  const { sourceText, setSourceText, sourceVendor } = useStore();

  return (
    <section className="panel flex-1 min-w-0">
      <header className="panel-header">
        <div className="flex items-center gap-2">
          <span>📥 Configuração de origem</span>
          {sourceVendor && <span className="pill-yellow uppercase">{sourceVendor}</span>}
        </div>
        <span className="text-xs text-slate-500">{sourceText.length} chars</span>
      </header>
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="ini"
          value={sourceText}
          onChange={(v) => setSourceText(v || '')}
          theme="vs-dark"
          options={{
            fontFamily: 'JetBrains Mono, Menlo, monospace',
            fontSize: 12,
            minimap: { enabled: false },
            wordWrap: 'off',
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            lineNumbers: 'on',
          }}
        />
      </div>
    </section>
  );
}
