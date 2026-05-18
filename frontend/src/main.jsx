import React from 'react';
import ReactDOM from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App.jsx';
import './index.css';

const qc = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5_000, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: { background: '#15192b', color: '#e2e8f0', border: '1px solid #1e2638' },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
