// Global type definitions for DigiScript Vue 3

// Future API response types will be defined here during Phase 2
// These will match the existing API structures from the Vue 2 app

// Basic API response structure
export interface ApiResponse<T = unknown> {
  data?: T
  error?: string
  success: boolean
}

// Future user types (Phase 2)
// export interface User {
//   id: number
//   username: string
//   email: string
//   is_admin: boolean
//   permissions: number
//   created_at: string
//   updated_at: string
// }

// Future show types (Phase 2)
// export interface Show {
//   id: number
//   name: string
//   description: string
//   created_at: string
//   updated_at: string
// }

// Future WebSocket message types (Phase 2)
// export interface WebSocketMessage {
//   OP: string
//   DATA: any
//   ACTION?: string
//   namespace?: string
// }

// Vue Router meta type extensions
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    permissions?: number[]
  }
}
