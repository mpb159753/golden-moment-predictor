import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppStore } from '@/stores/app'

describe('useAppStore', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('has default state values', () => {
        const store = useAppStore()

        expect(store.sidebarOpen).toBe(false)
        expect(store.filterEvent).toBeNull()
        expect(store.filterMinScore).toBe(0)
        expect(typeof store.isMobile).toBe('boolean')
    })

    it('state can be mutated', () => {
        const store = useAppStore()

        store.sidebarOpen = true
        store.filterEvent = 'cloud_sea'
        store.filterMinScore = 80

        expect(store.sidebarOpen).toBe(true)
        expect(store.filterEvent).toBe('cloud_sea')
        expect(store.filterMinScore).toBe(80)
    })

    it('initResponsive updates isMobile on resize', () => {
        const store = useAppStore()
        store.initResponsive()

        // Simulate wide viewport
        window.innerWidth = 1024
        window.dispatchEvent(new Event('resize'))
        expect(store.isMobile).toBe(false)

        // Simulate narrow viewport
        window.innerWidth = 375
        window.dispatchEvent(new Event('resize'))
        expect(store.isMobile).toBe(true)
    })

    it('initResponsive returns cleanup function that removes listener', () => {
        const store = useAppStore()
        const cleanup = store.initResponsive()

        window.innerWidth = 375
        window.dispatchEvent(new Event('resize'))
        expect(store.isMobile).toBe(true)

        cleanup()

        // After cleanup, resize should not update isMobile
        window.innerWidth = 1024
        window.dispatchEvent(new Event('resize'))
        expect(store.isMobile).toBe(true) // still true — listener removed
    })
})
