import { chromium } from 'playwright'
import { createServer } from 'http'
import { readFileSync, mkdirSync, writeFileSync } from 'fs'
import { join, resolve } from 'path'
import handler from 'serve-handler'
import { buildSummary } from './build-summary.mjs'

// 重导出供外部使用
export { buildSummary }

const GROUP_KEYS = ['gongga', 'siguniang', 'yala', 'genie', 'yading', 'lixiao', 'other']

const SCREENSHOT_CONFIGS = [
    { days: 3, dir: '3day' },
    { days: 7, dir: 'week' },
]

async function main() {
    const distDir = resolve(import.meta.dirname, '../dist')
    const outputBase = join(distDir, 'data', 'posters')

    // 1. 启动本地静态服务器
    const server = createServer((req, res) => handler(req, res, {
        public: distDir,
        rewrites: [{ source: '**', destination: '/index.html' }],
    }))
    await new Promise(r => server.listen(0, '127.0.0.1', r))
    const port = server.address().port
    const baseUrl = `http://127.0.0.1:${port}`
    console.log(`[generate-posters] 静态服务器启动: ${baseUrl}`)

    try {
        // 2. 启动 Playwright
        const browser = await chromium.launch()
        const context = await browser.newContext({ deviceScaleFactor: 2 })

        for (const config of SCREENSHOT_CONFIGS) {
            const outDir = join(outputBase, config.dir)
            mkdirSync(outDir, { recursive: true })

            const page = await context.newPage()
            const url = `${baseUrl}/ops/poster?days=${config.days}`
            console.log(`[generate-posters] 打开 ${url}`)
            await page.goto(url, { waitUntil: 'networkidle' })

            // 等待字体加载和内容渲染
            await page.evaluate(() => document.fonts.ready)
            await page.waitForSelector('.poster-content', { state: 'visible' })

            // 逐个 .group-section 截图
            const sections = await page.$$('.group-section')
            console.log(`[generate-posters] ${config.dir}: 找到 ${sections.length} 个分组`)

            for (let i = 0; i < sections.length; i++) {
                const key = GROUP_KEYS[i] || `group_${i}`
                const filePath = join(outDir, `${key}.png`)
                await sections[i].screenshot({ path: filePath })
                console.log(`[generate-posters] 已保存 ${config.dir}/${key}.png`)
            }

            await page.close()
        }

        await browser.close()

        // 4. 生成摘要 JSON
        const posterJsonPath = join(distDir, 'data', 'poster.json')
        const posterData = JSON.parse(readFileSync(posterJsonPath, 'utf-8'))

        for (const config of SCREENSHOT_CONFIGS) {
            const summary = buildSummary(posterData, config.days, 1) // dayOffset=1 从明天开始
            const jsonPath = join(outputBase, `summary_${config.dir}.json`)
            writeFileSync(jsonPath, JSON.stringify(summary, null, 2))
            console.log(`[generate-posters] 已保存 summary_${config.dir}.json`)
        }

        console.log('[generate-posters] 完成!')
    } finally {
        server.close()
    }
}

// 仅主脚本运行时执行
const isMain = process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)
if (isMain) main().catch(err => { console.error(err); process.exit(1) })
