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
            <!-- 页面头部 -->
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
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:-2px;margin-right:5px"><path d="M12 2v14M5 9l7 7 7-7"/><rect x="3" y="18" width="18" height="3" rx="1"/></svg>
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

            <!-- 页面底部 -->
            <footer class="poster-footer">
                <span>黄金时刻预测 · GMP</span>
                <span>数据更新于 {{ formattedGeneratedAt }}</span>
            </footer>
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

const formattedGeneratedAt = computed(() => {
    const iso = posterData.value?.generated_at
    if (!iso) return ''
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
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
    for (const group of posterData.value?.groups ?? []) {
        const el = groupRefs.value[group.key]
        if (!el) continue
        try {
            const { default: html2canvas } = await import('html2canvas')
            const canvas = await html2canvas(el, {
                width: 1080,
                scale: 2,
                backgroundColor: '#ffffff',
                useCORS: true,
            })
            const link = document.createElement('a')
            link.download = `poster_${group.key}.png`
            link.href = canvas.toDataURL('image/png')
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
        } catch (e) {
            console.error(`导出 ${group.name} 失败:`, e)
        }
    }
}
</script>

<style scoped>
.poster-view {
    min-height: 100vh;
    background: linear-gradient(160deg, #f0faf4 0%, #fefce8 50%, #f0f7f4 100%);
    padding: 24px;
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.loading-state,
.error-state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: #6b7280;
    font-size: 16px;
}

.error-state {
    color: #e53e3e;
}

/* ── 页面头部 ── */
.poster-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px;
    padding: 16px 22px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(45, 106, 79, 0.10);
    border: 1px solid #c8e6c9;
}

.poster-header__title h1 {
    margin: 0 0 4px;
    font-size: 20px;
    color: #1a4a2e;
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.poster-header__dates {
    margin: 0;
    color: #6b9a6b;
    font-size: 13px;
}

.poster-header__controls {
    display: flex;
    align-items: center;
    gap: 14px;
}

.day-selector {
    display: flex;
    gap: 4px;
}

.day-btn {
    padding: 6px 14px;
    border: 1.5px solid #c8e0c8;
    background: white;
    border-radius: 20px;
    cursor: pointer;
    font-size: 12px;
    color: #4a7a4a;
    transition: all 0.15s;
    font-family: inherit;
}

.day-btn.active {
    background: #2d6a4f;
    border-color: #2d6a4f;
    color: white;
}

.day-btn:hover:not(.active) {
    border-color: #2d6a4f;
    color: #2d6a4f;
    background: #f0f7f0;
}

.export-btn {
    padding: 8px 18px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-family: inherit;
    font-weight: 600;
    transition: all 0.2s;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.35);
}

.export-btn:hover {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.45);
    transform: translateY(-1px);
}

/* ── 内容区 ── */
.poster-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.group-section {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #c8e0c8;
    box-shadow: 0 2px 10px rgba(45, 106, 79, 0.08);
}

/* ── 页脚 ── */
.poster-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 24px;
    padding: 10px 16px;
    color: #9ab89a;
    font-size: 11px;
    border-top: 1px solid #dceadc;
    letter-spacing: 0.04em;
}
</style>
