/**
 * 评分→颜色/状态映射。
 *
 * 映射规则 (来自设计文档 10-frontend-common.md §10.0.3):
 *
 * | 范围    | CSS 变量                   | 状态              | 颜色描述   |
 * |---------|----------------------------|--------------------|------------|
 * | 95-100  | --score-perfect            | Perfect            | 金色渐变   |
 * | 80-94   | --score-recommended        | Recommended        | 翠绿       |
 * | 50-79   | --score-possible           | Possible           | 琥珀       |
 * | 0-49    | --score-not-recommended    | Not Recommended    | 灰色       |
 */
export function useScoreColor() {
    /**
     * 获取评分对应的颜色信息
     * @param {number} score - 0-100 评分
     * @returns {{ color: string, gradient: string|null, status: string, statusCn: string, cssVar: string }}
     */
    function getScoreColor(score) {
        if (score >= 95) return {
            color: '#FFD700',
            gradient: 'linear-gradient(135deg, #FFD700, #FF8C00)',
            status: 'Perfect',
            statusCn: '完美',
            cssVar: '--score-perfect',
        }
        if (score >= 80) return {
            color: '#10B981',
            gradient: null,
            status: 'Recommended',
            statusCn: '推荐',
            cssVar: '--score-recommended',
        }
        if (score >= 50) return {
            color: '#F59E0B',
            gradient: null,
            status: 'Possible',
            statusCn: '一般',
            cssVar: '--score-possible',
        }
        return {
            color: '#9CA3AF',
            gradient: null,
            status: 'Not Recommended',
            statusCn: '不推荐',
            cssVar: '--score-not-recommended',
        }
    }

    /**
     * 获取状态文字对应的颜色 (用于从 API status 字段映射)
     * @param {string} status - 'Perfect' | 'Recommended' | 'Possible' | 'Not Recommended'
     */
    function getStatusColor(status) {
        const map = {
            'Perfect': '#FFD700',
            'Recommended': '#10B981',
            'Possible': '#F59E0B',
            'Not Recommended': '#9CA3AF',
        }
        return map[status] ?? '#9CA3AF'
    }

    return { getScoreColor, getStatusColor }
}
