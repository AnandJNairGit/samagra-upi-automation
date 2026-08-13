/**
 * Application environment configuration
 */

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/upi-api',
  basePath: import.meta.env.VITE_BASE_PATH || '/upi/',
  appName: 'Samagra UPI Automation',
  isDev: import.meta.env.DEV,
};
