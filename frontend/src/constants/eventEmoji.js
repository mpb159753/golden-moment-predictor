/**
 * 事件类型 → emoji 映射表。
 *
 * 用于 Marker 图标徽章和 BottomSheet 半展态标题行。
 * 因 AMap Marker 使用 HTML 字符串，无法用 Vue 组件渲染 SVG，
 * 因此改用 emoji 表示事件图标。
 */
export const EVENT_EMOJI = {
    clear_sky: '☀️',
    sunrise_golden_mountain: '🏔️',
    sunset_golden_mountain: '🏔️',
    cloud_sea: '☁️',
    stargazing: '⭐',
    frost: '❄️',
    snow_tree: '❄️',
    ice_icicle: '❄️',
}
