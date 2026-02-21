# MH2 董妍彩蛋 (Easter Egg) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在搜索框输入「岽岩」时，触发一个专属彩蛋，包括一个「扫码开通 VIP」的搞笑 Modal，以及一个手机端扫码后的「假 VIP 落地页」。

**Architecture:** 在 `MapTopBar.vue` 中拦截搜索词，向父组件发出 `easter-egg` 事件；`HomeView.vue` 控制彩蛋 Modal 的显示；Modal 分两个状态：(1) 扫码开通页 (2) 「不开通」后的漫画+打油诗页。`/easter-egg/vip` 路由对应手机端扫码后的落地页，同样是漫画+打油诗形式。

**Tech Stack:** Vue 3 Composition API, Vue Router 4, `qrcode` npm 包（动态生成二维码）

---

## 背景与素材

### 漫画图片路径（已生成）
- **电脑端弹窗漫画**（不开通后展示）：`frontend/src/assets/easter-egg/comic-no-money.png`
  - 场景：卡通人物站在雪山前翻出空口袋，旁边酷炫师傅戴墨镜竖大拇指
- **手机端落地页漫画**（扫码后展示）：`frontend/src/assets/easter-egg/comic-face-scan.png`
  - 场景：卡通人物开心抱着显示「$0.00」的屏幕，旁边师傅无奈叉手

### 打油诗文案

**电脑端（不开通后弹出）：**
```
会员特权千般好，奈何兜里铜板少。
转身抱紧师傅腿，刷脸白嫖没烦恼！
```

**手机端扫码落地页：**
```
扫码以为要掏钱，谁知是个假会员。
一路畅通去刷脸，白嫖到底不花钱！
```

---

## Task 1: 安装 qrcode 依赖

**Files:**
- Modify: `frontend/package.json`

**Step 1: 安装依赖**

```bash
cd frontend && npm install qrcode
```

Expected output: `added 1 package, ...`

**Step 2: Commit**
```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(easter-egg): add qrcode dependency"
```

---

## Task 2: 创建 EasterEggModal 组件

**Files:**
- Create: `frontend/src/components/easter-egg/EasterEggModal.vue`

**Step 1: 创建组件文件**

```vue
<!-- frontend/src/components/easter-egg/EasterEggModal.vue -->
<template>
  <Teleport to="body">
    <div v-if="show" class="egg-overlay" @click.self="close">
      <div class="egg-modal">

        <!-- 关闭按钮 -->
        <button class="egg-close-btn" @click="close">✕</button>

        <!-- 状态1: 扫码开通 VIP -->
        <div v-if="phase === 'qrcode'" class="egg-phase egg-qrcode-phase">
          <div class="egg-badge">👑 至尊 VIP</div>
          <h2 class="egg-title">发现董妍专属隐藏通道</h2>
          <p class="egg-subtitle">扫码开通至尊 VIP 会员，解锁隐藏观景台！</p>
          <div class="egg-qr-wrapper">
            <canvas ref="qrCanvas" class="egg-qr-canvas" />
            <div class="egg-qr-hint">👆 扫我 解锁董妍</div>
          </div>
          <button class="egg-skip-btn" @click="phase = 'comic'">
            不开通（太贵了）
          </button>
        </div>

        <!-- 状态2: 漫画 + 打油诗 -->
        <div v-else class="egg-phase egg-comic-phase">
          <img :src="comicNoMoney" alt="穷人看山" class="egg-comic-img" />
          <div class="egg-poem">
            <p>会员特权千般好，奈何兜里铜板少。</p>
            <p>转身抱紧师傅腿，刷脸白嫖没烦恼！</p>
          </div>
          <button class="egg-done-btn" @click="close">朕知道了 👍</button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import QRCode from 'qrcode'
import comicNoMoney from '@/assets/easter-egg/comic-no-money.png'

const props = defineProps({
  show: { type: Boolean, default: false }
})
const emit = defineEmits(['close'])

const phase = ref('qrcode')
const qrCanvas = ref(null)

watch(() => props.show, async (val) => {
  if (val) {
    phase.value = 'qrcode'
    await nextTick()
    generateQR()
  }
})

async function generateQR() {
  if (!qrCanvas.value) return
  const url = `${window.location.origin}/easter-egg/vip`
  await QRCode.toCanvas(qrCanvas.value, url, {
    width: 180,
    margin: 2,
    color: { dark: '#1a1a2e', light: '#fffdf0' }
  })
}

function close() {
  emit('close')
}
</script>

<style scoped>
.egg-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
  animation: egg-fade-in 0.25s ease;
}

@keyframes egg-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.egg-modal {
  position: relative;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 32px 28px;
  max-width: 360px;
  width: 100%;
  color: white;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 215, 0, 0.1);
  animation: egg-slide-up 0.3s ease;
}

@keyframes egg-slide-up {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.egg-close-btn {
  position: absolute;
  top: 14px;
  right: 16px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.egg-close-btn:hover { background: rgba(255, 255, 255, 0.2); color: white; }

.egg-badge {
  display: inline-block;
  background: linear-gradient(90deg, #f7971e, #ffd200);
  color: #1a1a2e;
  font-weight: 700;
  font-size: 12px;
  padding: 4px 14px;
  border-radius: 999px;
  margin-bottom: 12px;
  letter-spacing: 1px;
}

.egg-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 8px;
  background: linear-gradient(90deg, #ffd200, #f7971e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.egg-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0 0 20px;
}

.egg-qr-wrapper {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  display: inline-block;
}

.egg-qr-canvas {
  display: block;
  border-radius: 8px;
}

.egg-qr-hint {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
}

.egg-skip-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  padding: 10px 24px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}
.egg-skip-btn:hover { background: rgba(255, 255, 255, 0.15); color: white; }

/* 漫画状态 */
.egg-comic-img {
  width: 100%;
  max-width: 240px;
  border-radius: 12px;
  margin-bottom: 16px;
}

.egg-poem {
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
}
.egg-poem p {
  margin: 4px 0;
  font-size: 15px;
  line-height: 1.8;
  color: rgba(255, 215, 0, 0.9);
  letter-spacing: 1px;
}

.egg-done-btn {
  background: linear-gradient(90deg, #f7971e, #ffd200);
  border: none;
  color: #1a1a2e;
  font-size: 14px;
  font-weight: 700;
  padding: 12px 32px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}
.egg-done-btn:hover { transform: scale(1.03); box-shadow: 0 4px 16px rgba(255, 210, 0, 0.4); }
</style>
```

**Step 2: 验证组件可以正常 import（不需要运行，visual check 即可）**

**Step 3: Commit**
```bash
git add frontend/src/components/easter-egg/EasterEggModal.vue frontend/src/assets/easter-egg/
git commit -m "feat(easter-egg): add EasterEggModal component with QR code & comic"
```

---

## Task 3: 修改 MapTopBar 拦截「岽岩」关键词

**Files:**
- Modify: `frontend/src/components/scheme-a/MapTopBar.vue`

**Step 1: 在 `emit` 声明中新增 `'easter-egg'` 事件**

当前代码（`MapTopBar.vue` 第 78 行附近）：
```js
const emit = defineEmits(['search', 'filter', 'date-change', 'toggle-route'])
```
改为：
```js
const emit = defineEmits(['search', 'filter', 'date-change', 'toggle-route', 'easter-egg'])
```

**Step 2: 修改 `onSearch` 函数，在输入「岽岩」时触发彩蛋**

当前代码（第 103 行附近）：
```js
function onSearch() {
  // 搜索逻辑由 computed 自动处理
}
```
改为：
```js
function onSearch() {
  if (searchQuery.value.trim() === '岽岩') {
    searchQuery.value = ''
    emit('easter-egg')
  }
}
```

**Step 3: Commit**
```bash
git add frontend/src/components/scheme-a/MapTopBar.vue
git commit -m "feat(easter-egg): intercept '岽岩' search keyword to trigger easter egg"
```

---

## Task 4: 在 HomeView.vue 中集成弹窗

**Files:**
- Modify: `frontend/src/views/HomeView.vue`

**Step 1: 在 imports 部分（第 181 行附近）新增 EasterEggModal 的引入**

在其他组件 import 之后新增：
```js
import EasterEggModal from '@/components/easter-egg/EasterEggModal.vue'
```

**Step 2: 在 script setup 中（`ref` 定义区域）新增控制变量**

```js
const showEasterEgg = ref(false)
```

**Step 3: 在 template 里的 `<MapTopBar>` 组件上新增事件监听**

找到 `<MapTopBar>` 组件（约第 35 行），在已有事件绑定中追加 `@easter-egg`：
```html
<MapTopBar
  ...
  @toggle-route="onToggleRoute"
  @easter-egg="showEasterEgg = true"
/>
```

**Step 4: 在 template 末尾（`</div>` 闭合标签前）新增 Modal 组件**

在 `<!-- GMP Logo 水印 -->` 之后，`</div>` 之前追加：
```html
<!-- 董妍彩蛋 -->
<EasterEggModal
  :show="showEasterEgg"
  @close="showEasterEgg = false"
/>
```

**Step 5: 手动验证（本地运行）**
```bash
cd frontend && npm run dev
```
- 浏览器打开后，在搜索框输入「岽岩」
- 期望：弹出黑金风 VIP 弹窗，显示二维码
- 期望：点击「不开通」后，切换为漫画+打油诗
- 期望：点击「朕知道了」后，弹窗关闭

**Step 6: Commit**
```bash
git add frontend/src/views/HomeView.vue
git commit -m "feat(easter-egg): wire EasterEggModal into HomeView"
```

---

## Task 5: 创建手机端 VIP 落地页

**Files:**
- Create: `frontend/src/views/EasterEggVip.vue`

**Step 1: 创建页面组件**

```vue
<!-- frontend/src/views/EasterEggVip.vue -->
<template>
  <div class="vip-page">
    <div class="vip-card">
      <div class="vip-top-badge">👑 懂妍专属至尊 VIP</div>

      <div class="vip-loading" v-if="phase === 'loading'">
        <div class="vip-spinner"></div>
        <p class="vip-loading-text">正在为您计算开通费用…</p>
      </div>

      <div class="vip-reveal" v-else>
        <img :src="comicFaceScan" alt="刷脸白嫖" class="vip-comic-img" />
        <div class="vip-poem">
          <p>扫码以为要掏钱，谁知是个假会员。</p>
          <p>一路畅通去刷脸，白嫖到底不花钱！</p>
        </div>
        <button class="vip-back-btn" @click="router.push('/')">
          原来如此，打入内部 🎉
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import comicFaceScan from '@/assets/easter-egg/comic-face-scan.png'

const router = useRouter()
const phase = ref('loading')

onMounted(() => {
  // 模拟「计算费用」动画，1.5s 后揭晓
  setTimeout(() => {
    phase.value = 'reveal'
  }, 1500)
})
</script>

<style scoped>
.vip-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 24px;
}

.vip-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 24px;
  padding: 36px 28px;
  max-width: 380px;
  width: 100%;
  text-align: center;
  color: white;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.vip-top-badge {
  display: inline-block;
  background: linear-gradient(90deg, #f7971e, #ffd200);
  color: #1a1a2e;
  font-weight: 700;
  font-size: 13px;
  padding: 6px 20px;
  border-radius: 999px;
  margin-bottom: 28px;
  letter-spacing: 1px;
}

/* 加载状态 */
.vip-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.vip-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255, 215, 0, 0.2);
  border-top-color: #ffd200;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.vip-loading-text {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

/* 揭晓状态 */
.vip-reveal {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.vip-comic-img {
  width: 100%;
  max-width: 260px;
  border-radius: 14px;
  margin-bottom: 20px;
}

.vip-poem {
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 24px;
  width: 100%;
}

.vip-poem p {
  margin: 5px 0;
  font-size: 15px;
  line-height: 1.8;
  color: rgba(255, 215, 0, 0.9);
  letter-spacing: 1px;
}

.vip-back-btn {
  background: linear-gradient(90deg, #f7971e, #ffd200);
  border: none;
  color: #1a1a2e;
  font-size: 15px;
  font-weight: 700;
  padding: 14px 32px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.vip-back-btn:hover {
  transform: scale(1.03);
  box-shadow: 0 4px 20px rgba(255, 210, 0, 0.4);
}
</style>
```

**Step 2: Commit**
```bash
git add frontend/src/views/EasterEggVip.vue
git commit -m "feat(easter-egg): add VIP landing page for QR code scan"
```

---

## Task 6: 注册路由

**Files:**
- Modify: `frontend/src/router/index.js`

**Step 1: 在 routes 数组末尾追加新路由**

在 `/route/:id` 路由之后新增：
```js
{
    path: '/easter-egg/vip',
    name: 'easter-egg-vip',
    component: () => import('@/views/EasterEggVip.vue'),
},
```

**Step 2: 手动验证**

本地 dev server 运行中，直接访问 `http://localhost:5173/easter-egg/vip`：
- 期望：出现 1.5s 加载动画后揭晓漫画页面
- 期望：点击「原来如此，打入内部」跳回首页

**Step 3: Commit**
```bash
git add frontend/src/router/index.js
git commit -m "feat(easter-egg): register /easter-egg/vip route"
```

---

## 完成检查清单

- [ ] `qrcode` 已安装（`npm list qrcode` 能看到版本）
- [ ] 搜索框输入「岽岩」→ 弹出黑金 VIP 弹窗，二维码正确生成
- [ ] 点击「不开通」→ 切换为漫画 + 打油诗，点「朕知道了」关闭
- [ ] 手机扫码（或浏览器访问 `/easter-egg/vip`）→ 加载动画 → 揭晓漫画 + 打油诗
- [ ] 点击「原来如此，打入内部」→ 跳回首页
- [ ] 不影响正常搜索其他观景台名称
