/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BASE_PATH?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEV_BACKEND_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
