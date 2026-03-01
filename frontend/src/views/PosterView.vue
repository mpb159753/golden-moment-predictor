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
                            v-for="d in [3, 7]"
                            :key="d"
                            class="day-btn"
                            :class="{ active: selectedDays === d }"
                            @click="selectedDays = d"
                        >{{ d }}天</button>
                    </div>

                </div>
            </header>

            <!-- 分组表格 -->
            <div class="poster-content">
                <div
                    v-for="group in posterData.groups"
                    :key="group.key"
                    :ref="el => { if (el) groupRefs[group.key] = el }"
                    class="group-section"
                    :style="groupSectionStyle"
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
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useDataLoader } from '@/composables/useDataLoader'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const route = useRoute()
const { loadPoster } = useDataLoader()

const posterData = ref(null)
const loading = ref(true)
const error = ref(null)
const selectedDays = ref(Number(route.query.days) || 7)
const groupRefs = reactive({})


const displayedDays = computed(() => {
    if (!posterData.value) return []
    return posterData.value.days.slice(1, 1 + selectedDays.value)
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

// 根据天数动态计算表格宽度（景点名 76px + 时段 32px = 108px，每列 90px）
const groupSectionStyle = computed(() => {
    const w = Math.max(540, 108 + selectedDays.value * 90)
    return { width: w + 'px' }
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


</script>

<style scoped>
.poster-view {
    min-height: 100vh;
    background: #F9FAFB; /* 最简洁的浅灰白背景 */
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
    color: #EF4444;
}

/* ── 页面头部 ── */
.poster-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px;
    padding: 18px 24px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    border: 1px solid #E5E7EB;
}

.poster-header__title h1 {
    margin: 0 0 6px;
    font-size: 22px;
    color: #C0392B; /* 与表格标题呼应的砖红 */
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    font-weight: 800;
    letter-spacing: 0.05em;
}

.poster-header__dates {
    margin: 0;
    color: #6B7280;
    font-size: 14px;
    font-weight: 500;
}

.poster-header__controls {
    display: flex;
    align-items: center;
    gap: 16px;
}

.day-selector {
    display: flex;
    gap: 6px;
}

.day-btn {
    padding: 6px 16px;
    border: 1px solid #D1D5DB;
    background: white;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    color: #4B5563;
    transition: all 0.15s;
    font-family: inherit;
    font-weight: 500;
}

.day-btn.active {
    background: #C0392B;
    border-color: #C0392B;
    color: white;
}

.day-btn:hover:not(.active) {
    border-color: #C0392B;
    color: #C0392B;
    background: #FEF2F2;
}



/* ── 内容区 ── */
.poster-content {
    display: flex;
    flex-direction: column;
    gap: 32px; /* 组间隔大一些，呼吸感好 */
}

.group-section {
    /* 宽度由 groupSectionStyle 动态计算：3天 540px / 5天 558px / 7天 738px */
    background: white;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

/* ── 页脚 ── */
.poster-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 32px;
    padding: 12px 16px;
    color: #9CA3AF;
    font-size: 12px;
    border-top: 1px solid #E5E7EB;
    letter-spacing: 0.02em;
}
</style>
