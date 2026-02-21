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
