import Store from 'electron-store';
import { randomUUID } from 'crypto';

export interface Connection {
  id: string;
  url: string;
  nickname: string;
  lastConnected: number | null;
  sslEnabled: boolean;
  username: string | null;
  passwordHash: string | null;
}

export interface ConnectionInput {
  url: string;
  nickname: string;
  sslEnabled?: boolean;
  username?: string | null;
  passwordHash?: string | null;
}

interface ConnectionStoreSchema {
  connections: Connection[];
  activeConnectionId: string | null;
}

class ConnectionManager {
  private store: Store<ConnectionStoreSchema>;
  private appStore: Store<Record<string, unknown>>;

  constructor() {
    this.store = new Store<ConnectionStoreSchema>({
      name: 'digiscript-connections',
      schema: {
        connections: {
          type: 'array',
          default: [],
          items: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              url: { type: 'string' },
              nickname: { type: 'string' },
              lastConnected: { type: ['number', 'null'] },
              sslEnabled: { type: 'boolean', default: false },
              username: { type: ['string', 'null'], default: null },
              passwordHash: { type: ['string', 'null'], default: null },
            },
            required: ['id', 'url', 'nickname'],
          },
        },
        activeConnectionId: {
          type: ['string', 'null'],
          default: null,
        },
      },
    });

    this.appStore = new Store({
      name: 'digiscript-app-storage',
    });
  }

  getAllConnections(): Connection[] {
    return this.store.get('connections', []);
  }

  getConnectionById(id: string): Connection | null {
    const connections = this.getAllConnections();
    return connections.find((conn) => conn.id === id) || null;
  }

  addConnection(connection: ConnectionInput): Connection {
    const connections = this.getAllConnections();

    const newConnection: Connection = {
      id: randomUUID(),
      url: connection.url,
      nickname: connection.nickname,
      lastConnected: null,
      sslEnabled: connection.sslEnabled || false,
      username: connection.username || null,
      passwordHash: connection.passwordHash || null,
    };

    connections.push(newConnection);
    this.store.set('connections', connections);

    return newConnection;
  }

  updateConnection(id: string, updates: Partial<Omit<Connection, 'id'>>): Connection | null {
    const connections = this.getAllConnections();
    const index = connections.findIndex((conn) => conn.id === id);

    if (index === -1) {
      return null;
    }

    connections[index] = {
      ...connections[index],
      ...updates,
      id,
    };

    this.store.set('connections', connections);
    return connections[index];
  }

  deleteConnection(id: string): boolean {
    const connections = this.getAllConnections();
    const filtered = connections.filter((conn) => conn.id !== id);

    if (filtered.length === connections.length) {
      return false;
    }

    this.store.set('connections', filtered);

    if (this.store.get('activeConnectionId') === id) {
      this.store.set('activeConnectionId', null);
    }

    return true;
  }

  getActiveConnection(): Connection | null {
    const activeId = this.store.get('activeConnectionId');
    if (!activeId) {
      return null;
    }
    return this.getConnectionById(activeId);
  }

  setActiveConnection(id: string): Connection | null {
    const connection = this.getConnectionById(id);
    if (!connection) {
      return null;
    }

    this.updateConnection(id, { lastConnected: Date.now() });

    this.store.set('activeConnectionId', id);

    return this.getConnectionById(id);
  }

  clearActiveConnection(): void {
    this.store.set('activeConnectionId', null);
  }

  getStorageItem(key: string): unknown {
    return this.appStore.get(key, null);
  }

  setStorageItem(key: string, value: unknown): void {
    this.appStore.set(key, value);
  }

  deleteStorageItem(key: string): void {
    this.appStore.delete(key);
  }

  clearStorage(): void {
    this.appStore.clear();
  }
}

export default ConnectionManager;
