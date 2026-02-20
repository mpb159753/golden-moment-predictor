<script setup>
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
    daily: {
        type: Array,
        required: true,
    },
    selectedDate: {
        type: String,
        default: null,
    },
})

const emit = defineEmits(['select'])

const { getScoreColor } = useScoreColor()

const WEEKDAY_SHORT = ['日', '一', '二', '三', '四', '五', '六']

function formatDay(dateStr) {
    const d = new Date(dateStr + 'T00:00:00+08:00')
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return { date: `${mm}/${dd}`, weekday: `周${WEEKDAY_SHORT[d.getDay()]}` }
}

function scoreColorStyle(score) {
    const { color } = getScoreColor(score)
    return { color }
}
</script>

<template>
    <div class="mini-trend">
        <div
            v-for="day in daily"
            :key="day.date"
            class="trend-day"
            :class="{ selected: day.date === selectedDate }"
            @click="emit('select', day.date)"
        >
            <span class="trend-date">{{ formatDay(day.date).date }}</span>
            <span class="trend-weekday">{{ formatDay(day.date).weekday }}</span>
            <span class="trend-score" :style="scoreColorStyle(day.best_event?.score ?? 0)">
                {{ day.best_event?.score ?? 0 }}
            </span>
        </div>
    </div>
</template>

<style scoped>
.mini-trend {
    display: flex;
    gap: 4px;
}

.trend-day {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 4px 2px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
}

.trend-day:hover {
    background: rgba(255, 255, 255, 0.08);
}

.trend-day.selected {
    background: rgba(59, 130, 246, 0.2);
    box-shadow: inset 0 0 0 1.5px rgba(59, 130, 246, 0.5);
}

.trend-day.selected .trend-date,
.trend-day.selected .trend-weekday {
    color: var(--color-primary, #3B82F6);
    font-weight: 600;
}

.trend-date {
    font-size: 11px;
    color: var(--color-text-secondary, #9CA3AF);
}

.trend-weekday {
    font-size: 10px;
    color: var(--color-text-secondary, #9CA3AF);
}

.trend-score {
    font-size: 14px;
    font-weight: 700;
}

/* 移动端紧凑适配 */
@media (max-width: 420px) {
    .mini-trend {
        gap: 2px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .mini-trend::-webkit-scrollbar {
        display: none;
    }
    .trend-day {
        min-width: 44px;
        padding: 4px 1px;
    }
    .trend-date {
        font-size: 10px;
    }
    .trend-weekday {
        font-size: 9px;
    }
    .trend-score {
        font-size: 12px;
    }
}
</style>
