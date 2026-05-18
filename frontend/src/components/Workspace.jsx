import RuntimeExplorer from './RuntimeExplorer.jsx';
import EntityInspector from './EntityInspector.jsx';
import CliPreview from './CliPreview.jsx';
import ValidationPanel from './ValidationPanel.jsx';

export default function Workspace() {
  return (
    <div className="h-full grid grid-cols-12 gap-px bg-bg-border">
      <aside className="col-span-3 bg-bg-panel flex flex-col overflow-hidden">
        <RuntimeExplorer />
      </aside>
      <main className="col-span-5 bg-bg-panel flex flex-col overflow-hidden">
        <EntityInspector />
        <ValidationPanel />
      </main>
      <aside className="col-span-4 bg-bg-panel flex flex-col overflow-hidden">
        <CliPreview />
      </aside>
    </div>
  );
}
