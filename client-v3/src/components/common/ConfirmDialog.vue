<template>
  <BModal
    v-model="visible"
    :title="currentOptions.title ?? 'Confirm'"
    :ok-variant="currentOptions.okVariant ?? 'primary'"
    :ok-title="currentOptions.okTitle ?? 'OK'"
    :cancel-title="currentOptions.cancelTitle ?? 'Cancel'"
    :size="currentOptions.size"
    @ok="_handleOk"
    @hidden="_handleHidden"
  >
    {{ message }}
  </BModal>
</template>

<script setup lang="ts">
import { useConfirm } from '@/composables/useConfirm';

const { visible, message, currentOptions, _handleOk, _handleHidden } = useConfirm();
</script>
