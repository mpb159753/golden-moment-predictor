<template>
  <span
    class="status-badge"
    :style="{
      backgroundColor: bgColor,
      color: textColor,
    }"
  >
    {{ displayText }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: v => ['Perfect', 'Recommended', 'Possible', 'Not Recommended'].includes(v),
  },
  lang: { type: String, default: 'cn' },
})

const { getStatusColor } = useScoreColor()

const labelMap = {
  cn: {
    'Perfect': '完美',
    'Recommended': '推荐',
    'Possible': '一般',
    'Not Recommended': '不推荐',
  },
  en: {
    'Perfect': 'Perfect',
    'Recommended': 'Recommended',
    'Possible': 'Possible',
    'Not Recommended': 'Not Recommended',
  },
}

const displayText = computed(() => labelMap[props.lang]?.[props.status] ?? props.status)
const baseColor = computed(() => getStatusColor(props.status))
const bgColor = computed(() => `${baseColor.value}20`) // 12% 透明度背景
const textColor = computed(() => baseColor.value)
</script>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
}
</style>
