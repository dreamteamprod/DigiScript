import { ref } from 'vue';

export function useHoverTooltip() {
  const tooltipTarget = ref<HTMLElement | null>(null);
  const tooltipText = ref('');
  const tooltipVisible = ref(false);

  function showTooltip(text: string, event: MouseEvent): void {
    tooltipTarget.value = event.currentTarget as HTMLElement;
    tooltipText.value = text;
    tooltipVisible.value = true;
  }

  function hideTooltip(): void {
    tooltipVisible.value = false;
  }

  return { tooltipTarget, tooltipText, tooltipVisible, showTooltip, hideTooltip };
}
