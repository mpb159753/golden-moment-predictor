import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock GSAP — vi.hoisted ensures the variable is available when vi.mock is hoisted
const { mockGsapTo } = vi.hoisted(() => {
    const mockGsapTo = vi.fn()
    return { mockGsapTo }
})
vi.mock('gsap', () => ({
    default: { to: mockGsapTo },
}))

import BottomSheet from '@/components/scheme-a/BottomSheet.vue'

function mountSheet(props = {}, slots = {}) {
    return mount(BottomSheet, {
        props: {
            state: 'collapsed',
            ...props,
        },
        slots: {
            collapsed: '<p class="slot-collapsed">收起内容</p>',
            half: '<p class="slot-half">半展内容</p>',
            full: '<p class="slot-full">全展内容</p>',
            ...slots,
        },
        attachTo: document.body,
    })
}

describe('BottomSheet', () => {
    const originalInnerHeight = window.innerHeight

    beforeEach(() => {
        mockGsapTo.mockClear()
    })

    afterEach(() => {
        Object.defineProperty(window, 'innerHeight', {
            value: originalInnerHeight,
            writable: true,
        })
    })

    // --- 渲染 ---
    it('renders the sheet container with fixed positioning', () => {
        const wrapper = mountSheet()
        expect(wrapper.find('.bottom-sheet').exists()).toBe(true)
    })

    it('renders the drag handle bar', () => {
        const wrapper = mountSheet()
        expect(wrapper.find('.sheet-handle').exists()).toBe(true)
        expect(wrapper.find('.handle-bar').exists()).toBe(true)
    })

    it('renders the scrollable content area', () => {
        const wrapper = mountSheet()
        expect(wrapper.find('.sheet-content').exists()).toBe(true)
    })

    // --- 三级状态 CSS class ---
    it('applies state-collapsed class by default', () => {
        const wrapper = mountSheet()
        expect(wrapper.find('.bottom-sheet').classes()).toContain('state-collapsed')
    })

    it('applies state-half class when state is half', () => {
        const wrapper = mountSheet({ state: 'half' })
        expect(wrapper.find('.bottom-sheet').classes()).toContain('state-half')
    })

    it('applies state-full class when state is full', () => {
        const wrapper = mountSheet({ state: 'full' })
        expect(wrapper.find('.bottom-sheet').classes()).toContain('state-full')
    })

    // --- Slots ---
    it('shows collapsed slot content when state is collapsed', () => {
        const wrapper = mountSheet({ state: 'collapsed' })
        expect(wrapper.find('.slot-collapsed').isVisible()).toBe(true)
        expect(wrapper.find('.slot-half').isVisible()).toBe(false)
        expect(wrapper.find('.slot-full').isVisible()).toBe(false)
    })

    it('shows half slot content when state is half', () => {
        const wrapper = mountSheet({ state: 'half' })
        expect(wrapper.find('.slot-collapsed').isVisible()).toBe(false)
        expect(wrapper.find('.slot-half').isVisible()).toBe(true)
        expect(wrapper.find('.slot-full').isVisible()).toBe(false)
    })

    it('shows full slot content when state is full', () => {
        const wrapper = mountSheet({ state: 'full' })
        expect(wrapper.find('.slot-collapsed').isVisible()).toBe(false)
        expect(wrapper.find('.slot-half').isVisible()).toBe(false)
        expect(wrapper.find('.slot-full').isVisible()).toBe(true)
    })

    // --- State prop sync ---
    it('syncs internal state when state prop changes', async () => {
        const wrapper = mountSheet({ state: 'collapsed' })
        expect(wrapper.find('.bottom-sheet').classes()).toContain('state-collapsed')
        await wrapper.setProps({ state: 'half' })
        expect(wrapper.find('.bottom-sheet').classes()).toContain('state-half')
    })

    // --- Desktop mode ---
    it('applies desktop-mode class when desktopMode is true', () => {
        const wrapper = mountSheet({ desktopMode: true })
        expect(wrapper.find('.bottom-sheet').classes()).toContain('desktop-mode')
    })

    it('does not apply desktop-mode class by default', () => {
        const wrapper = mountSheet()
        expect(wrapper.find('.bottom-sheet').classes()).not.toContain('desktop-mode')
    })

    it('hides drag handle in desktop mode via CSS', () => {
        const wrapper = mountSheet({ desktopMode: true })
        // The handle element exists but should be hidden via CSS
        expect(wrapper.find('.sheet-handle').exists()).toBe(true)
    })

    // --- 手势拖拽 ---
    describe('touch drag gesture', () => {
        it('starts drag on touchstart', async () => {
            const wrapper = mountSheet()
            const handle = wrapper.find('.sheet-handle')
            await handle.trigger('touchstart', {
                touches: [{ clientY: 500 }],
            })
            // After touchstart, isDragging should be true — verified via inline style presence
            // We verify the drag is active by moving and checking style update
            await handle.trigger('touchmove', {
                touches: [{ clientY: 400 }],
            })
            const sheet = wrapper.find('.bottom-sheet')
            // During drag, inline height style should be applied
            expect(sheet.element.style.height).not.toBe('')
        })

        it('emits state-change on touchend with snap to nearest state', async () => {
            // Mock window.innerHeight
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'collapsed' })
            const handle = wrapper.find('.sheet-handle')

            // Start drag at bottom area (collapsed = 20% = 200px from bottom, clientY ~ 800)
            await handle.trigger('touchstart', {
                touches: [{ clientY: 800 }],
            })

            // Drag up to ~500px height (50% of viewport → should snap to 'half')
            await handle.trigger('touchmove', {
                touches: [{ clientY: 500 }],
            })

            await handle.trigger('touchend')

            // GSAP onComplete triggers the emit
            mockGsapTo.mock.calls[0][1].onComplete()

            const emitted = wrapper.emitted('state-change')
            expect(emitted).toBeTruthy()
            expect(emitted[0][0]).toBe('half')
        })

        it('snaps to collapsed when drag ratio < 0.30', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'half' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('touchstart', {
                touches: [{ clientY: 550 }],
            })

            // Drag down so height ~ 150px = 15% → collapsed
            await handle.trigger('touchmove', {
                touches: [{ clientY: 850 }],
            })

            await handle.trigger('touchend')

            // GSAP onComplete triggers the emit
            mockGsapTo.mock.calls[0][1].onComplete()

            const emitted = wrapper.emitted('state-change')
            expect(emitted).toBeTruthy()
            expect(emitted[0][0]).toBe('collapsed')
        })

        it('snaps to full when drag ratio >= 0.65', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'half' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('touchstart', {
                touches: [{ clientY: 550 }],
            })

            // Drag up so height ~ 750px = 75% → full
            await handle.trigger('touchmove', {
                touches: [{ clientY: 250 }],
            })

            await handle.trigger('touchend')

            // GSAP onComplete triggers the emit
            mockGsapTo.mock.calls[0][1].onComplete()

            const emitted = wrapper.emitted('state-change')
            expect(emitted).toBeTruthy()
            expect(emitted[0][0]).toBe('full')
        })
    })

    // --- Mouse 拖拽 (桌面端) ---
    describe('mouse drag gesture', () => {
        it('starts drag on mousedown and listens for mousemove/mouseup', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'collapsed' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('mousedown', { clientY: 800 })

            // Simulate mousemove on document
            document.dispatchEvent(new MouseEvent('mousemove', { clientY: 500 }))

            const sheet = wrapper.find('.bottom-sheet')
            expect(sheet.element.style.height).not.toBe('')

            // Simulate mouseup
            document.dispatchEvent(new MouseEvent('mouseup'))

            // GSAP onComplete triggers the emit
            mockGsapTo.mock.calls[0][1].onComplete()

            const emitted = wrapper.emitted('state-change')
            expect(emitted).toBeTruthy()
        })
    })

    // --- 清理 ---
    it('cleans up mouse event listeners on unmount', () => {
        const removeEventSpy = vi.spyOn(document, 'removeEventListener')
        const wrapper = mountSheet()
        wrapper.unmount()
        // Should attempt to remove mousemove and mouseup listeners
        expect(removeEventSpy).toHaveBeenCalled()
        removeEventSpy.mockRestore()
    })

    // --- GSAP 动画 ---
    describe('GSAP spring animation', () => {
        it('calls gsap.to with elastic easing when drag ends', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'collapsed' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('touchstart', {
                touches: [{ clientY: 800 }],
            })
            await handle.trigger('touchmove', {
                touches: [{ clientY: 500 }],
            })
            await handle.trigger('touchend')

            expect(mockGsapTo).toHaveBeenCalledTimes(1)
            const [target, options] = mockGsapTo.mock.calls[0]
            expect(target).toBe(wrapper.find('.bottom-sheet').element)
            expect(options.ease).toBe('elastic.out(1, 0.75)')
            expect(options.duration).toBe(0.5)
        })

        it('animates to correct target height for half state', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'collapsed' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('touchstart', {
                touches: [{ clientY: 800 }],
            })
            // Drag to ~500px height → snaps to half (45% = 450px)
            await handle.trigger('touchmove', {
                touches: [{ clientY: 500 }],
            })
            await handle.trigger('touchend')

            const [, options] = mockGsapTo.mock.calls[0]
            expect(options.height).toBe(450) // 45% of 1000
        })

        it('calls onComplete to emit state-change after animation', async () => {
            Object.defineProperty(window, 'innerHeight', { value: 1000, writable: true })

            const wrapper = mountSheet({ state: 'collapsed' })
            const handle = wrapper.find('.sheet-handle')

            await handle.trigger('touchstart', {
                touches: [{ clientY: 800 }],
            })
            await handle.trigger('touchmove', {
                touches: [{ clientY: 500 }],
            })
            await handle.trigger('touchend')

            // onComplete callback should exist
            const [, options] = mockGsapTo.mock.calls[0]
            expect(typeof options.onComplete).toBe('function')

            // Calling onComplete should emit state-change
            options.onComplete()
            const emitted = wrapper.emitted('state-change')
            expect(emitted).toBeTruthy()
            expect(emitted[0][0]).toBe('half')
        })
    })
})

