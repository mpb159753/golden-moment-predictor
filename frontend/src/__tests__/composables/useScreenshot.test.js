import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock html2canvas
const mockCanvas = {
    toDataURL: vi.fn(() => 'data:image/png;base64,mockdata'),
}
vi.mock('html2canvas', () => ({
    default: vi.fn(() => Promise.resolve(mockCanvas)),
}))

import { useScreenshot } from '@/composables/useScreenshot'

describe('useScreenshot', () => {
    const { capture, captureToCanvas } = useScreenshot()
    let mockElement

    beforeEach(() => {
        vi.clearAllMocks()
        mockElement = document.createElement('div')
    })

    describe('capture', () => {
        it('throws when element is null', async () => {
            await expect(capture(null)).rejects.toThrow('Screenshot target element is required')
        })

        it('calls html2canvas with correct default options', async () => {
            const html2canvas = (await import('html2canvas')).default

            await capture(mockElement)

            expect(html2canvas).toHaveBeenCalledWith(mockElement, {
                scale: 2,
                backgroundColor: null,
                useCORS: true,
            })
        })

        it('merges custom options into html2canvas call', async () => {
            const html2canvas = (await import('html2canvas')).default

            await capture(mockElement, 'test.png', { scale: 3, logging: false })

            expect(html2canvas).toHaveBeenCalledWith(mockElement, {
                scale: 3,
                backgroundColor: null,
                useCORS: true,
                logging: false,
            })
        })

        it('creates download link with correct filename', async () => {
            const clickSpy = vi.fn()
            const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValueOnce({
                set download(val) { this._download = val },
                get download() { return this._download },
                set href(val) { this._href = val },
                get href() { return this._href },
                click: clickSpy,
            })

            await capture(mockElement, 'my-screenshot.png')

            expect(clickSpy).toHaveBeenCalled()
            createElementSpy.mockRestore()
        })

        it('returns the canvas', async () => {
            const result = await capture(mockElement)
            expect(result).toBe(mockCanvas)
        })
    })

    describe('captureToCanvas', () => {
        it('calls html2canvas with default options', async () => {
            const html2canvas = (await import('html2canvas')).default

            const result = await captureToCanvas(mockElement)

            expect(html2canvas).toHaveBeenCalledWith(mockElement, {
                scale: 2,
                backgroundColor: null,
                useCORS: true,
            })
            expect(result).toBe(mockCanvas)
        })

        it('merges custom options', async () => {
            const html2canvas = (await import('html2canvas')).default

            await captureToCanvas(mockElement, { backgroundColor: '#fff' })

            expect(html2canvas).toHaveBeenCalledWith(mockElement, {
                scale: 2,
                backgroundColor: '#fff',
                useCORS: true,
            })
        })
    })
})
