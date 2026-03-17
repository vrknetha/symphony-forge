/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AZURE_AUTHORITY?: string;
  readonly VITE_AZURE_CLIENT_ID?: string;
  readonly VITE_AZURE_REDIRECT_URI?: string;
  readonly VITE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
