<template>
  <div
    ref="sheetRef"
    class="bottom-sheet"
    :class="[`state-${currentState}`, { 'desktop-mode': desktopMode }]"
    :style="sheetStyle"
  >
    <!-- 拖拽手柄 -->
    <div
      class="sheet-handle"
      @touchstart.passive="onTouchStart"
      @touchmove.passive="onTouchMove"
      @touchend="onTouchEnd"
      @mousedown="onMouseDown"
    >
      <div class="handle-bar" />
    </div>

    <!-- 内容区域 (可滚动) -->
    <div ref="contentRef" class="sheet-content">
      <!-- 收起态 -->
      <div v-show="currentState === 'collapsed'" ref="collapsedSlotRef">
        <slot name="collapsed" />
      </div>

      <!-- 半展态 -->
      <div v-show="currentState === 'half'" ref="halfSlotRef">
        <slot name="half" />
      </div>

      <!-- 全展态 -->
      <div v-show="currentState === 'full'" class="full-scroll">
        <slot name="full" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  state: { type: String, default: 'collapsed' },
  desktopMode: { type: Boolean, default: false },
})

const emit = defineEmits(['state-change'])

const sheetRef = ref(null)
const contentRef = ref(null)
const collapsedSlotRef = ref(null)
const halfSlotRef = ref(null)

// 状态管理
const currentState = ref(props.state)
watch(() => props.state, (val) => { currentState.value = val })

// 动态高度常量
const HANDLE_HEIGHT = 32 // handle 区域高度（含 padding）
const MAX_RATIOS = {
  collapsed: 0.40,  // 最大不超过 40vh（容纳5个推荐项）
  half: 0.55,       // 最大不超过 55vh
  full: 0.90,       // 90%
}

// 记录测量到的内容高度
const measuredHeights = ref({ collapsed: 0, half: 0, full: 0 })

function getViewportHeight() {
  return window.innerHeight
}

// 测量某个状态的 slot 内容实际高度
function measureSlotHeight(state) {
  let slotEl = null
  if (state === 'collapsed') slotEl = collapsedSlotRef.value
  else if (state === 'half') slotEl = halfSlotRef.value
  if (!slotEl) return 0
  return slotEl.scrollHeight
}

// 获取某个状态的目标高度
function getTargetHeight(state) {
  if (state === 'full') {
    return MAX_RATIOS.full * getViewportHeight()
  }
  const contentH = measuredHeights.value[state] + HANDLE_HEIGHT
  const maxH = MAX_RATIOS[state] * getViewportHeight()
  return Math.min(contentH, maxH)
}

// 暴露给父组件的当前高度
const currentHeight = computed(() => getTargetHeight(currentState.value))

// 测量并更新高度
async function remeasure() {
  await nextTick()
  measuredHeights.value = {
    collapsed: measureSlotHeight('collapsed'),
    half: measureSlotHeight('half'),
    full: MAX_RATIOS.full * getViewportHeight(),
  }
}

// 当 state 变化时重新测量
watch(currentState, () => {
  remeasure()
})

// 初始测量
let observer = null
onMounted(() => {
  remeasure()

  // 监听 slot 内容 DOM 变化，自动重新测量高度
  // 解决异步数据加载后内容变化但高度不更新的问题
  if (contentRef.value) {
    observer = new MutationObserver(() => {
      remeasure()
    })
    observer.observe(contentRef.value, {
      childList: true,
      subtree: true,
      characterData: true,
    })
  }
})

// 计算样式
const sheetStyle = computed(() => {
  if (isDragging.value) {
    return { height: `${dragHeight.value}px` }
  }
  // full 状态使用 CSS class 控制
  if (currentState.value === 'full') {
    return {}
  }
  const h = getTargetHeight(currentState.value)
  return { height: `${h}px` }
})

// 拖拽状态
const isDragging = ref(false)
const dragHeight = ref(0)
let startY = 0
let startHeight = 0

function getCurrentHeight() {
  return getTargetHeight(currentState.value)
}

// Touch 事件
function onTouchStart(e) {
  startDrag(e.touches[0].clientY)
}

function onTouchMove(e) {
  moveDrag(e.touches[0].clientY)
}

function onTouchEnd() {
  endDrag()
}

// Mouse 事件 (桌面端)
function onMouseDown(e) {
  startDrag(e.clientY)
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e) {
  moveDrag(e.clientY)
}

function onMouseUp() {
  endDrag()
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

function startDrag(y) {
  isDragging.value = true
  startY = y
  startHeight = getCurrentHeight()
}

function moveDrag(y) {
  if (!isDragging.value) return
  const delta = startY - y  // 向上拖为正
  const newHeight = Math.max(0, Math.min(
    getViewportHeight() * 0.95,
    startHeight + delta
  ))
  dragHeight.value = newHeight
}

function endDrag() {
  if (!isDragging.value) return

  // 先记录当前拖拽高度，再关闭拖拽状态
  const currentDragHeight = dragHeight.value
  isDragging.value = false

  // 立即将当前高度固定到 DOM，防止 Vue 移除 inline style 后
  // 高度闪回 CSS class 定义的旧状态高度
  if (sheetRef.value) {
    sheetRef.value.style.height = `${currentDragHeight}px`
  }

  const vh = getViewportHeight()
  const ratio = currentDragHeight / vh

  // 使用吸附阈值确定目标状态
  let targetState
  if (ratio < 0.30) {
    targetState = 'collapsed'
  } else if (ratio < 0.65) {
    targetState = 'half'
  } else {
    targetState = 'full'
  }

  animateToState(targetState)
}

function animateToState(targetState) {
  if (!sheetRef.value) return

  const targetHeight = getTargetHeight(targetState)

  gsap.to(sheetRef.value, {
    height: targetHeight,
    duration: 0.5,
    ease: 'elastic.out(1, 0.75)',
    onComplete: () => {
      // 动画完成后清除 GSAP 设置的 inline height，
      // 让 computed style 接管高度控制
      if (sheetRef.value) {
        sheetRef.value.style.height = ''
      }
      currentState.value = targetState
      emit('state-change', targetState)
    }
  })
}

// 为父组件提供重新测量的方法（当 slot 内容变化时调用）
defineExpose({ currentHeight, remeasure })

// 清理
onUnmounted(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
})
</script>

<style scoped>
.bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 200;
  background: var(--bg-card, #fff);
  border-radius: var(--radius-lg, 20px) var(--radius-lg, 20px) 0 0;
  box-shadow: var(--shadow-float, 0 16px 48px rgba(0, 0, 0, 0.12));
  overflow: hidden;
  will-change: height;
  /* 默认过渡（非拖拽时的 state 切换） */
  transition: height 0.3s ease;
}

/* full 状态使用固定高度 */
.state-full { height: 90vh; }

/* 拖拽手柄 */
.sheet-handle {
  display: flex;
  justify-content: center;
  padding: 12px 0 8px;
  cursor: grab;
  touch-action: none;
}

.sheet-handle:active {
  cursor: grabbing;
}

.handle-bar {
  width: 40px;
  height: 4px;
  border-radius: var(--radius-full, 9999px);
  background: var(--text-muted, #94A3B8);
  opacity: 0.5;
}

/* 内容区域 */
.sheet-content {
  height: calc(100% - 32px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.full-scroll {
  padding-bottom: env(safe-area-inset-bottom);
}

/* 桌面模式: 右侧面板 */
.desktop-mode {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: auto;
  width: 380px;
  height: 100vh !important;
  border-radius: var(--radius-lg, 20px) 0 0 var(--radius-lg, 20px);
}

.desktop-mode .sheet-handle {
  display: none;
}

.desktop-mode .sheet-content {
  height: 100%;
}

/* 安全距离 */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .bottom-sheet {
    padding-bottom: env(safe-area-inset-bottom);
  }
}
</style>
