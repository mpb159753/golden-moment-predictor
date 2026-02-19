/**
 * 四段摄影时段划分与评分计算。
 *
 * 时段定义 (来自设计文档 11-frontend-architecture-v2.md §11.4.2):
 *
 * | 时段   | 时间        | 典型事件           |
 * |--------|-------------|--------------------|
 * | 🌄 日出 | 05:00-08:00 | 日出金山、晴天      |
 * | ☀️ 白天 | 08:00-16:00 | 晴天、雾凇、雪挂树  |
 * | 🌅 日落 | 16:00-19:00 | 日落金山、晴天      |
 * | ⭐ 夜晚 | 19:00-05:00 | 观星               |
 */
export function useTimePeriod() {
    const periods = [
        { id: 'sunrise', label: '日出', icon: '🌄', start: 5, end: 8 },
        { id: 'daytime', label: '白天', icon: '☀️', start: 8, end: 16 },
        { id: 'sunset', label: '日落', icon: '🌅', start: 16, end: 19 },
        { id: 'night', label: '夜晚', icon: '⭐', start: 19, end: 5 },
    ]

    /**
     * 判断某小时是否属于指定时段
     */
    function isHourInPeriod(hour, period) {
        if (period.start < period.end) {
            // 普通时段: start <= hour < end
            return hour >= period.start && hour < period.end
        }
        // 跨午夜时段 (night): hour >= start 或 hour < end
        return hour >= period.start || hour < period.end
    }

    /**
     * 根据 timeline hourly 数据计算每个时段的最佳事件+评分
     * @param {Array} hourly - timeline.json 的 hourly 数组
     * @returns {Array<{id, label, icon, start, end, bestScore, bestEvent, events}>}
     */
    function getPeriodScores(hourly) {
        return periods.map(period => {
            const periodEvents = []

            for (const h of hourly) {
                if (!isHourInPeriod(h.hour, period)) continue
                if (!h.events_active) continue

                for (const evt of h.events_active) {
                    periodEvents.push(evt)
                }
            }

            let bestScore = 0
            let bestEvent = null

            for (const evt of periodEvents) {
                if (evt.score > bestScore) {
                    bestScore = evt.score
                    bestEvent = evt.event_type
                }
            }

            return {
                ...period,
                bestScore,
                bestEvent,
                events: periodEvents,
            }
        })
    }

    return { periods, getPeriodScores }
}
