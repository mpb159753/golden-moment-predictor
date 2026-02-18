/**
 * 组合推荐标签计算 (前端自行计算)。
 *
 * 组合规则 (来自设计文档 10-frontend-common.md §10.0.4):
 *
 * | 标签类型          | 触发条件                                      | 显示文字     |
 * |-------------------|----------------------------------------------|-------------|
 * | combo_day         | 同日 2+ 个 score≥80 的事件                    | 组合日      |
 * | photographer_pick | 金山(sunrise/sunset) + cloud_sea 同日均 ≥80  | 摄影师推荐  |
 * | perfect_day       | 任一事件 score≥95                              | 完美之日    |
 */
export function useComboTags() {
    /**
     * @param {Array<{event_type: string, score: number}>} dayEvents - 某日的事件数组
     * @returns {Array<{type: string, label: string, icon: string}>} 标签列表
     */
    function computeTags(dayEvents) {
        const tags = []
        const recommended = dayEvents.filter(e => e.score >= 80)

        // combo_day: 同日 2+ 个 Recommended 以上事件
        if (recommended.length >= 2) {
            tags.push({ type: 'combo_day', label: '组合日', icon: '🎯' })
        }

        // photographer_pick: 金山+云海同日
        const hasGoldenMountain = recommended.some(e =>
            e.event_type.includes('golden_mountain')
        )
        const hasCloudSea = recommended.some(e =>
            e.event_type === 'cloud_sea'
        )
        if (hasGoldenMountain && hasCloudSea) {
            tags.push({ type: 'photographer_pick', label: '摄影师推荐', icon: '📸' })
        }

        // perfect_day: 有任一事件 95+
        if (dayEvents.some(e => e.score >= 95)) {
            tags.push({ type: 'perfect_day', label: '完美之日', icon: '✨' })
        }

        return tags
    }

    return { computeTags }
}
