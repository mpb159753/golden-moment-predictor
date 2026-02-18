<template>
  <div v-if="meta" class="update-banner">
    <span class="update-banner__icon">🔄</span>
    <span class="update-banner__text">
      数据更新于 {{ formatTime(meta.generated_at) }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  meta: { type: Object, default: null },
})

function formatTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.update-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-card);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  color: var(--text-muted);
  box-shadow: var(--shadow-card);
}
</style>
