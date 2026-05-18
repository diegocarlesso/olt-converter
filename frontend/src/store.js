import { create } from 'zustand';

/**
 * Frontend mantém APENAS view-state. O OLTConfig vive no backend.
 * Selection, expanded tree, filtros, target preview, drawer visibility.
 */
export const useStore = create((set, get) => ({
  // session
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  resetSession: () => set({
    sessionId: null, selection: null, expandedGroups: { vlans: true, pons: true, service_ports: false, uplinks: true, profiles: false },
    filter: '', filterSource: 'all', filterNeedsReview: false, targetVendor: 'fiberhome',
  }),

  // selection
  selection: null,  // { entity_type, entity_id }
  setSelection: (sel) => set({ selection: sel }),

  // explorer state
  expandedGroups: { vlans: true, pons: true, service_ports: false, uplinks: true, profiles: false },
  toggleGroup: (k) => set((s) => ({ expandedGroups: { ...s.expandedGroups, [k]: !s.expandedGroups[k] } })),
  expandedPons: {},  // pon_iface -> bool
  togglePon: (k) => set((s) => ({ expandedPons: { ...s.expandedPons, [k]: !s.expandedPons[k] } })),

  // filters
  filter: '',
  setFilter: (v) => set({ filter: v }),
  filterSource: 'all',  // all|parser|inference|synthesis|promotion|manual|default
  setFilterSource: (v) => set({ filterSource: v }),
  filterNeedsReview: false,
  setFilterNeedsReview: (v) => set({ filterNeedsReview: v }),

  // preview
  targetVendor: 'fiberhome',
  setTargetVendor: (v) => set({ targetVendor: v }),
  previewMode: 'cli',  // cli | diff
  setPreviewMode: (v) => set({ previewMode: v }),

  // recent sessions (persisted to localStorage manualmente)
  recentSessions: JSON.parse(localStorage.getItem('olt:recent') || '[]'),
  pushRecent: (entry) => set((s) => {
    const next = [entry, ...s.recentSessions.filter(r => r.session_id !== entry.session_id)].slice(0, 10);
    localStorage.setItem('olt:recent', JSON.stringify(next));
    return { recentSessions: next };
  }),
}));
