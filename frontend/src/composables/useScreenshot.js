import html2canvas from 'html2canvas'

/**
 * 截图导出 composable。
 *
 * 策略 (来自设计文档 10-frontend-common.md §10.0.6):
 * - 使用 html2canvas 进行 DOM 区域截图
 * - 2x 分辨率 (Retina 友好)
 * - 支持透明背景 (方案 C 卡片流需要)
 *
 * 各组件通过 ref="screenshotArea" 标记可截图区域。
 */
export function useScreenshot() {
    /**
     * 截取指定 DOM 元素为图片并下载
     * @param {HTMLElement} element - 要截取的 DOM 元素
     * @param {string} filename - 下载文件名
     * @param {Object} options - html2canvas 额外选项
     */
    async function capture(element, filename = 'gmp-prediction.png', options = {}) {
        if (!element) {
            throw new Error('Screenshot target element is required')
        }

        const canvas = await html2canvas(element, {
            scale: 2,
            backgroundColor: null,
            useCORS: true,
            ...options,
        })

        const link = document.createElement('a')
        link.download = filename
        link.href = canvas.toDataURL('image/png')
        link.click()

        return canvas
    }

    /**
     * 截取并返回 canvas (不自动下载，供 ShareCard 合成使用)
     * @param {HTMLElement} element
     * @param {Object} options
     * @returns {Promise<HTMLCanvasElement>}
     */
    async function captureToCanvas(element, options = {}) {
        return html2canvas(element, {
            scale: 2,
            backgroundColor: null,
            useCORS: true,
            ...options,
        })
    }

    return { capture, captureToCanvas }
}
