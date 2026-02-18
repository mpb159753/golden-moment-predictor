<template>
  <div class="viewpoint-detail">
    <h1>观景台详情: {{ id }}</h1>
    <p v-if="date">日期: {{ date }}</p>
    <p>详情页组件将在 M25 中实现</p>
  </div>
</template>

<script setup>
const props = defineProps({
  id: String,
  date: { type: String, default: null },
})
</script>
