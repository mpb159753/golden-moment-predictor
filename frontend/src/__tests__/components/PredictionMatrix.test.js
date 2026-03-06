import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const mockGroup = {
    name: '贡嘎山系',
    key: 'gongga',
    viewpoints: [{
        id: 'niubei',
        name: '牛背山',
        daily: [{
            date: '2026-02-21',
            am: { weather: '晴天', event: '日照金山', score: 90 },
            pm: { weather: '晴天', event: '云海', score: 75 },
        }],
    }],
}

describe('PredictionMatrix', () => {
    it('renders group name', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('贡嘎山系')
    })

    it('renders viewpoint names', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('牛背山')
    })

    it('renders am/pm labels', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('上午')
        expect(wrapper.text()).toContain('下午')
    })

    it('applies score-star class for score >= 80', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const cells = wrapper.findAll('td')
        const amCell = cells.find(c => c.text().includes('日照金山'))
        expect(amCell?.classes()).toContain('score-star')
    })

    it('applies score-good class for score 50-79', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const cells = wrapper.findAll('td')
        const pmCell = cells.find(c => c.text().includes('云海'))
        expect(pmCell?.classes()).toContain('score-good')
    })

    it('formats date as M/D', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('2/21')
    })

    it('renders score legend with all four levels', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const legend = wrapper.find('.score-legend')
        expect(legend.exists()).toBe(true)
        expect(legend.text()).toContain('强烈推荐')
        expect(legend.text()).toContain('值得关注')
        expect(legend.text()).toContain('一般')
        expect(legend.text()).toContain('不推荐')
    })

    it('renders four legend swatches', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const swatches = wrapper.findAll('.legend-swatch')
        expect(swatches).toHaveLength(4)
        expect(swatches[0].classes()).toContain('swatch-star')
        expect(swatches[1].classes()).toContain('swatch-good')
        expect(swatches[2].classes()).toContain('swatch-mild')
        expect(swatches[3].classes()).toContain('swatch-poor')
    })
})
