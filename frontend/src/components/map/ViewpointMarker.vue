<script>
import { watch, onMounted, onUnmounted, inject } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

/**
 * ViewpointMarker — 地图评分标记组件
 *
 * 使用 AMap Marker API 创建自定义 DOM 标记。
 * 不渲染自身 DOM，通过 render function 返回 null。
 * 依赖父组件通过 provide 注入 useAMap 实例。
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
    selected: { type: Boolean, default: false },
    map: { type: Object, default: null },
  },
  emits: ['click'],
  setup(props, { emit }) {
    let marker = null
    let AMapRef = null

    const { getScoreColor } = useScoreColor()

    function createContent() {
      const colorInfo = getScoreColor(props.score)
      const bg = colorInfo.gradient || colorInfo.color
      const scale = props.selected ? 'transform: scale(1.2);' : ''
      const shadow = props.selected
        ? 'box-shadow: 0 4px 16px rgba(0,0,0,0.35);'
        : 'box-shadow: 0 2px 8px rgba(0,0,0,0.2);'
      const pulse = props.score >= 95
        ? `<div style="
            position: absolute; top: -4px; left: -4px;
            width: 48px; height: 48px; border-radius: 50%;
            border: 2px solid ${colorInfo.color};
            animation: marker-pulse 2s infinite;
            pointer-events: none;
          "></div>`
        : ''
      const bounce = props.selected ? 'animation: marker-bounce 0.4s ease-out;' : ''

      return `<div style="
        position: relative;
        ${scale} ${bounce}
        transition: transform 0.3s ease;
      ">
        ${pulse}
        <div style="
          width: 40px; height: 40px; border-radius: 50%;
          background: ${bg};
          color: white; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 14px;
          ${shadow}
          cursor: pointer;
          transition: box-shadow 0.3s ease, transform 0.3s ease;
        ">${props.score}</div>
      </div>`
    }

    function createMarker() {
      if (!props.map || !props.viewpoint?.location) return

      // 获取 AMap 构造函数 — 通过 map 实例上下文
      const AMap = window.AMap
      if (!AMap) return

      AMapRef = AMap

      marker = new AMap.Marker({
        position: [props.viewpoint.location.lon, props.viewpoint.location.lat],
        content: createContent(),
        offset: new AMap.Pixel(-20, -20),
        title: props.viewpoint.name,
      })

      marker.on('click', () => emit('click', props.viewpoint))
      props.map.add(marker)
    }

    function updateMarker() {
      if (!marker || !AMapRef) return
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

    // 监听 score / selected 变化更新样式
    watch(() => [props.score, props.selected], () => {
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
