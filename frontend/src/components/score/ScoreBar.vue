<template>
  <div class="score-bar">
    <div class="score-bar__header">
      <span class="score-bar__label">{{ label }}</span>
      <span v-if="showValues" class="score-bar__values">{{ score }} / {{ max }}</span>
    </div>
    <div class="score-bar__track">
      <div
        class="score-bar__fill"
        :style="{
          width: `${percentage}%`,
          backgroundColor: colorInfo.color,
          backgroundImage: colorInfo.gradient || 'none',
          transition: 'width 0.8s var(--ease-out-expo)',
        }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  score: { type: Number, default: 0 },
  label: { type: String, default: '' },
  max: { type: Number, default: 100 },
  showValues: { type: Boolean, default: true },
})

const { getScoreColor } = useScoreColor()
const percentage = computed(() => props.max > 0 ? Math.min(100, Math.max(0, (props.score / props.max) * 100)) : 0)
const normalizedScore = computed(() => props.max > 0 ? Math.min(100, Math.max(0, Math.round((props.score / props.max) * 100))) : 0)
const colorInfo = computed(() => getScoreColor(normalizedScore.value))
</script>

<style scoped>
.score-bar__track {
  height: 6px;
  background: #E5E7EB;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.score-bar__fill {
  height: 100%;
  border-radius: var(--radius-full);
}

.score-bar__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: var(--text-sm);
}

.score-bar__label {
  color: var(--text-secondary);
}

.score-bar__values {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
