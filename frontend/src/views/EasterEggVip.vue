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
