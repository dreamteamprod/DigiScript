export interface RoomMember {
  user_id: number | null;
  username: string;
  role: 'editor' | 'viewer';
  /** Per-connection key — `user_id` alone can't tell one user's two tabs apart. */
  client_id: string | null;
}

export interface RoomMembersMessage {
  members: RoomMember[];
}

export interface CollabErrorMessage {
  error: string;
}

export interface ScriptSavedMessage {
  last_saved_at: string;
}

export interface SaveProgressMessage {
  page: number;
  total: number;
  percent: number;
}

/**
 * The JSON shape sent/received as the payload of a `YJS_AWARENESS` message — the
 * server relays these as opaque bytes, so this encoding is entirely client-owned.
 * `clientId` self-identifies the sender (the broadcast excludes them server-side but
 * carries no sender tag of its own), matching `RoomMember.client_id`.
 */
export interface AwarenessState {
  clientId: string;
  openLineUids: string[];
}
