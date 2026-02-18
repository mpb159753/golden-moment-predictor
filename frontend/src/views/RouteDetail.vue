<template>
  <div class="route-detail">
    <h1>线路详情: {{ id }}</h1>
    <p>线路详情页组件将在 M25 中实现</p>
  </div>
</template>

<script setup>
const props = defineProps({
  id: String,
})
</script>
