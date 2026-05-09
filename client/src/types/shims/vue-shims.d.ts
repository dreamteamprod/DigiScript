export {};

declare module 'vue/types/vue' {
  interface VueToastPlugin {
    open(options: Record<string, unknown>): unknown;
    success(message: string, options?: Record<string, unknown>): unknown;
    warning(message: string, options?: Record<string, unknown>): unknown;
    error(message: string, options?: Record<string, unknown>): unknown;
    info(message: string, options?: Record<string, unknown>): unknown;
    clear(): void;
  }
  interface Vue {
    $socket: WebSocket & { sendObj: (obj: object) => void };
    $toast: VueToastPlugin;
  }
  interface VueConstructor {
    $toast: VueToastPlugin;
  }
}

declare module 'vue/types/options' {
  // eslint-disable-next-line no-undef
  interface ComponentOptions<V extends Vue> {
    sockets?: Record<string, (data: unknown) => void>;
  }
}
