<template>
    <div class="poster-view">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
            <p>加载中...</p>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="error" class="error-state">
            <p>加载失败：{{ error }}</p>
        </div>

        <!-- 主内容 -->
        <template v-else-if="posterData">
            <!-- 页面头部：标题 + 天数切换 + 导出按钮 -->
            <header class="poster-header">
                <div class="poster-header__title">
                    <h1>黄金时刻预测海报</h1>
                    <p class="poster-header__dates">{{ dateRange }}</p>
                </div>
                <div class="poster-header__controls">
                    <div class="day-selector">
                        <button
                            v-for="d in [3, 5, 7]"
                            :key="d"
                            class="day-btn"
                            :class="{ active: selectedDays === d }"
                            @click="selectedDays = d"
                        >{{ d }}天</button>
                    </div>
                    <button class="export-btn" @click="exportAll">
                        一键导出全部
                    </button>
                </div>
            </header>

            <!-- 分组表格 -->
            <div class="poster-content">
                <div
                    v-for="group in posterData.groups"
                    :key="group.key"
                    :ref="el => { if (el) groupRefs[group.key] = el }"
                    class="group-section"
                >
                    <PredictionMatrix
                        :group="group"
                        :days="displayedDays"
                        :showHeader="true"
                        :showFooter="false"
                        :generatedAt="posterData.generated_at"
                    />
                </div>
            </div>
        </template>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const { loadPoster } = useDataLoader()

const posterData = ref(null)
const loading = ref(true)
const error = ref(null)
const selectedDays = ref(5)
const groupRefs = ref({})

const displayedDays = computed(() => {
    if (!posterData.value) return []
    return posterData.value.days.slice(0, selectedDays.value)
})

const dateRange = computed(() => {
    const days = displayedDays.value
    if (!days.length) return ''
    const fmt = d => {
        const dt = new Date(d)
        return `${dt.getMonth() + 1}/${dt.getDate()}`
    }
    return `${fmt(days[0])} — ${fmt(days[days.length - 1])}`
})

onMounted(async () => {
    try {
        posterData.value = await loadPoster()
    } catch (e) {
        error.value = e.message
    } finally {
        loading.value = false
    }
})

async function exportAll() {
    // 每组独立导出 PNG（1080px 宽）
    for (const group of posterData.value?.groups ?? []) {
        const el = groupRefs.value[group.key]
        if (!el) continue
        try {
            const { default: html2canvas } = await import('html2canvas')
            const canvas = await html2canvas(el, { width: 1080, scale: 2 })
            const link = document.createElement('a')
            link.download = `poster_${group.key}.png`
            link.href = canvas.toDataURL('image/png')
            link.click()
        } catch (e) {
            console.error(`导出 ${group.name} 失败:`, e)
        }
    }
}
</script>

<style scoped>
.poster-view {
    min-height: 100vh;
    background: #f5f5f5;
    padding: 24px;
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.loading-state,
.error-state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: #666;
    font-size: 16px;
}

.error-state {
    color: #e53e3e;
}

.poster-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px;
    padding: 16px 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.poster-header__title h1 {
    margin: 0 0 4px;
    font-size: 22px;
    color: #1a1a1a;
}

.poster-header__dates {
    margin: 0;
    color: #666;
    font-size: 14px;
}

.poster-header__controls {
    display: flex;
    align-items: center;
    gap: 16px;
}

.day-selector {
    display: flex;
    gap: 4px;
}

.day-btn {
    padding: 6px 14px;
    border: 1px solid #d0d0d0;
    background: white;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    color: #555;
    transition: all 0.15s;
}

.day-btn.active {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
}

.day-btn:hover:not(.active) {
    border-color: #2563eb;
    color: #2563eb;
}

.export-btn {
    padding: 8px 20px;
    background: #059669;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.15s;
}

.export-btn:hover {
    background: #047857;
}

.poster-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.group-section {
    background: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
</style>
