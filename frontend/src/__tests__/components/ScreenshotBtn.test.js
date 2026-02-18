import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock useScreenshot composable
const mockCapture = vi.fn(() => Promise.resolve())
vi.mock('@/composables/useScreenshot', () => ({
    useScreenshot: () => ({
        capture: mockCapture,
        captureToCanvas: vi.fn(),
    }),
}))

import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'

describe('ScreenshotBtn', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders button with default screenshot text', () => {
        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#test' },
        })
        expect(wrapper.find('.screenshot-btn').exists()).toBe(true)
        expect(wrapper.text()).toContain('截图')
    })

    it('renders camera icon when not capturing', () => {
        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#test' },
        })
        expect(wrapper.find('.screenshot-btn__icon').exists()).toBe(true)
        expect(wrapper.find('.screenshot-btn__icon').text()).toBe('📷')
        expect(wrapper.find('.screenshot-btn__spinner').exists()).toBe(false)
    })

    it('resolves CSS selector target and calls capture', async () => {
        // Create a target element in the DOM
        const targetEl = document.createElement('div')
        targetEl.id = 'capture-target'
        document.body.appendChild(targetEl)

        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#capture-target', filename: 'test.png' },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        // Wait for async handleCapture
        await vi.waitFor(() => {
            expect(mockCapture).toHaveBeenCalledWith(targetEl, 'test.png')
        })

        document.body.removeChild(targetEl)
    })

    it('uses default filename when not specified', async () => {
        const targetEl = document.createElement('div')
        targetEl.id = 'default-fn-target'
        document.body.appendChild(targetEl)

        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#default-fn-target' },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        await vi.waitFor(() => {
            expect(mockCapture).toHaveBeenCalledWith(targetEl, 'gmp-prediction.png')
        })

        document.body.removeChild(targetEl)
    })

    it('shows loading state while capturing', async () => {
        // Make capture hang
        let resolveCapture
        mockCapture.mockImplementationOnce(() => new Promise(r => { resolveCapture = r }))

        const targetEl = document.createElement('div')
        targetEl.id = 'loading-target'
        document.body.appendChild(targetEl)

        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#loading-target' },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        await wrapper.vm.$nextTick()

        // Should show loading state
        expect(wrapper.find('.screenshot-btn--loading').exists()).toBe(true)
        expect(wrapper.find('.screenshot-btn__spinner').exists()).toBe(true)
        expect(wrapper.text()).toContain('截图中...')
        expect(wrapper.find('button').attributes('disabled')).toBeDefined()

        // Resolve to clean up
        resolveCapture()
        await vi.waitFor(() => {
            expect(wrapper.find('.screenshot-btn--loading').exists()).toBe(false)
        })

        document.body.removeChild(targetEl)
    })

    it('handles capture error gracefully', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { })
        mockCapture.mockRejectedValueOnce(new Error('capture failed'))

        const targetEl = document.createElement('div')
        targetEl.id = 'error-target'
        document.body.appendChild(targetEl)

        const wrapper = mount(ScreenshotBtn, {
            props: { target: '#error-target' },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        await vi.waitFor(() => {
            expect(consoleSpy).toHaveBeenCalledWith('Screenshot failed:', expect.any(Error))
        })

        // Should recover from error
        expect(wrapper.find('.screenshot-btn--loading').exists()).toBe(false)

        consoleSpy.mockRestore()
        document.body.removeChild(targetEl)
    })

    it('handles object ref target (with $el)', async () => {
        const el = document.createElement('div')
        const refObj = { $el: el }

        const wrapper = mount(ScreenshotBtn, {
            props: { target: refObj },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        await vi.waitFor(() => {
            expect(mockCapture).toHaveBeenCalledWith(el, 'gmp-prediction.png')
        })
    })

    it('handles raw HTMLElement target', async () => {
        const el = document.createElement('div')

        const wrapper = mount(ScreenshotBtn, {
            props: { target: el },
        })

        await wrapper.find('.screenshot-btn').trigger('click')
        await vi.waitFor(() => {
            expect(mockCapture).toHaveBeenCalledWith(el, 'gmp-prediction.png')
        })
    })
})
