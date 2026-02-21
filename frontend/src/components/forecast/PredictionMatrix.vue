<template>
    <div class="prediction-matrix">
        <table>
            <thead>
                <tr>
                    <th colspan="2">{{ group.name }}</th>
                    <th v-for="day in days" :key="day">{{ formatDate(day) }}</th>
                </tr>
            </thead>
            <tbody>
                <template v-for="vp in group.viewpoints" :key="vp.id">
                    <!-- 上午行 -->
                    <tr>
                        <td :rowspan="2" class="viewpoint-name">{{ vp.name }}</td>
                        <td class="period-label">上午</td>
                        <td
                            v-for="day in days"
                            :key="day + '-am'"
                            :style="{ backgroundColor: getCellColor(getDayData(vp, day)?.am?.score ?? 0) }"
                        >{{ getCellContent(getDayData(vp, day)?.am) }}</td>
                    </tr>
                    <!-- 下午行 -->
                    <tr>
                        <td class="period-label">下午</td>
                        <td
                            v-for="day in days"
                            :key="day + '-pm'"
                            :style="{ backgroundColor: getCellColor(getDayData(vp, day)?.pm?.score ?? 0) }"
                        >{{ getCellContent(getDayData(vp, day)?.pm) }}</td>
                    </tr>
                </template>
            </tbody>
            <tfoot v-if="showFooter">
                <tr>
                    <td :colspan="2 + days.length">
                        <span>更新时间：{{ generatedAt }}</span>
                        <span>黄金时刻预测</span>
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

function getCellColor(score) {
    if (score >= 80) return '#C6EFCE'
    if (score >= 50) return '#FFEB9C'
    if (score >= 25) return '#FFC7CE'
    return '#F4CCCC'
}

function getCellContent(period) {
    if (!period) return ''
    if (period.event && period.score >= 50) {
        return `${period.weather}+${period.event}`
    }
    return period.weather || ''
}

function getDayData(vp, day) {
    return vp.daily?.find(d => d.date === day)
}
</script>

<style scoped>
.prediction-matrix {
    overflow-x: auto;
    margin-bottom: 24px;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
}

th, td {
    border: 1px solid #ccc;
    padding: 6px 8px;
    text-align: center;
    white-space: nowrap;
}

th {
    background: #f0f0f0;
    font-weight: 600;
}

.viewpoint-name {
    font-weight: 500;
    min-width: 80px;
}

.period-label {
    color: #666;
    min-width: 36px;
}
</style>
