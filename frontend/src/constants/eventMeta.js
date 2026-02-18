/**
 * 事件类型元数据 — 共享常量
 *
 * 统一定义 event_type 对应的颜色和中文名称，
 * 由 WeekTrend / HourlyTimeline 等组件共享引用。
 * 颜色值与设计文档 §10.0.3 EventIcon 主色保持一致。
 */

/** 事件颜色映射 (与 EventIcon 主色一致) */
export const EVENT_COLORS = {
    sunrise_golden_mountain: '#FF8C00',
    sunset_golden_mountain: '#FF4500',
    cloud_sea: '#87CEEB',
    stargazing: '#4A0E8F',
    frost: '#B0E0E6',
    snow_tree: '#E0E8EF',
    ice_icicle: '#ADD8E6',
}

/** 事件中文名称映射 */
export const EVENT_NAMES = {
    sunrise_golden_mountain: '日出金山',
    sunset_golden_mountain: '日落金山',
    cloud_sea: '云海',
    stargazing: '观星',
    frost: '雾凇',
    snow_tree: '树挂积雪',
    ice_icicle: '冰挂',
}
