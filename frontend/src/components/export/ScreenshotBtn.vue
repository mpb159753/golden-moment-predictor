<template>
  <button
    class="screenshot-btn"
    :class="{ 'screenshot-btn--loading': capturing }"
    @click="handleCapture"
    :disabled="capturing"
  >
    <span v-if="!capturing" class="screenshot-btn__icon">📷</span>
    <span v-else class="screenshot-btn__spinner" />
    <span class="screenshot-btn__text">
      {{ capturing ? '截图中...' : displayLabel }}
    </span>
  </button>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useScreenshot } from '@/composables/useScreenshot'

const props = defineProps({
  target: { type: [String, Object], required: true },
  filename: { type: String, default: 'gmp-prediction.png' },
  beforeCapture: { type: Function, default: null },
  afterCapture: { type: Function, default: null },
  label: { type: String, default: '截图' },
})

const { capture } = useScreenshot()
const capturing = ref(false)

const displayLabel = computed(() => props.label)

async function handleCapture() {
  capturing.value = true
  try {
    if (props.beforeCapture) await props.beforeCapture()
    const element = typeof props.target === 'string'
      ? document.querySelector(props.target)
      : props.target?.$el ?? props.target
    await capture(element, props.filename)
  } catch (e) {
    console.error('Screenshot failed:', e)
  } finally {
    if (props.afterCapture) await props.afterCapture()
    capturing.value = false
  }
}
</script>

<style scoped>
.screenshot-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.screenshot-btn:hover {
  box-shadow: var(--shadow-elevated);
  transform: translateY(-1px);
}

.screenshot-btn--loading {
  opacity: 0.7;
  cursor: wait;
}

.screenshot-btn__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--text-muted);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
