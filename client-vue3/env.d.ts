/// <reference types="vite/client" />
/// <reference lib="DOM" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Environment variables type definitions
interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  // Add more env variables here as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}