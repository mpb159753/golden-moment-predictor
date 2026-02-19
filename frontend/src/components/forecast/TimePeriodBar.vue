<script setup>
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
    periods: {
        type: Array,
        required: true,
    },
})

const { getScoreColor } = useScoreColor()

function scoreDisplay(score) {
    return score > 0 ? String(score) : '--'
}

function scoreColorStyle(score) {
    if (score <= 0) return {}
    const { color } = getScoreColor(score)
    return { color }
}
</script>

<template>
    <div class="time-period-bar">
        <div
            v-for="period in periods"
            :key="period.id"
            class="period-cell"
        >
            <span class="period-icon">{{ period.icon }}</span>
            <span class="period-label">{{ period.label }}</span>
            <span class="period-score" :style="scoreColorStyle(period.bestScore)">
                {{ scoreDisplay(period.bestScore) }}
            </span>
        </div>
    </div>
</template>

<style scoped>
.time-period-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
}

.period-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 4px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
}

.period-icon {
    font-size: 18px;
    line-height: 1;
}

.period-label {
    font-size: 11px;
    color: var(--color-text-secondary, #9CA3AF);
}

.period-score {
    font-size: 16px;
    font-weight: 700;
    color: var(--color-text-secondary, #9CA3AF);
}
</style>
