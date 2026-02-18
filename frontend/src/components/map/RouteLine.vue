<script>
import { watch, onMounted, onUnmounted } from 'vue'

/**
 * RouteLine — 线路连线组件
 *
 * 使用 AMap Polyline API 连接线路站点。
 * 不渲染自身 DOM，通过 render function 返回 null。
 *
 * 样式:
 * - 常态: 虚线、3px 宽度、蓝色
 * - 高亮: 实线、4px 宽度、加深颜色
 * - 箭头: 按 stops 顺序显示方向
 * - hover: 自动高亮
 */
export default {
  name: 'RouteLine',
  props: {
    stops: { type: Array, default: () => [] },
    highlighted: { type: Boolean, default: false },
    map: { type: Object, default: null },
  },
  setup(props) {
    let polyline = null

    function getStyle() {
      return {
        strokeColor: props.highlighted ? '#2563EB' : '#3B82F6',
        strokeWeight: props.highlighted ? 4 : 3,
        strokeStyle: props.highlighted ? 'solid' : 'dashed',
      }
    }

    function createPolyline() {
      if (!props.map || props.stops.length < 2) return

      const AMap = window.AMap
      if (!AMap) return

      const path = props.stops.map(s => [s.location.lon, s.location.lat])
      const style = getStyle()

      polyline = new AMap.Polyline({
        path,
        strokeColor: style.strokeColor,
        strokeWeight: style.strokeWeight,
        strokeStyle: style.strokeStyle,
        showDir: true,
        lineJoin: 'round',
        lineCap: 'round',
      })

      // hover 时自动高亮
      polyline.on('mouseover', () => {
        if (!props.highlighted) {
          polyline.setOptions({
            strokeColor: '#2563EB',
            strokeWeight: 4,
            strokeStyle: 'solid',
          })
        }
      })

      polyline.on('mouseout', () => {
        if (!props.highlighted) {
          const normal = getStyle()
          polyline.setOptions({
            strokeColor: normal.strokeColor,
            strokeWeight: normal.strokeWeight,
            strokeStyle: normal.strokeStyle,
          })
        }
      })

      props.map.add(polyline)
    }

    function updatePolyline() {
      if (!polyline) return
      const style = getStyle()
      polyline.setOptions({
        strokeColor: style.strokeColor,
        strokeWeight: style.strokeWeight,
        strokeStyle: style.strokeStyle,
      })
    }

    function removePolyline() {
      if (polyline && props.map) {
        props.map.remove(polyline)
        polyline = null
      }
    }

    // 监听 map 就绪
    watch(() => props.map, (newMap) => {
      if (newMap) {
        removePolyline()
        createPolyline()
      }
    })

    // 监听 highlighted 变化
    watch(() => props.highlighted, () => {
      updatePolyline()
    })

    // 监听 stops 变化
    watch(() => props.stops, () => {
      removePolyline()
      createPolyline()
    }, { deep: true })

    onMounted(() => {
      if (props.map) {
        createPolyline()
      }
    })

    onUnmounted(() => {
      removePolyline()
    })

    return () => null // 不渲染 DOM，线路由 AMap 管理
  },
}
</script>
