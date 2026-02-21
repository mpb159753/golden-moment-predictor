<template>
    <div class="prediction-matrix">
        <table>
            <thead>
                <tr class="group-header-row">
                    <th colspan="2" class="group-name-cell">{{ group.name }}</th>
                    <th v-for="day in days" :key="day" class="date-header">{{ formatDate(day) }}</th>
                </tr>
            </thead>
            <tbody>
                <template v-for="(vp, vpIdx) in group.viewpoints" :key="vp.id">
                    <!-- 上午行 -->
                    <tr :class="['data-row', 'am-row', vpIdx % 2 === 0 ? 'row-even' : 'row-odd']">
                        <td :rowspan="2" class="viewpoint-name">{{ vp.name }}</td>
                        <td class="period-label am-label">上午</td>
                        <td
                            v-for="day in days"
                            :key="day + '-am'"
                            class="score-cell"
                            :class="getScoreClass(getDayData(vp, day)?.am?.score ?? 0)"
                        >
                            <span class="cell-inner">
                                <span class="cell-event" v-if="getDayData(vp, day)?.am?.event && (getDayData(vp, day)?.am?.score ?? 0) >= 50">
                                    {{ getDayData(vp, day)?.am?.event }}
                                </span>
                                <span class="cell-weather">{{ getDayData(vp, day)?.am?.weather || '—' }}</span>
                            </span>
                        </td>
                    </tr>
                    <!-- 下午行 -->
                    <tr :class="['data-row', 'pm-row', vpIdx % 2 === 0 ? 'row-even' : 'row-odd']">
                        <td class="period-label pm-label">下午</td>
                        <td
                            v-for="day in days"
                            :key="day + '-pm'"
                            class="score-cell"
                            :class="getScoreClass(getDayData(vp, day)?.pm?.score ?? 0)"
                        >
                            <span class="cell-inner">
                                <span class="cell-event" v-if="getDayData(vp, day)?.pm?.event && (getDayData(vp, day)?.pm?.score ?? 0) >= 50">
                                    {{ getDayData(vp, day)?.pm?.event }}
                                </span>
                                <span class="cell-weather">{{ getDayData(vp, day)?.pm?.weather || '—' }}</span>
                            </span>
                        </td>
                    </tr>
                </template>
            </tbody>
            <tfoot v-if="showFooter">
                <tr class="footer-row">
                    <td :colspan="2 + days.length" class="footer-cell">
                        <span class="footer-brand">黄金时刻预测</span>
                        <span class="footer-time">更新于 {{ formatGeneratedAt(generatedAt) }}</span>
                    </td>
                </tr>
            </tfoot>
        </table>
    </div>
</template>

<script setup>
const props = defineProps({
    group: { type: Object, required: true },
    days: { type: Array, required: true },
    showHeader: { type: Boolean, default: true },
    showFooter: { type: Boolean, default: false },
    generatedAt: { type: String, default: '' },
})

function formatDate(dateStr) {
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatGeneratedAt(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/**
 * 返回分数对应的 CSS class，替代内联 backgroundColor
 * score >= 80  → score-star   (强烈推荐，深青）
 * score >= 50  → score-good   (推荐，暖琥珀）
 * score >= 25  → score-mild   (一般，冷蓝灰）
 * score < 25   → score-poor   (不推荐，极浅冷灰）
 */
function getScoreClass(score) {
    if (score >= 80) return 'score-star'
    if (score >= 50) return 'score-good'
    if (score >= 25) return 'score-mild'
    return 'score-poor'
}

function getDayData(vp, day) {
    return vp.daily?.find(d => d.date === day)
}
</script>

<style scoped>
/* ── 容器 ── */
.prediction-matrix {
    overflow-x: auto;
}

/* ── 表格基础 ── */
table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    font-size: 12.5px;
    font-family: 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
}

/* ── 表头：山系标题行 ── */
.group-header-row th {
    background: #1e293b;   /* slate-900 */
    color: #f8fafc;        /* slate-50 */
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 10px 12px;
    border: none;
}

.group-name-cell {
    text-align: left;
    font-size: 13.5px;
}

.date-header {
    font-size: 12px;
    font-weight: 600;
    opacity: 0.85;
    min-width: 80px;
}

/* ── 景点名称列 ── */
.viewpoint-name {
    font-weight: 600;
    font-size: 12px;
    color: #334155;        /* slate-700 */
    background: #f8fafc;   /* slate-50 */
    min-width: 72px;
    padding: 0 10px;
    border-right: 2px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
    white-space: normal;
    word-break: keep-all;
    text-align: center;
    line-height: 1.3;
}

/* ── 上午/下午标签 ── */
.period-label {
    font-size: 11px;
    font-weight: 500;
    min-width: 32px;
    padding: 5px 6px;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    white-space: nowrap;
}

.am-label {
    color: #b45309;        /* amber-700 */
    background: #fffbeb;   /* amber-50 */
}

.pm-label {
    color: #6366f1;        /* indigo-500 */
    background: #eef2ff;   /* indigo-50 */
}

/* ── 行间隔着色 ── */
.row-even .viewpoint-name,
.row-even .period-label { /* 已由 am/pm 覆盖 */ }

/* ── 数据格子 ── */
.score-cell {
    padding: 5px 6px;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    border-right: 1px solid rgba(0,0,0,0.06);
    vertical-align: middle;
    transition: opacity 0.15s;
}

.score-cell:hover { opacity: 0.85; }

.cell-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    line-height: 1.3;
}

.cell-event {
    font-size: 11.5px;
    font-weight: 700;
    color: inherit;
    white-space: nowrap;
}

.cell-weather {
    font-size: 10.5px;
    opacity: 0.75;
    white-space: nowrap;
}

/* ══ 评分色阶 ══
   设计原则：
   - 强推荐 (≥80)：深青底 + 白字，醒目但不刺眼
   - 推荐   (50-79)：暖琥珀底，中等饱和，文字深棕
   - 一般   (25-49)：冷蓝灰底，低饱和，表示「存在但不突出」
   - 不推荐 (<25)： 极浅冷底，几乎无色，低噪声
*/
.score-star {
    background: #0d9488;   /* teal-600 */
    color: #ffffff;
}
.score-star .cell-weather { color: rgba(255,255,255,0.8); }

.score-good {
    background: #fef3c7;   /* amber-100 */
    color: #92400e;        /* amber-800 */
}

.score-mild {
    background: #e2e8f0;   /* slate-200 */
    color: #475569;        /* slate-600 */
}

.score-poor {
    background: #f8fafc;   /* slate-50 */
    color: #94a3b8;        /* slate-400 */
}

/* ── 页脚 ── */
.footer-row td {
    background: #f1f5f9;   /* slate-100 */
    border-top: 1px solid #cbd5e1;
    padding: 8px 12px;
}

.footer-cell {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #64748b;        /* slate-500 */
}

.footer-brand { font-weight: 700; color: #334155; }
.footer-time { font-style: italic; }
</style>
