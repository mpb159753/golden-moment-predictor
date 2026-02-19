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
    enterDelay: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    map: { type: Object, default: null },
  },
  emits: ['click'],
  setup(props, { emit }) {
    let marker = null
    const AMapSDK = inject('AMapSDK', null)

    const { getScoreColor } = useScoreColor()

    function getSvgBadge() {
      if (!props.bestEvent) return ''
      return getEventSvgBadge(props.bestEvent, 16, 'white')
    }

    function createContent() {
      const colorInfo = getScoreColor(props.score)
      const bg = colorInfo.gradient || colorInfo.color
      const isZoomMini = props.zoom < 9 && !props.selected

      // 缩略态: 仅圆点 (zoom < 9 且未选中)
      if (isZoomMini) {
        return `<div class="marker-dot" style="
          width: 12px; height: 12px; border-radius: 50%;
          background: ${bg};
          box-shadow: 0 1px 4px rgba(0,0,0,0.2);
          cursor: pointer;
        "></div>`
      }

      const pulse = props.score >= 95
        ? `<div style="
            position: absolute; top: -4px; left: -4px;
            width: 48px; height: 48px; border-radius: 50%;
            border: 2px solid ${colorInfo.color};
            animation: marker-pulse 2s infinite;
            pointer-events: none;
          "></div>`
        : ''

      // 选中态: 展开名称 + 评分 + 弹跳动画 + 脉冲光圈
      if (props.selected) {
        return `<div style="
          position: relative;
          transform: scale(1.2);
          animation: marker-bounce 0.4s ease-out;
          transition: transform 0.3s ease;
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

      // 默认态: 圆形评分标记
      return `<div style="
        position: relative;
        transition: transform 0.3s ease;
      ">
        ${pulse}
        <div style="
          width: 40px; height: 40px; border-radius: 50%;
          background: ${bg};
          color: white; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 14px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
          cursor: pointer;
          transition: box-shadow 0.3s ease, transform 0.3s ease;
        ">${getSvgBadge()}${props.score}</div>
        <div style="
          width: 0; height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 5px solid ${bg};
          margin: 0 auto;
        "></div>
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

    // 监听 score / selected / zoom / bestEvent 变化更新样式
    watch(() => [props.score, props.selected, props.zoom, props.bestEvent], () => {
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
