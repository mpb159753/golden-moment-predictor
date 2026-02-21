import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PredictionMatrix from '@/components/forecast/PredictionMatrix.vue'

const mockGroup = {
    name: '贡嘎山系',
    key: 'gongga',
    viewpoints: [{
        id: 'niubei_gongga',
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

    it('applies green background for score >= 80', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        const cells = wrapper.findAll('td')
        const amCell = cells.find(c => c.text().includes('日照金山'))
        expect(amCell?.attributes('style')).toContain('#C6EFCE')
    })

    it('formats date as M/D', () => {
        const wrapper = mount(PredictionMatrix, {
            props: { group: mockGroup, days: ['2026-02-21'], showHeader: true, showFooter: false },
        })
        expect(wrapper.text()).toContain('2/21')
    })
})
