import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBadge from '@/components/score/StatusBadge.vue'

describe('StatusBadge', () => {
    it('renders Perfect status in Chinese by default', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Perfect' },
        })
        expect(wrapper.text()).toBe('完美')
    })

    it('renders Recommended status in Chinese', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Recommended' },
        })
        expect(wrapper.text()).toBe('推荐')
    })

    it('renders Possible status in Chinese', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Possible' },
        })
        expect(wrapper.text()).toBe('一般')
    })

    it('renders Not Recommended status in Chinese', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Not Recommended' },
        })
        expect(wrapper.text()).toBe('不推荐')
    })

    it('renders status in English when lang is en', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Perfect', lang: 'en' },
        })
        expect(wrapper.text()).toBe('Perfect')
    })

    it('applies gold-based background for Perfect status', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Perfect' },
        })
        const span = wrapper.find('.status-badge')
        // backgroundColor should be #FFD70020 (gold with 12% alpha)
        expect(span.attributes('style')).toContain('#FFD70020')
        // textColor should be #FFD700
        expect(span.attributes('style')).toContain('color: #FFD700')
    })

    it('applies green-based colors for Recommended status', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Recommended' },
        })
        const span = wrapper.find('.status-badge')
        expect(span.attributes('style')).toContain('#10B98120')
        expect(span.attributes('style')).toContain('color: #10B981')
    })

    it('applies amber-based colors for Possible status', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Possible' },
        })
        const span = wrapper.find('.status-badge')
        expect(span.attributes('style')).toContain('#F59E0B20')
        expect(span.attributes('style')).toContain('color: #F59E0B')
    })

    it('applies gray-based colors for Not Recommended status', () => {
        const wrapper = mount(StatusBadge, {
            props: { status: 'Not Recommended' },
        })
        const span = wrapper.find('.status-badge')
        expect(span.attributes('style')).toContain('#9CA3AF20')
        expect(span.attributes('style')).toContain('color: #9CA3AF')
    })
})
