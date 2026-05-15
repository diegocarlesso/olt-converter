import { create } from 'zustand';

export const useStore = create((set) => ({
  sourceText: '',
  sourceVendor: null,
  targetVendor: 'zte',
  vendors: [],
  parsedConfig: null,
  renderedConfig: '',
  diff: '',
  validation: null,
  warnings: [],
  unparsedLines: [],
  stats: {},
  loading: false,
  logs: [],

  setSourceText: (sourceText) => set({ sourceText }),
  setSourceVendor: (sourceVendor) => set({ sourceVendor }),
  setTargetVendor: (targetVendor) => set({ targetVendor }),
  setVendors: (vendors) => set({ vendors }),
  setParsed: (parsedConfig) => set({ parsedConfig }),
  setRendered: (renderedConfig) => set({ renderedConfig }),
  setDiff: (diff) => set({ diff }),
  setValidation: (validation) => set({ validation }),
  setWarnings: (warnings) => set({ warnings }),
  setUnparsed: (unparsedLines) => set({ unparsedLines }),
  setStats: (stats) => set({ stats }),
  setLoading: (loading) => set({ loading }),
  appendLog: (entry) =>
    set((state) => ({
      logs: [{ id: Date.now() + Math.random(), at: new Date().toISOString(), ...entry }, ...state.logs].slice(0, 200),
    })),
  clearLogs: () => set({ logs: [] }),
}));
