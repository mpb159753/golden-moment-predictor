<template>
  <teleport to="body">
    <div v-if="visible" class="share-overlay" @click.self="$emit('close')">
      <div id="share-card-target" class="share-card">
        <!-- 品牌头 -->
        <div class="share-card__header">
          <span class="share-card__logo">🏔️</span>
          <span class="share-card__brand">GMP 川西景观预测</span>
        </div>

        <!-- 内容区 -->
        <div class="share-card__content">
          <h2>{{ viewpoint?.name }} · {{ formatDate(day?.date) }}</h2>
          <div class="share-card__score-area" :style="{ '--score-color': scoreColor }">
            <ScoreRing :score="bestScore" size="xl" />
            <StatusBadge :status="bestStatus" />
          </div>

          <div class="share-card__events">
            <div v-for="event in day?.events" :key="event.event_type" class="share-card__event-row">
              <EventIcon :eventType="event.event_type" :size="20" />
              <span>{{ event.display_name }}</span>
              <span class="share-card__event-score">{{ event.score }}</span>
            </div>
          </div>

          <!-- 标签 -->
          <div class="share-card__tags">
            <span v-for="tag in comboTags" :key="tag.type">{{ tag.icon }} {{ tag.label }}</span>
          </div>
        </div>

        <!-- 品牌底 -->
        <div class="share-card__footer">
          <p>让每一次川西之行，都不错过自然的馈赠</p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="share-overlay__actions">
        <ScreenshotBtn target="#share-card-target" filename="gmp-share.png" />
        <button @click="$emit('close')">关闭</button>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'
import { useComboTags } from '@/composables/useComboTags'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import EventIcon from '@/components/event/EventIcon.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'

const props = defineProps({
  viewpoint: { type: Object, default: null },
  day: { type: Object, default: null },
  visible: { type: Boolean, default: false },
})

defineEmits(['close'])

const { getScoreColor } = useScoreColor()
const { computeTags } = useComboTags()

const bestScore = computed(() => props.day?.best_score ?? 0)
const scoreResult = computed(() => getScoreColor(bestScore.value))
const bestStatus = computed(() => props.day?.best_status || scoreResult.value.status)
const scoreColor = computed(() => scoreResult.value.color)
const comboTags = computed(() => props.day?.events ? computeTags(props.day.events) : [])

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<style scoped>
.share-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.share-card {
  width: 360px;
  max-width: 90vw;
  aspect-ratio: 3 / 4;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  overflow: hidden;
  padding: 32px 24px;
  text-align: center;
}

.share-card__score-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--score-color, transparent) 8%, transparent);
}

.share-card__header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.share-card__logo {
  font-size: 24px;
}

.share-card__brand {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
}

.share-card__content h2 {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.share-card__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.share-card__events {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.share-card__event-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
}

.share-card__event-row span:first-of-type {
  flex: 1;
  text-align: left;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.share-card__event-score {
  font-weight: 700;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.share-card__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 8px;
}

.share-card__tags span {
  padding: 4px 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.share-card__footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.share-card__footer p {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0;
}

.share-overlay__actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.share-overlay__actions button {
  padding: 8px 20px;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  color: white;
  cursor: pointer;
  font-size: var(--text-sm);
  transition: background var(--duration-fast) var(--ease-out-expo);
}

.share-overlay__actions button:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
