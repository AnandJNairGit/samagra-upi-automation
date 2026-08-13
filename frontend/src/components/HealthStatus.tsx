import React, { useState, useEffect } from 'react';
import { checkAppHealth, checkDatabaseHealth, HealthResponse, DbHealthResponse } from '../services/api';
import { RefreshCw, Server, XCircle, Clock } from 'lucide-react';
import { config } from '../core/config';

export const HealthStatus: React.FC = () => {
  const [appStatus, setAppStatus] = useState<'checking' | 'connected' | 'unavailable'>('checking');
  const [dbStatus, setDbStatus] = useState<'checking' | 'connected' | 'unavailable'>('checking');
  const [appData, setAppData] = useState<HealthResponse | null>(null);
  const [dbData, setDbData] = useState<DbHealthResponse | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const performChecks = async () => {
    setIsRefreshing(true);
    setAppStatus('checking');
    setDbStatus('checking');

    try {
      const appRes = await checkAppHealth();
      setAppData(appRes);
      setAppStatus(appRes.status === 'ok' ? 'connected' : 'unavailable');
    } catch {
      setAppData(null);
      setAppStatus('unavailable');
    }

    try {
      const dbRes = await checkDatabaseHealth();
      setDbData(dbRes);
      setDbStatus(dbRes.status === 'ok' ? 'connected' : 'unavailable');
    } catch {
      setDbData(null);
      setDbStatus('unavailable');
    }

    setLastChecked(new Date().toLocaleTimeString());
    setIsRefreshing(false);
  };

  useEffect(() => {
    performChecks();
    const interval = setInterval(performChecks, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 className="card-title" style={{ margin: 0 }}>
          <Server size={20} color="#60a5fa" />
          Infrastructure Connectivity
        </h2>
        <button
          onClick={performChecks}
          disabled={isRefreshing}
          className="btn"
          title="Refresh connectivity status"
        >
          <RefreshCw size={14} className={isRefreshing ? 'pulse' : ''} />
          {isRefreshing ? 'Checking...' : 'Refresh'}
        </button>
      </div>

      <div className="status-grid">
        {/* Backend App Health */}
        <div className="status-item">
          <div className="status-info">
            <span className="status-label">FastAPI Backend</span>
            <span className="status-endpoint">/upi-api/v1/health</span>
          </div>
          <div>
            {appStatus === 'connected' && (
              <span className="status-pill connected">
                <span className="dot pulse" />
                Connected
              </span>
            )}
            {appStatus === 'unavailable' && (
              <span className="status-pill unavailable">
                <XCircle size={14} />
                Unavailable
              </span>
            )}
            {appStatus === 'checking' && (
              <span className="status-pill checking">
                <Clock size={14} />
                Checking
              </span>
            )}
          </div>
        </div>

        {/* PostgreSQL Database Health */}
        <div className="status-item">
          <div className="status-info">
            <span className="status-label">PostgreSQL Database</span>
            <span className="status-endpoint">/upi-api/v1/health/db</span>
          </div>
          <div>
            {dbStatus === 'connected' && (
              <span className="status-pill connected">
                <span className="dot pulse" />
                Connected
              </span>
            )}
            {dbStatus === 'unavailable' && (
              <span className="status-pill unavailable">
                <XCircle size={14} />
                Unavailable
              </span>
            )}
            {dbStatus === 'checking' && (
              <span className="status-pill checking">
                <Clock size={14} />
                Checking
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Connection Metadata */}
      <table className="meta-table">
        <tbody>
          <tr>
            <td className="meta-key">Frontend Base Path</td>
            <td className="meta-val">{config.basePath}</td>
          </tr>
          <tr>
            <td className="meta-key">API Base URL</td>
            <td className="meta-val">{config.apiBaseUrl}</td>
          </tr>
          <tr>
            <td className="meta-key">Backend Reported App</td>
            <td className="meta-val">{appData?.app || '—'}</td>
          </tr>
          <tr>
            <td className="meta-key">Backend Environment</td>
            <td className="meta-val">{appData?.env || '—'}</td>
          </tr>
          <tr>
            <td className="meta-key">Database Status</td>
            <td className="meta-val">{dbData?.database || '—'}</td>
          </tr>
          <tr>
            <td className="meta-key">Last Inspected</td>
            <td className="meta-val">{lastChecked || 'Pending initial check'}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
