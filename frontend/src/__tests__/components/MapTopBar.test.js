import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MapTopBar from '@/components/scheme-a/MapTopBar.vue'

function mountTopBar(props = {}) {
    return mount(MapTopBar, {
        props: {
            viewpoints: [
                { id: 'niubei', name: '牛背山' },
                { id: 'zheduo', name: '折多山' },
                { id: 'panyang', name: '磐羊湖' },
            ],
            selectedDate: '2026-02-12',
            availableDates: ['2026-02-12', '2026-02-13'],
            activeFilters: [],
            ...props,
        },
    })
}

describe('MapTopBar', () => {
    // --- 渲染 ---
    it('renders search input', () => {
        const wrapper = mountTopBar()
        const input = wrapper.find('.search-box input')
        expect(input.exists()).toBe(true)
        expect(input.attributes('placeholder')).toContain('搜索')
    })

    it('renders filter chips for event types', () => {
        const wrapper = mountTopBar()
        const chips = wrapper.findAll('.chip')
        expect(chips.length).toBe(4) // golden_mountain, cloud_sea, stargazing, frost
    })

    it('renders date button showing formatted date', () => {
        const wrapper = mountTopBar()
        const dateBtn = wrapper.find('.date-btn')
        expect(dateBtn.exists()).toBe(true)
        expect(dateBtn.text()).toContain('2/12')
    })

    it('renders route mode toggle button', () => {
        const wrapper = mountTopBar()
        expect(wrapper.find('.route-btn').exists()).toBe(true)
    })

    // --- 搜索 ---
    it('shows search results when query matches viewpoints', async () => {
        const wrapper = mountTopBar()
        const input = wrapper.find('.search-box input')
        await input.setValue('牛背')
        const results = wrapper.findAll('.search-results li')
        expect(results.length).toBe(1)
        expect(results[0].text()).toContain('牛背山')
    })

    it('hides search results with empty query', () => {
        const wrapper = mountTopBar()
        expect(wrapper.find('.search-results').exists()).toBe(false)
    })

    it('limits search results to 5 items', async () => {
        const manyViewpoints = Array.from({ length: 10 }, (_, i) => ({
            id: `vp${i}`,
            name: `观景台${i}`,
        }))
        const wrapper = mountTopBar({ viewpoints: manyViewpoints })
        await wrapper.find('.search-box input').setValue('观景台')
        const results = wrapper.findAll('.search-results li')
        expect(results.length).toBe(5)
    })

    it('emits search with viewpoint id when result is clicked', async () => {
        const wrapper = mountTopBar()
        await wrapper.find('.search-box input').setValue('牛背')
        await wrapper.find('.search-results li').trigger('click')
        expect(wrapper.emitted('search')).toBeTruthy()
        expect(wrapper.emitted('search')[0]).toEqual(['niubei'])
    })

    it('clears search query after selecting a result', async () => {
        const wrapper = mountTopBar()
        const input = wrapper.find('.search-box input')
        await input.setValue('牛背')
        await wrapper.find('.search-results li').trigger('click')
        expect(input.element.value).toBe('')
    })

    // --- 筛选 ---
    it('marks active filter chips', () => {
        const wrapper = mountTopBar({ activeFilters: ['golden_mountain'] })
        const activeChips = wrapper.findAll('.chip.active')
        expect(activeChips.length).toBe(1)
    })

    it('emits filter with toggled type when chip is clicked', async () => {
        const wrapper = mountTopBar({ activeFilters: [] })
        const chips = wrapper.findAll('.chip')
        await chips[0].trigger('click') // golden_mountain
        expect(wrapper.emitted('filter')).toBeTruthy()
        expect(wrapper.emitted('filter')[0][0]).toContain('golden_mountain')
    })

    it('emits filter removing type when active chip is clicked', async () => {
        const wrapper = mountTopBar({ activeFilters: ['golden_mountain'] })
        const chips = wrapper.findAll('.chip')
        await chips[0].trigger('click')
        expect(wrapper.emitted('filter')[0][0]).not.toContain('golden_mountain')
    })

    // --- 线路模式 ---
    it('emits toggle-route when route button is clicked', async () => {
        const wrapper = mountTopBar()
        await wrapper.find('.route-btn').trigger('click')
        expect(wrapper.emitted('toggle-route')).toBeTruthy()
        expect(wrapper.emitted('toggle-route')[0]).toEqual([true])
    })

    it('toggles route button active state', async () => {
        const wrapper = mountTopBar()
        const btn = wrapper.find('.route-btn')
        expect(btn.classes()).not.toContain('active')
        await btn.trigger('click')
        expect(btn.classes()).toContain('active')
    })

    // --- 日期 ---
    it('shows \"今天\" when selectedDate is empty', () => {
        const wrapper = mountTopBar({ selectedDate: '' })
        expect(wrapper.find('.date-btn').text()).toContain('今天')
    })

    // --- P1-4: 筛选按钮 Tooltip ---
    it('each chip button has a title attribute with Chinese label', () => {
        const wrapper = mountTopBar()
        const chips = wrapper.findAll('.chip')
        const expectedTitles = ['日照金山', '云海', '观星', '霜冻']
        chips.forEach((chip, i) => {
            expect(chip.attributes('title')).toBe(expectedTitles[i])
        })
    })

    it('each chip button has an aria-label attribute for accessibility', () => {
        const wrapper = mountTopBar()
        const chips = wrapper.findAll('.chip')
        const expectedLabels = ['日照金山', '云海', '观星', '霜冻']
        chips.forEach((chip, i) => {
            expect(chip.attributes('aria-label')).toBe(expectedLabels[i])
        })
    })
})
