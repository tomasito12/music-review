/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PROFILE_STYLE_MAP?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
