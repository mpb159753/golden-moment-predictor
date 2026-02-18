import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BestRecommendList from '@/components/scheme-a/BestRecommendList.vue'

// Stub child components
const stubs = {
    EventIcon: {
        name: 'EventIcon',
        template: '<span class="event-icon-stub" :data-type="eventType" />',
        props: ['eventType', 'size'],
    },
    ScoreRing: {
        name: 'ScoreRing',
        template: '<span class="score-ring-stub" :data-score="score" />',
        props: ['score', 'size', 'showLabel'],
    },
}

const sampleRecs = [
    {
        viewpoint: { id: 'niubei', name: '牛背山' },
        event: { event_type: 'golden_mountain', event_label: '日出金山', score: 98 },
        score: 98,
    },
    {
        viewpoint: { id: 'panyang', name: '磐羊湖' },
        event: { event_type: 'cloud_sea', event_label: '壮观云海', score: 90 },
        score: 90,
    },
]

describe('BestRecommendList', () => {
    function mountList(props = {}) {
        return mount(BestRecommendList, {
            props: { recommendations: sampleRecs, ...props },
            global: { stubs },
        })
    }

    // --- 结构 ---
    it('renders section title with "今日最佳推荐"', () => {
        const wrapper = mountList()
        expect(wrapper.text()).toContain('今日最佳推荐')
    })

    it('renders EventIcon for each recommendation', () => {
        const wrapper = mountList()
        const icons = wrapper.findAll('.event-icon-stub')
        expect(icons.length).toBe(2)
        expect(icons[0].attributes('data-type')).toBe('golden_mountain')
        expect(icons[1].attributes('data-type')).toBe('cloud_sea')
    })

    it('renders ScoreRing for each recommendation', () => {
        const wrapper = mountList()
        const rings = wrapper.findAll('.score-ring-stub')
        expect(rings.length).toBe(2)
        expect(rings[0].attributes('data-score')).toBe('98')
    })

    it('renders viewpoint name for each recommendation', () => {
        const wrapper = mountList()
        expect(wrapper.text()).toContain('牛背山')
        expect(wrapper.text()).toContain('磐羊湖')
    })

    it('renders event label for each recommendation', () => {
        const wrapper = mountList()
        expect(wrapper.text()).toContain('日出金山')
        expect(wrapper.text()).toContain('壮观云海')
    })

    // --- 交互 ---
    it('emits select with recommendation when item clicked', async () => {
        const wrapper = mountList()
        const items = wrapper.findAll('.recommend-item')
        await items[0].trigger('click')
        expect(wrapper.emitted('select')).toBeTruthy()
        expect(wrapper.emitted('select')[0][0]).toEqual(sampleRecs[0])
    })

    // --- 空状态 ---
    it('shows empty hint when no recommendations', () => {
        const wrapper = mountList({ recommendations: [] })
        expect(wrapper.text()).toContain('暂无推荐')
    })

    it('does not render list items when empty', () => {
        const wrapper = mountList({ recommendations: [] })
        expect(wrapper.findAll('.recommend-item').length).toBe(0)
    })
})
