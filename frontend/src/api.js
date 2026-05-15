import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

export const listVendors = () => api.get('/vendors').then((r) => r.data);

export const uploadConfig = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data);
};

export const parseConfig = (config_text, vendor) =>
  api.post('/parse', { config_text, vendor }).then((r) => r.data);

export const convertConfig = ({ config_text, source_vendor, target_vendor }) =>
  api.post('/convert', { config_text, source_vendor, target_vendor }).then((r) => r.data);

export const renderConfig = (config, target_vendor) =>
  api.post('/render', { config, target_vendor }).then((r) => r.data);

export const validateConfig = (config) =>
  api.post('/validate', { config }).then((r) => r.data);

export default api;
