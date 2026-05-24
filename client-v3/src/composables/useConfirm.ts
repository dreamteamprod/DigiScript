import { ref } from 'vue';

export interface ConfirmOptions {
  title?: string;
  okVariant?: string;
  okTitle?: string;
  cancelTitle?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

// Module-level singleton state shared across all callers
const visible = ref(false);
const message = ref('');
const currentOptions = ref<ConfirmOptions>({});
let resolveCallback: ((value: boolean) => void) | null = null;
let resolved = false;

function _handleOk(): void {
  if (resolved) return;
  resolved = true;
  resolveCallback?.(true);
}

function _handleHidden(): void {
  if (resolved) return;
  resolved = true;
  resolveCallback?.(false);
}

export function useConfirm() {
  function confirm(msg: string, opts: ConfirmOptions = {}): Promise<boolean> {
    message.value = msg;
    currentOptions.value = opts;
    resolved = false;
    visible.value = true;
    return new Promise((resolve) => {
      resolveCallback = resolve;
    });
  }

  return { confirm, visible, message, currentOptions, _handleOk, _handleHidden };
}
