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
                                <span class="cell-weather">
                                    <span class="weather-icon">{{ weatherEmoji(getDayData(vp, day)?.am?.weather) }}</span>
                                    <span class="weather-text">{{ getDayData(vp, day)?.am?.weather || '—' }}</span>
                                </span>
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
                                <span class="cell-weather">
                                    <span class="weather-icon">{{ weatherEmoji(getDayData(vp, day)?.pm?.weather) }}</span>
                                    <span class="weather-text">{{ getDayData(vp, day)?.pm?.weather || '—' }}</span>
                                </span>
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
        <!-- 品牌水印 -->
        <div class="watermark">黄金时刻预测 GMP · golden-moment-predictor</div>
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

const WEATHER_EMOJI = {
    '晴天': '☀️',
    '多云': '⛅',
    '阴天': '☁️',
    '雾': '🌫️',
    '小雨': '🌦️',
    '中雨': '🌧️',
    '大雨': '🌧️',
    '雨': '🌦️',
    '小雪': '🌨️',
    '大雪': '❄️',
    '雪': '🌨️',
    '冻雨': '🌨️',
}

function weatherEmoji(weather) {
    if (!weather) return ''
    return WEATHER_EMOJI[weather] ?? '🌤️'
}

function formatDate(dateStr) {
    const d = new Date(dateStr)
    const weekDays = ['日', '一', '二', '三', '四', '五', '六']
    return `${d.getMonth() + 1}/${d.getDate()}\n周${weekDays[d.getDay()]}`
}

function formatGeneratedAt(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/**
 * 分数色阶（明亮主题）
 * score >= 80  → score-star   (金橙，强烈推荐)
 * score >= 50  → score-good   (翠绿，推荐)
 * score >= 25  → score-mild   (蓝灰，一般)
 * score < 25   → score-poor   (极浅，不推荐)
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
    position: relative;
}

/* ── 表格基础 ── */
table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    font-size: 12px;
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 表头：山系标题行 ── */
.group-header-row th {
    background: linear-gradient(135deg, #1a4a2e 0%, #2d6a4f 60%, #1a5e3a 100%);
    color: #fef9e7;
    font-weight: 800;
    letter-spacing: 0.1em;
    padding: 11px 14px;
    border: none;
}

.group-name-cell {
    text-align: left;
    font-size: 14px;
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    letter-spacing: 0.14em;
}

.date-header {
    font-size: 11px;
    font-weight: 600;
    opacity: 0.92;
    min-width: 78px;
    text-align: center;
    white-space: pre-line;
    line-height: 1.6;
}

/* ── 景点名称列 ── */
.viewpoint-name {
    font-weight: 700;
    font-size: 11.5px;
    color: #2d4a2d;
    background: #f0f7f0;
    min-width: 68px;
    padding: 0 10px;
    border-right: 2px solid #c8e0c8;
    border-bottom: 1px solid #dceadc;
    vertical-align: middle;
    white-space: normal;
    word-break: keep-all;
    text-align: center;
    line-height: 1.4;
}

/* ── 上午/下午标签 ── */
.period-label {
    font-size: 10.5px;
    font-weight: 600;
    min-width: 28px;
    padding: 4px 6px;
    border-right: 1px solid #e0ece0;
    border-bottom: 1px solid #e8f0e8;
    white-space: nowrap;
    text-align: center;
    letter-spacing: 0.02em;
}

.am-label {
    color: #92400e;
    background: #fffbeb;
}

.pm-label {
    color: #4c1d95;
    background: #f5f3ff;
}

/* ── 数据格子 ── */
.score-cell {
    padding: 5px 5px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    border-right: 1px solid rgba(0, 0, 0, 0.06);
    vertical-align: middle;
    transition: filter 0.15s;
}

.score-cell:hover { filter: brightness(0.94); }

.cell-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    line-height: 1.3;
}

/* 景观事件标签 */
.cell-event {
    font-size: 11px;
    font-weight: 800;
    white-space: nowrap;
    color: inherit;
    background: rgba(255, 255, 255, 0.55);
    border-radius: 10px;
    padding: 1px 7px;
    letter-spacing: 0.02em;
}

/* 天气行 */
.cell-weather {
    display: flex;
    align-items: center;
    gap: 2px;
    white-space: nowrap;
}

.weather-icon {
    font-size: 11px;
    line-height: 1;
}

.weather-text {
    font-size: 10px;
    opacity: 0.78;
}

/* ══ 评分色阶（明亮主题）══
   ★ ≥80: 饱和金橙，醒目强推
   ✦ 50-79: 清新翠绿，值得关注
   - 25-49: 冷蓝灰，存在但不突出
   · <25: 极浅米色，视觉静音
*/
.score-star {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
    color: #78350f;
}
.score-star .cell-event {
    background: rgba(255, 255, 255, 0.6);
    color: #7c2d12;
}

.score-good {
    background: linear-gradient(135deg, #6ee7b7 0%, #34d399 100%);
    color: #064e3b;
}
.score-good .cell-event {
    background: rgba(255, 255, 255, 0.55);
    color: #065f46;
}

.score-mild {
    background: #dbeafe;
    color: #1e40af;
}
.score-mild .cell-event {
    background: rgba(255, 255, 255, 0.6);
}

.score-poor {
    background: #fafaf9;
    color: #a8a29e;
}

/* ── 页脚 ── */
.footer-row td {
    background: #f0f7f0;
    border-top: 1px solid #c8e0c8;
    padding: 8px 12px;
}

.footer-cell {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #6b7280;
}

.footer-brand { font-weight: 700; color: #2d4a2d; }
.footer-time { font-style: italic; }

/* ── 品牌水印 ── */
.watermark {
    text-align: center;
    padding: 6px 0;
    font-size: 10px;
    color: #a0b8a0;
    letter-spacing: 0.08em;
    font-family: 'Noto Sans SC', sans-serif;
    border-top: 1px solid #dceadc;
    background: #f8fcf8;
}

/* ── 行间色 ── */
.row-even .viewpoint-name {
    background: #f0f7f0;
}
.row-odd .viewpoint-name {
    background: #e8f4e8;
}
</style>
