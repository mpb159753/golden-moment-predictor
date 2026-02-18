<template>
  <div
    ref="sheetRef"
    class="bottom-sheet"
    :class="[`state-${currentState}`, { 'desktop-mode': desktopMode }]"
    :style="{ height: isDragging ? `${dragHeight}px` : undefined }"
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
      <transition name="fade" mode="out-in">
        <!-- 收起态 -->
        <div v-if="currentState === 'collapsed'" key="collapsed">
          <slot name="collapsed" />
        </div>

        <!-- 半展态 -->
        <div v-else-if="currentState === 'half'" key="half">
          <slot name="half" />
        </div>

        <!-- 全展态 -->
        <div v-else key="full" class="full-scroll">
          <slot name="full" />
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  state: { type: String, default: 'collapsed' },
  desktopMode: { type: Boolean, default: false },
})

const emit = defineEmits(['state-change'])

const sheetRef = ref(null)
const contentRef = ref(null)

// 状态管理
const currentState = ref(props.state)
watch(() => props.state, (val) => { currentState.value = val })

// 高度映射
const stateHeights = {
  collapsed: 0.20,  // 20% 视窗高度
  half: 0.45,       // 45%
  full: 0.90,       // 90%
}

// 拖拽状态
const isDragging = ref(false)
const dragHeight = ref(0)
let startY = 0
let startHeight = 0

function getViewportHeight() {
  return window.innerHeight
}

function getCurrentHeight() {
  return stateHeights[currentState.value] * getViewportHeight()
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

  const targetHeight = stateHeights[targetState] * getViewportHeight()

  gsap.to(sheetRef.value, {
    height: targetHeight,
    duration: 0.5,
    ease: 'elastic.out(1, 0.75)',
    onComplete: () => {
      // 动画完成后清除 GSAP 设置的 inline height，
      // 让 CSS class 接管高度控制
      if (sheetRef.value) {
        sheetRef.value.style.height = ''
      }
      currentState.value = targetState
      emit('state-change', targetState)
    }
  })
}

// 清理
onUnmounted(() => {
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
  /* height transition handled by GSAP */
  overflow: hidden;
  will-change: height;
}

/* 三级高度 */
.state-collapsed { height: 20vh; }
.state-half      { height: 45vh; }
.state-full      { height: 90vh; }

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

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast, 200ms) ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
