import { useStore } from './store';
import StatusBar from './components/StatusBar.jsx';
import Workspace from './components/Workspace.jsx';
import OnboardingSurface from './components/OnboardingSurface.jsx';

export default function App() {
  const sessionId = useStore((s) => s.sessionId);

  return (
    <div className="h-full w-full flex flex-col bg-bg">
      <StatusBar />
      <div className="flex-1 overflow-hidden">
        {sessionId ? <Workspace /> : <OnboardingSurface />}
      </div>
    </div>
  );
}
