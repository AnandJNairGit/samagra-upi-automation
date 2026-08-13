import React from 'react';
import { HealthStatus } from '../components/HealthStatus';
import { ShieldCheck, Layers } from 'lucide-react';

export const App: React.FC = () => {
  return (
    <div className="container">
      <header className="header">
        <div className="badge">
          <ShieldCheck size={14} />
          Phase 1 — Infrastructure Skeleton
        </div>
        <h1 className="title">Samagra UPI Automation</h1>
        <p className="subtitle">
          Foundational modular monolith stack: Vite + React, FastAPI, PostgreSQL, and Host Caddy.
        </p>
      </header>

      <main>
        <HealthStatus />

        <div className="card">
          <h2 className="card-title">
            <Layers size={20} color="#a78bfa" />
            Active Service Topologies
          </h2>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Host Reverse Proxy</td>
                <td className="meta-val">Host Caddy (Ports 80 / 443)</td>
              </tr>
              <tr>
                <td className="meta-key">Public URL Routes</td>
                <td className="meta-val">/upi/* (Frontend), /upi-api/* (Backend)</td>
              </tr>
              <tr>
                <td className="meta-key">Frontend Host Port</td>
                <td className="meta-val">127.0.0.1:8080 (Prod) / 127.0.0.1:5173 (Dev)</td>
              </tr>
              <tr>
                <td className="meta-key">Backend Host Port</td>
                <td className="meta-val">127.0.0.1:8001 (FastAPI Container)</td>
              </tr>
              <tr>
                <td className="meta-key">PostgreSQL Storage</td>
                <td className="meta-val">./docker/postgres/data (Host Bind Mount)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>

      <footer className="footer">
        <p>Samagra UPI Automation Platform &bull; Phase 1 Verified</p>
      </footer>
    </div>
  );
};
