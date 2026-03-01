/**
 * 从 posterData 构建精简摘要，用于 AI 生成小红书文案。
 * @param {object} data - posterData
 * @param {number} dayCount - 要包含的天数（从 dayOffset 起）
 * @param {number} [dayOffset=0] - 起始偏移（0=今天，1=明天）
 * @returns {object} summary
 */
export function buildSummary(data, dayCount, dayOffset = 0) {
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
                    if (!slot) continue

                    if (!groupBest || slot.score > groupBest.分数) {
                        groupBest = { 点位: vp.name, 分数: slot.score, 天气: slot.weather }
                    }

                    if (slot.score < 60) continue

                    highlights.push({
                        日期: day.date,
                        时段: half === 'am' ? '上午' : '下午',
                        区域: group.name,
                        点位: vp.name,
                        景观: slot.event || '无',
                        天气: slot.weather,
                        分数: slot.score
                    })
                }
            }
        }
        if (groupBest) groupOverview[group.name] = groupBest
    }

    highlights.sort((a, b) => b.分数 - a.分数)

    const fmt = d => {
        const dt = new Date(d)
        return `${dt.getMonth() + 1}月${dt.getDate()}日`
    }
    const dateRange = displayedDayList.length
        ? `${fmt(displayedDayList[0])}—${fmt(displayedDayList[displayedDayList.length - 1])}`
        : ''

    return {
        生成时间: data.generated_at,
        适用日期: dateRange,
        各区概况: groupOverview,
        推荐点位: highlights,
    }
}
