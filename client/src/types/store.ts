import type { Show } from './api/show';

export interface RootState {
  currentShow: Show | null;
}
