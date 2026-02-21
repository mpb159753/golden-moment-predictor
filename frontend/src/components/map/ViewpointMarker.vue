<script>
import { watch, inject, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'
import { useScoreColor } from '@/composables/useScoreColor'
import { convertToGCJ02 } from '@/composables/useCoordConvert'
import { getEventSvgBadge } from '@/constants/eventSvgBadge'

/**
 * ViewpointMarker — 地图评分标记组件
 *
 * 使用 AMap Marker API 创建自定义 DOM 标记。
 * 不渲染自身 DOM，通过 render function 返回 null。
 * 依赖父组件通过 provide('AMapSDK') 注入 AMap 模块。
 *
 * 标记样式:
 * - 常态: 40x40px 圆形，背景色 = 评分颜色，白色数字
 * - 选中: 放大 1.2x + 弹跳动画 + 阴影加深
 * - Perfect (95+): 额外脉冲光圈动画
 */
export default {
  name: 'ViewpointMarker',
  props: {
    viewpoint: { type: Object, required: true },
    score: { type: Number, default: 0 },
    bestEvent: { type: String, default: null },
    selected: { type: Boolean, default: false },
    zoom: { type: Number, default: 10 },
    rank: { type: String, default: 'standard' },  // 'top' | 'standard' | 'low'
    enterDelay: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    map: { type: Object, default: null },
  },
  emits: ['click'],
  setup(props, { emit }) {
    let marker = null
    const AMapSDK = inject('AMapSDK', null)

    const { getScoreColor } = useScoreColor()

    function getSvgBadge(size = 16) {
      if (!props.bestEvent) return ''
      return getEventSvgBadge(props.bestEvent, size, 'white')
    }

    /** 圆点标记 (最小态) */
    function renderDot(bg, dotSize = 12) {
      return `<div style="
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
      "><div class="marker-dot" style="
        width: ${dotSize}px; height: ${dotSize}px; border-radius: 50%;
        background: ${bg};
        border: 2px solid rgba(255,255,255,0.8);
        box-shadow: 0 1px 4px rgba(0,0,0,0.2);
      "></div></div>`
    }

    /** 中等紧凑标记 (评分圆形, 无名称) */
    function renderCompact(bg, colorInfo) {
      return `<div style="
        position: relative; cursor: pointer;
        display: flex; flex-direction: column; align-items: center;
      ">
        <div class="marker-compact" style="
          width: 28px; height: 28px; border-radius: 50%;
          background: ${bg}; color: white;
          display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 11px;
          border: 2px solid rgba(255,255,255,0.8);
          box-shadow: 0 1px 4px rgba(0,0,0,0.25);
        ">${props.score}</div>
        <div style="
          width: 0; height: 0;
          border-left: 4px solid transparent;
          border-right: 4px solid transparent;
          border-top: 4px solid ${bg};
        "></div>
      </div>`
    }

    /** Top 级大标记 (评分+名称+事件图标, 始终可见) */
    function renderTop(bg, colorInfo) {
      const pulse = props.score >= 95
        ? `<div style="
            position: absolute; top: -4px; left: -4px;
            width: 52px; height: 52px; border-radius: 50%;
            border: 2px solid ${colorInfo.color};
            animation: marker-pulse 2s infinite;
            pointer-events: none;
          "></div>`
        : ''
      return `<div class="marker-top" style="
        position: relative;
        transition: transform 0.3s ease;
        padding: 4px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 10;
      ">
        ${pulse}
        <div style="
          width: 44px; height: 44px; border-radius: 50%;
          background: ${bg};
          color: white; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 14px;
          border: 2.5px solid rgba(255,255,255,0.9);
          box-shadow: 0 2px 10px rgba(0,0,0,0.3);
          transition: box-shadow 0.3s ease, transform 0.3s ease;
        ">${getSvgBadge(14)}${props.score}</div>
        <div style="
          width: 0; height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 5px solid ${bg};
        "></div>
        <div style="
          font-size: 10px;
          color: #374151;
          font-weight: 600;
          white-space: nowrap;
          text-align: center;
          margin-top: 2px;
          text-shadow: 0 0 3px white, 0 0 3px white, 0 0 5px white;
          max-width: 80px;
          overflow: hidden;
          text-overflow: ellipsis;
        ">${props.viewpoint.name}</div>
      </div>`
    }

    function createContent() {
      const colorInfo = getScoreColor(props.score)
      const bg = colorInfo.gradient || colorInfo.color
      const rank = props.rank
      const zoom = props.zoom

      const pulse = props.score >= 95
        ? `<div style="
            position: absolute; top: -4px; left: -4px;
            width: 48px; height: 48px; border-radius: 50%;
            border: 2px solid ${colorInfo.color};
            animation: marker-pulse 2s infinite;
            pointer-events: none;
          "></div>`
        : ''

      // 选中态: 展开名称 + 评分 + 弹跳动画 + 脉冲光圈 (最高优先级)
      if (props.selected) {
        return `<div style="
          position: relative;
          transform: scale(1.2);
          animation: marker-bounce 0.4s ease-out;
          transition: transform 0.3s ease;
          z-index: 20;
        ">
          ${pulse}
          <div class="marker-expanded" style="
            position: relative;
            background: ${bg};
            color: white; padding: 6px 12px;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.35);
            cursor: pointer;
            text-align: center;
            min-width: 60px;
          ">
            <div style="font-weight: 700; font-size: 13px; white-space: nowrap;">${props.viewpoint.name}</div>
            <div style="font-size: 12px; margin-top: 2px;">${props.score}</div>
          </div>
          <div class="pulse-glow-ring" style="
            position: absolute;
            inset: -4px;
            border-radius: 8px;
            border: 2px solid ${colorInfo.color};
            animation: pulse-glow 2s ease-in-out infinite;
            pointer-events: none;
          "></div>
          <div style="
            width: 0; height: 0;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-top: 6px solid ${bg};
            margin: 0 auto;
          "></div>
        </div>`
      }

      // === 排名分级渲染 ===

      // Top 级: 始终显示大标记 (44px + 名称 + 评分 + 事件图标)
      if (rank === 'top') {
        return renderTop(bg, colorInfo)
      }

      // 标准级: zoom < 7 → 圆点; zoom >= 7 → 紧凑评分
      if (rank === 'standard') {
        if (zoom < 7) return renderDot(bg, 16)
        if (zoom < 10) return renderCompact(bg, colorInfo)
        // zoom >= 10: 完整默认态
      }

      // 低优先级: zoom < 10 → 小圆点; zoom >= 10 → 紧凑评分
      if (rank === 'low') {
        if (zoom < 10) return renderDot(bg, 12)
        return renderCompact(bg, colorInfo)
      }

      // 默认态 (standard + zoom >= 10): 圆形评分标记 + 名称标签
      return `<div style="
        position: relative;
        transition: transform 0.3s ease;
        padding: 4px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
      ">
        ${pulse}
        <div style="
          width: 40px; height: 40px; border-radius: 50%;
          background: ${bg};
          color: white; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 14px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
          transition: box-shadow 0.3s ease, transform 0.3s ease;
        ">${getSvgBadge()}${props.score}</div>
        <div style="
          width: 0; height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 5px solid ${bg};
        "></div>
        <div style="
          font-size: 10px;
          color: #374151;
          white-space: nowrap;
          text-align: center;
          margin-top: 2px;
          text-shadow: 0 0 3px white, 0 0 3px white;
          max-width: 80px;
          overflow: hidden;
          text-overflow: ellipsis;
        ">${props.viewpoint.name}</div>
      </div>`
    }

    function getAMap() {
      return AMapSDK || window.AMap
    }

    function playEnterAnimation() {
      if (!marker) return
      const el = marker.getContentElement?.()
      if (!el) return
      gsap.fromTo(el, {
        y: 30,
        scale: 0,
        opacity: 0,
      }, {
        y: 0,
        scale: 1,
        opacity: 1,
        duration: 0.6,
        ease: 'back.out(1.7)',
        delay: props.enterDelay,
      })
    }

    async function createMarker() {
      if (!props.map || !props.viewpoint?.location) return

      const AMap = getAMap()
      if (!AMap) return

      const [gcjLon, gcjLat] = await convertToGCJ02(
        AMap, props.viewpoint.location.lon, props.viewpoint.location.lat
      )

      marker = new AMap.Marker({
        position: [gcjLon, gcjLat],
        content: createContent(),
        offset: new AMap.Pixel(-20, -20),
        title: props.viewpoint.name,
      })

      marker.on('click', () => emit('click', props.viewpoint))
      props.map.add(marker)
      playEnterAnimation()
    }

    function updateMarker() {
      if (!marker || !getAMap()) return
      marker.setContent(createContent())
    }

    function removeMarker() {
      if (marker && props.map) {
        props.map.remove(marker)
        marker = null
      }
    }

    // 监听 map 实例就绪
    watch(() => props.map, (newMap) => {
      if (newMap) {
        removeMarker()
        createMarker()
      }
    })

    // 监听 score / selected / zoom / bestEvent / rank 变化更新样式
    watch(() => [props.score, props.selected, props.zoom, props.bestEvent, props.rank], () => {
      updateMarker()
    })

    // 监听观景台位置变化
    watch(() => props.viewpoint, () => {
      removeMarker()
      createMarker()
    }, { deep: true })

    onMounted(() => {
      if (props.map) {
        createMarker()
      }
    })

    onUnmounted(() => {
      removeMarker()
    })

    return () => null // 不渲染 DOM，标记由 AMap 管理
  },
}
</script>

<style>
/* 全局样式 — 标记动画 (不能 scoped，因为是 AMap DOM) */
@keyframes marker-pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0; }
  100% { transform: scale(1); opacity: 0; }
}

@keyframes marker-bounce {
  0% { transform: scale(1.2) translateY(0); }
  40% { transform: scale(1.2) translateY(-8px); }
  60% { transform: scale(1.2) translateY(-4px); }
  100% { transform: scale(1.2) translateY(0); }
}
</style>
