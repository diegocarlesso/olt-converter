import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useStore } from './store';
import { listVendors, uploadConfig, convertConfig, parseConfig } from './api';
import Topbar from './components/Topbar.jsx';
import SourcePanel from './components/SourcePanel.jsx';
import StructurePanel from './components/StructurePanel.jsx';
import TargetPanel from './components/TargetPanel.jsx';
import DiffDrawer from './components/DiffDrawer.jsx';
import LogsDrawer from './components/LogsDrawer.jsx';

export default function App() {
  const {
    sourceText,
    sourceVendor,
    targetVendor,
    setVendors,
    setSourceText,
    setSourceVendor,
    setParsed,
    setRendered,
    setDiff,
    setValidation,
    setWarnings,
    setUnparsed,
    setStats,
    setLoading,
    appendLog,
  } = useStore();

  const [diffOpen, setDiffOpen] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);

  useEffect(() => {
    listVendors()
      .then((v) => setVendors(v))
      .catch((err) => {
        appendLog({ level: 'error', message: 'Falha ao buscar vendors: ' + err.message });
      });
  }, [setVendors, appendLog]);

  const handleUpload = async (file) => {
    setLoading(true);
    try {
      const data = await uploadConfig(file);
      setSourceText(data.content);
      setSourceVendor(data.vendor);
      appendLog({
        level: 'info',
        message: `Arquivo "${data.filename}" carregado (${data.size} bytes). Vendor detectado: ${data.vendor} (${Math.round(data.confidence * 100)}% confiança).`,
      });
      toast.success(`Vendor detectado: ${data.vendor.toUpperCase()}`);
    } catch (err) {
      appendLog({ level: 'error', message: err.message });
      toast.error('Falha no upload: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    if (!sourceText.trim()) {
      toast.error('Cole ou faça upload de uma configuração primeiro.');
      return;
    }
    setLoading(true);
    try {
      const data = await parseConfig(sourceText, sourceVendor || null);
      setParsed(data.config);
      setSourceVendor(data.detected_vendor);
      setStats(data.stats);
      setWarnings(data.warnings);
      setUnparsed(data.unparsed_lines);
      appendLog({
        level: 'info',
        message: `Parse OK – vendor=${data.detected_vendor}, hostname=${data.hostname}, vlans=${data.stats.vlans}, onus=${data.stats.onus}.`,
      });
      toast.success('Configuração parseada com sucesso.');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      appendLog({ level: 'error', message: 'Erro no parse: ' + detail });
      toast.error('Falha no parse: ' + detail);
    } finally {
      setLoading(false);
    }
  };

  const handleConvert = async () => {
    if (!sourceText.trim()) {
      toast.error('Cole ou faça upload de uma configuração primeiro.');
      return;
    }
    setLoading(true);
    try {
      const data = await convertConfig({
        config_text: sourceText,
        source_vendor: sourceVendor || null,
        target_vendor: targetVendor,
      });
      setRendered(data.rendered_config);
      setDiff(data.diff);
      setValidation(data.validation);
      setWarnings(data.warnings);
      setUnparsed(data.unparsed_lines);
      setStats(data.stats);
      appendLog({
        level: data.validation.ok ? 'success' : 'warning',
        message: `Conversão ${data.source_vendor}→${data.target_vendor} concluída. Erros=${data.validation.summary.error}, warnings=${data.validation.summary.warning}.`,
      });
      toast.success(`Convertido para ${data.target_vendor.toUpperCase()}.`);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      appendLog({ level: 'error', message: 'Erro na conversão: ' + detail });
      toast.error('Falha: ' + detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <Topbar
        onUpload={handleUpload}
        onParse={handleParse}
        onConvert={handleConvert}
        onOpenDiff={() => setDiffOpen(true)}
        onOpenLogs={() => setLogsOpen(true)}
      />
      <main className="flex flex-1 gap-3 p-3 overflow-hidden">
        <SourcePanel />
        <StructurePanel />
        <TargetPanel />
      </main>
      <DiffDrawer open={diffOpen} onClose={() => setDiffOpen(false)} />
      <LogsDrawer open={logsOpen} onClose={() => setLogsOpen(false)} />
    </div>
  );
}
