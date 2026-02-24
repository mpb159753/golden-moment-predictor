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
                    <button class="export-btn" :disabled="exporting" @click="exportAll">
                        <svg v-if="!exporting" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline;vertical-align:-2px;margin-right:5px"><path d="M12 2v14M5 9l7 7 7-7"/><rect x="3" y="18" width="18" height="3" rx="1"/></svg>
                        <span v-if="exporting">{{ exportProgress }}</span>
                        <span v-else>一键导出全部</span>
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
import { ref, computed, reactive, onMounted } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const { loadPoster } = useDataLoader()

const posterData = ref(null)
const loading = ref(true)
const error = ref(null)
const selectedDays = ref(5)
const groupRefs = reactive({})
const exporting = ref(false)
const exportProgress = ref('')

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

/**
 * 从 posterData 构建精简摘要，用于 AI 生成小红书文案。
 * @param {object} data - posterData
 * @param {number} dayCount - 要包含的天数（从 dayOffset 起）
 * @param {number} [dayOffset=0] - 起始偏移（0=今天，1=明天）
 * @returns {object} summary
 */
function buildSummary(data, dayCount, dayOffset = 0) {
    const displayedDayList = data.days.slice(dayOffset, dayOffset + dayCount)
    const highlights = []
    const groupOverview = {}

    for (const group of data.groups) {
        let groupBest = null
        for (const vp of group.viewpoints) {
            for (const day of vp.daily) {
                if (!displayedDayList.includes(day.date)) continue
                for (const half of ['am', 'pm']) {
                    const slot = day[half]
                    if (!slot || slot.score < 70) continue
                    highlights.push({
                        date: day.date,
                        period: half === 'am' ? '上午' : '下午',
                        group: group.name,
                        viewpoint: vp.name,
                        event: slot.event || '',
                        weather: slot.weather,
                        score: slot.score,
                        conditions: slot.conditions || {},
                    })
                    if (!groupBest || slot.score > groupBest.score) {
                        groupBest = { date: day.date, viewpoint: vp.name, score: slot.score }
                    }
                }
            }
        }
        if (groupBest) groupOverview[group.name] = groupBest
    }

    highlights.sort((a, b) => b.score - a.score)

    const fmt = d => {
        const dt = new Date(d)
        return `${dt.getMonth() + 1}月${dt.getDate()}日`
    }
    const dateRange = displayedDayList.length
        ? `${fmt(displayedDayList[0])}—${fmt(displayedDayList[displayedDayList.length - 1])}`
        : ''

    return {
        generated_at: data.generated_at,
        date_range: dateRange,
        highlights,
        group_overview: groupOverview,
    }
}

async function exportAll() {
    if (exporting.value) return
    exporting.value = true
    try {
        const [{ default: html2canvas }, { default: JSZip }] = await Promise.all([
            import('html2canvas'),
            import('jszip'),
        ])
        const zip = new JSZip()
        const groups = posterData.value?.groups ?? []
        const dateStr = posterData.value.generated_at.slice(0, 10).replace(/-/g, '')

        // ── 图片截图 ──
        console.log('[导出] 开始，共', groups.length, '个分组，groupRefs 键：', Object.keys(groupRefs))
        for (let i = 0; i < groups.length; i++) {
            const group = groups[i]
            const el = groupRefs[group.key]
            if (!el) {
                console.warn(`[导出] 找不到 ${group.key} 的 DOM 节点，跳过`)
                continue
            }
            exportProgress.value = `渲染中 ${i + 1}/${groups.length}…`
            try {
                const canvas = await html2canvas(el, {
                    scale: 2,
                    backgroundColor: '#ffffff',
                    useCORS: true,
                    logging: false,
                })
                const base64 = canvas.toDataURL('image/png').split(',')[1]
                zip.file(`poster_${group.key}_${dateStr}.png`, base64, { base64: true })
                console.log(`[导出] ${group.name} 截图完成`)
            } catch (e) {
                console.error(`渲染 ${group.name} 失败:`, e)
            }
        }

        // ── 精简 JSON（供 AI 生成文案）──

        // 明日摘要（日帖用）：取 days[1]，即明天
        const summaryTomorrow = buildSummary(posterData.value, 1, 1)
        zip.file(`poster_tomorrow_${dateStr}.json`, JSON.stringify(summaryTomorrow, null, 2))

        // 本周摘要（周报用）：取全部 7 天
        const summaryWeek = buildSummary(posterData.value, 7, 0)
        zip.file(`poster_week_${dateStr}.json`, JSON.stringify(summaryWeek, null, 2))

        // ── 打包下载 ──
        exportProgress.value = '打包中…'
        // 使用 blob URL 触发下载。data URI 在 Safari 下有 ~15MB 大小限制，
        // 7 张 scale=2 PNG 打包后远超限制会静默失败（UUID 文件名无法打开）。
        // 改回 blob URL，并延迟 5s 释放，确保 Safari 有足够时间完成文件写入。
        const blob = await zip.generateAsync({ type: 'blob' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.setAttribute('href', url)
        // 文件名格式：posters_YYYYMMDD.zip（以数据生成日期为准）
        link.setAttribute('download', `posters_${dateStr}.zip`)
        link.style.display = 'none'
        document.body.appendChild(link)
        link.click()
        setTimeout(() => {
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
        }, 5000)
    } finally {
        exporting.value = false
        exportProgress.value = ''
    }
}
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

.export-btn {
    padding: 8px 20px;
    background: #FF8C00;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-family: inherit;
    font-weight: 600;
    transition: all 0.2s;
    box-shadow: 0 2px 8px rgba(255, 140, 0, 0.25);
}

.export-btn:hover:not(:disabled) {
    background: #E67E00;
    box-shadow: 0 4px 12px rgba(255, 140, 0, 0.35);
    transform: translateY(-1px);
}

.export-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
}

/* ── 内容区 ── */
.poster-content {
    display: flex;
    flex-direction: column;
    gap: 32px; /* 组间隔大一些，呼吸感好 */
}

.group-section {
    width: 540px;   /* 小红书场景固定宽：html2canvas scale=2 → 1080px 物理像素 */
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
