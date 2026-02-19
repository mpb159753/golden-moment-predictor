/**
 * 事件类型 → 内联 SVG 映射表。
 *
 * 用于 AMap Marker 图标徽章。因 AMap Marker 使用 HTML 字符串，
 * 无法用 Vue 组件渲染，因此提供可直接嵌入 HTML 的 SVG 字符串。
 *
 * @param {number} size - SVG 尺寸 (默认 16px)
 * @param {string} color - SVG 颜色 (默认 white)
 */

function makeSvg(innerContent, size = 16, color = 'white') {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;">${innerContent}</svg>`
}

const SVG_CONTENT = {
    clear_sky: `<circle cx="12" cy="12" r="5" fill="%COLOR%" stroke="none"/><g stroke="%COLOR%" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.93" y1="4.93" x2="6.76" y2="6.76"/><line x1="17.24" y1="17.24" x2="19.07" y2="19.07"/><line x1="4.93" y1="19.07" x2="6.76" y2="17.24"/><line x1="17.24" y1="6.76" x2="19.07" y2="4.93"/></g>`,
    sunrise_golden_mountain: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">日</text>`,
    sunset_golden_mountain: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">落</text>`,
    cloud_sea: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">云</text>`,
    stargazing: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">星</text>`,
    frost: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">霜</text>`,
    snow_tree: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">雪</text>`,
    ice_icicle: `<circle cx="12" cy="12" r="10" /><text x="12" y="16" text-anchor="middle" font-size="10" fill="%COLOR%" stroke="none">冰</text>`,
}

/**
 * 获取事件类型的内联 SVG 字符串
 * @param {string} eventType - 事件类型
 * @param {number} [size=16] - SVG 尺寸
 * @param {string} [color='white'] - SVG 颜色
 * @returns {string} 内联 SVG 字符串，类型不存在时返回空字符串
 */
export function getEventSvgBadge(eventType, size = 16, color = 'white') {
    const template = SVG_CONTENT[eventType]
    if (!template) return ''
    const inner = template.replaceAll('%COLOR%', color)
    return makeSvg(inner, size, color)
}
