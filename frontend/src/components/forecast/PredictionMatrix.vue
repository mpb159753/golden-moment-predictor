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
        <div class="watermark">数据来源：专业气象预报模型 · 黄金时刻预测 GMP</div>
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
 * 分数色阶（暖橙日落主题）
 * score >= 80  → score-star   (金橙/琥珀，强烈推荐)
 * score >= 50  → score-good   (温杏/暖黄，推荐)
 * score >= 25  → score-mild   (浅米色，一般)
 * score < 25   → score-poor   (纯白/发灰，不推荐)
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
    background: #ffffff; /* 确保内部白色背景 */
}

/* ── 表格基础 ── */
table {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    font-size: 13px;
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 表头：山系标题行 ── */
.group-header-row th {
    background: #C0392B; /* 砖红标题 */
    color: #ffffff;
    font-weight: 800;
    letter-spacing: 0.12em;
    padding: 12px 14px;
    border: none;
}

.group-name-cell {
    text-align: center;
    font-size: 16px;
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    letter-spacing: 0.2em;
}

.date-header {
    font-size: 12px;
    font-weight: 600;
    opacity: 0.95;
    min-width: 82px;
    text-align: center;
    white-space: pre-line;
    line-height: 1.5;
}

/* ── 景点名称列 ── */
.viewpoint-name {
    font-weight: 700;
    font-size: 13px;
    color: #333333;
    background: #FFFFFF;
    min-width: 76px;
    padding: 0 10px;
    border-right: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    vertical-align: middle;
    white-space: normal;
    word-break: keep-all;
    text-align: center;
    line-height: 1.4;
}

/* ── 上午/下午标签 ── */
.period-label {
    font-size: 11px;
    font-weight: 600;
    min-width: 32px;
    padding: 6px 6px;
    border-right: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    white-space: nowrap;
    text-align: center;
    letter-spacing: 0.05em;
}

.am-label {
    color: #92400e;
    background: #FFFAEB;
}

.pm-label {
    color: #0c4a6e;
    background: #F0F9FF;
}

/* ── 数据格子 ── */
.score-cell {
    padding: 6px 4px;
    border-bottom: 1px solid #F3F4F6;
    border-right: 1px solid #F3F4F6;
    vertical-align: middle;
    transition: filter 0.15s;
}

.score-cell:hover { filter: brightness(0.95); }

.cell-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    line-height: 1.2;
}

/* 景观事件标签：需要更大更醒目 */
.cell-event {
    font-size: 13px; /* 从 11px 放大到 13px */
    font-weight: 900;
    white-space: nowrap;
    color: inherit;
    background: rgba(255, 255, 255, 0.4);
    border-radius: 12px; /* 圆角更大 */
    padding: 2px 8px; /* 内边距更大 */
    letter-spacing: 0.02em;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* 轻微阴影突出 */
}

/* 天气行：次要信息，字号缩小或保持相对较小 */
.cell-weather {
    display: flex;
    align-items: center;
    gap: 2px;
    white-space: nowrap;
}

.weather-icon {
    font-size: 12px;
    line-height: 1;
}

.weather-text {
    font-size: 11px;
    font-weight: 500;
    opacity: 0.85;
}

/* ══ 评分色阶（暖橙日落主题）══
   ★ ≥80: 饱和金橙，字白，强烈推荐
   ✦ 50-79: 温杏色/淡橙黄，深褐字，值得关注
   - 25-49: 极淡米色，灰字，存在但不突出
   · <25: 纯白/接近纯白，浅灰字，视觉静音
*/
.score-star {
    background: #FF8C00;
    color: #FFFFFF;
}
.score-star .cell-event {
    background: rgba(255, 255, 255, 0.25);
    color: #FFFFFF;
    text-shadow: 0 1px 2px rgba(180, 83, 9, 0.5); /* 文字阴影增加可读性 */
}

.score-good {
    background: #FFD580;
    color: #5C2A0B;
}
.score-good .cell-event {
    background: rgba(255, 255, 255, 0.6);
    color: #8C430B;
}

.score-mild {
    background: #FFF3E0;
    color: #97786A;
}
.score-mild .cell-event {
    background: rgba(255, 255, 255, 0.8);
    color: #7B5C43;
}

.score-poor {
    background: #FAFAFA;
    color: #9CA3AF;
}

/* ── 页脚 ── */
.footer-row td {
    background: #FFFFFF;
    border-top: 1px solid #E5E7EB;
    padding: 8px 12px;
}

.footer-cell {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #6b7280;
}

.footer-brand { font-weight: 700; color: #374151; }
.footer-time { font-style: italic; }

/* ── 品牌水印 ── */
.watermark {
    text-align: center;
    padding: 8px 0;
    font-size: 11px;
    color: #9CA3AF;
    letter-spacing: 0.05em;
    font-family: 'Noto Sans SC', sans-serif;
    border-top: 1px solid #F3F4F6;
    background: #FFFFFF;
}

/* ── 行间色 ── */
.row-even .viewpoint-name {
    background: #FFFFFF;
}
.row-odd .viewpoint-name {
    background: #F9FAFB;
}
</style>
