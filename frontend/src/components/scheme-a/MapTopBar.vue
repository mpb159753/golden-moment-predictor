<template>
  <div class="map-top-bar">
    <!-- 搜索框 -->
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索观景台"
        @input="onSearch"
      />
      <!-- 搜索结果下拉 -->
      <ul v-if="searchResults.length" class="search-results">
        <li
          v-for="vp in searchResults"
          :key="vp.id"
          @click="selectResult(vp)"
        >
          {{ vp.name }}
        </li>
      </ul>
    </div>

    <!-- 事件类型筛选 Chips -->
    <div class="filter-chips">
      <button
        v-for="filter in filterOptions"
        :key="filter.type"
        :class="['chip', { active: activeFilters.includes(filter.type) }]"
        @click="toggleFilter(filter.type)"
        :title="filter.label"
        :aria-label="filter.label"
      >
        {{ filter.icon }}
      </button>
    </div>

    <!-- 日期切换 -->
    <div class="date-picker-wrapper" ref="datePickerRef">
      <button class="date-btn" @click="showDatePicker = !showDatePicker">
        📅 {{ formatDate(selectedDate) }}
      </button>
      <div v-if="showDatePicker" class="date-picker-dropdown">
        <DatePicker
          :model-value="selectedDate"
          :dates="availableDates"
          @update:model-value="onDateSelect"
        />
      </div>
    </div>

    <!-- 线路模式切换 -->
    <button
      :class="['route-btn', { active: routeMode }]"
      @click="toggleRouteMode"
    >
      🛤️
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import DatePicker from '@/components/layout/DatePicker.vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  selectedDate: { type: String, default: '' },
  availableDates: { type: Array, default: () => [] },
  activeFilters: { type: Array, default: () => [] },
})

const emit = defineEmits(['search', 'filter', 'date-change', 'toggle-route'])

const searchQuery = ref('')
const routeMode = ref(false)
const showDatePicker = ref(false)
const datePickerRef = ref(null)

// 点击组件外部关闭日期选择器
function handleClickOutside(e) {
  if (datePickerRef.value && !datePickerRef.value.contains(e.target)) {
    showDatePicker.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))

const filterOptions = [
  { type: 'golden_mountain', icon: '🏔️', label: '日照金山' },
  { type: 'cloud_sea', icon: '☁️', label: '云海' },
  { type: 'stargazing', icon: '⭐', label: '观星' },
  { type: 'frost', icon: '❄️', label: '霜冻' },
]

const searchResults = computed(() => {
  if (!searchQuery.value) return []
  return props.viewpoints.filter(vp =>
    vp.name.includes(searchQuery.value)
  ).slice(0, 5)
})

function selectResult(vp) {
  searchQuery.value = ''
  emit('search', vp.id)
}

function onSearch() {
  // 搜索逻辑由 computed 自动处理
}

function toggleFilter(type) {
  const current = [...props.activeFilters]
  const index = current.indexOf(type)
  if (index >= 0) {
    current.splice(index, 1)
  } else {
    current.push(type)
  }
  emit('filter', current)
}

function toggleRouteMode() {
  routeMode.value = !routeMode.value
  emit('toggle-route', routeMode.value)
}

function formatDate(dateStr) {
  if (!dateStr) return '今天'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function onDateSelect(date) {
  showDatePicker.value = false
  emit('date-change', date)
}
</script>

<style scoped>
.map-top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: var(--bg-overlay);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  /* 防止子元素超出视口宽度，但允许纵向溢出（日期选择器下拉） */
  max-width: 100vw;
  box-sizing: border-box;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 0; /* 允许 flex 子元素收缩 */
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-full);
  padding: 6px 12px;
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  outline: none;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.search-icon {
  margin-right: 6px;
  font-size: var(--text-sm);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-elevated);
  list-style: none;
  padding: 4px 0;
  z-index: 10;
}

.search-results li {
  padding: 8px 16px;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.search-results li:hover {
  background: var(--bg-primary);
}

.filter-chips {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.chip {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
  flex-shrink: 0;
}

.chip.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.date-btn,
.route-btn {
  height: 32px;
  padding: 0 10px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  font-size: var(--text-xs);
  white-space: nowrap;
  transition: all var(--duration-fast);
  flex-shrink: 0;
}

.route-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.date-picker-wrapper {
  position: relative;
  flex-shrink: 0;
}

.date-picker-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: var(--bg-card, #fff);
  border-radius: var(--radius-md, 12px);
  box-shadow: var(--shadow-elevated, 0 8px 24px rgba(0, 0, 0, 0.15));
  padding: 8px;
  z-index: 200;
  min-width: 320px;
}

/* 小屏适配 —— 搜索框缩短、filter chips 隐藏在滚动中 */
@media (max-width: 480px) {
  .map-top-bar {
    gap: 6px;
    padding: 8px 12px;
    padding-top: max(8px, env(safe-area-inset-top));
  }

  .search-box {
    flex: 1 1 80px;
    min-width: 80px;
  }

  .chip {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .date-btn,
  .route-btn {
    height: 28px;
    padding: 0 8px;
    font-size: 11px;
  }

  .date-picker-dropdown {
    right: -40px;
    min-width: 280px;
  }
}
</style>
