import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

export const http = axios.create({ baseURL: BASE, timeout: 60000 });

// Sessions
export const createSession = async (configText, vendor = null) => {
  const { data } = await http.post('/sessions', { config_text: configText, vendor });
  return data;
};

export const getProjection = async (sid) => {
  const { data } = await http.get(`/sessions/${sid}/projection`);
  return data;
};

export const getEntity = async (sid, type, id) => {
  const { data } = await http.get(`/sessions/${sid}/entity/${type}/${encodeURIComponent(id)}`);
  return data;
};

export const patchEntity = async (sid, patch) => {
  const { data } = await http.patch(`/sessions/${sid}/entity`, patch);
  return data;
};

export const renderTarget = async (sid, vendor) => {
  const { data } = await http.get(`/sessions/${sid}/render/${vendor}`);
  return data;
};

export const getValidation = async (sid) => {
  const { data } = await http.get(`/sessions/${sid}/validation`);
  return data;
};

export const getAudit = async (sid) => {
  const { data } = await http.get(`/sessions/${sid}/audit`);
  return data;
};

export const undoSession = async (sid) => {
  const { data } = await http.post(`/sessions/${sid}/undo`);
  return data;
};

export const redoSession = async (sid) => {
  const { data } = await http.post(`/sessions/${sid}/redo`);
  return data;
};

// Discovery
export const listVendors = async () => {
  const { data } = await http.get('/vendors');
  return data;
};
