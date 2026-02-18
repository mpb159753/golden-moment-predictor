<template>
  <div class="amap-wrapper">
    <div
      ref="containerRef"
      :id="containerId"
      class="amap-container"
      :style="{ height }"
    />
    <!-- 渲染无 DOM 子组件 (ViewpointMarker, RouteLine 等) -->
    <slot />
  </div>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted } from 'vue'
import { useAMap } from '@/composables/useAMap'

const props = defineProps({
  mapOptions: { type: Object, default: () => ({}) },
  height: { type: String, default: '100%' },
})

const emit = defineEmits(['ready'])

const containerId = `amap-${Date.now()}`
const containerRef = ref(null)
const { init, destroy, map, getAMapModule } = useAMap(containerId)
const amapSdkRef = ref(null)

// provide must be called in setup scope (synchronous)
provide('AMapSDK', amapSdkRef)

onMounted(async () => {
  const result = await init(props.mapOptions)
  if (result.success) {
    amapSdkRef.value = getAMapModule()
    emit('ready', map())
  }
})

onUnmounted(() => {
  destroy()
})

// 暴露地图操作方法给父组件
defineExpose({
  getMap: () => map(),
})
</script>

<style scoped>
.amap-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.amap-container {
  width: 100%;
  min-height: 200px;
}
</style>
