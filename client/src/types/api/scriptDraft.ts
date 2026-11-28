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

export interface CollabWarningMessage {
  warning: string;
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
 * carries no sender tag of its own), matching `RoomMember.client_id`. `currentPage` is
 * optional so a sender running older code (or one that hasn't navigated yet) doesn't
 * fail validation — a missing value just means "unknown page" to every receiver.
 */
export interface AwarenessState {
  clientId: string;
  openLineUids: string[];
  currentPage?: number;
}

/**
 * A room member's last-known awareness snapshot, keyed by `client_id` in
 * `scriptDraft`'s `remoteAwareness`. Kept as one object per sender (rather than two
 * parallel maps) so a member who leaves is pruned in a single place.
 */
export interface RemoteAwareness {
  openLineUids: string[];
  currentPage?: number;
}
