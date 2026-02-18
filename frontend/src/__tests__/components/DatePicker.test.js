import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DatePicker from '@/components/layout/DatePicker.vue'

describe('DatePicker', () => {
    const sampleDates = [
        '2026-02-12',
        '2026-02-13',
        '2026-02-14',
        '2026-02-15',
        '2026-02-16',
        '2026-02-17',
        '2026-02-18',
    ]

    it('renders a pill for each date in dates prop', () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-14' },
        })
        const pills = wrapper.findAll('.date-picker__pill')
        expect(pills).toHaveLength(sampleDates.length)
    })

    it('displays short date and weekday in each pill', () => {
        const wrapper = mount(DatePicker, {
            props: { dates: ['2026-02-14'], modelValue: '2026-02-14' },
        })
        const pill = wrapper.find('.date-picker__pill')
        // Should show month/day like "2/14"
        expect(pill.text()).toContain('2/14')
        // Should show weekday (六 = Saturday for 2026-02-14)
        expect(pill.text()).toContain('六')
    })

    it('highlights the selected date with active class', () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-14' },
        })
        const pills = wrapper.findAll('.date-picker__pill')
        const activePill = pills.find(p => p.classes('date-picker__pill--active'))
        expect(activePill).toBeTruthy()
        expect(activePill.text()).toContain('2/14')
    })

    it('emits update:modelValue when a pill is clicked', async () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-14' },
        })
        const pills = wrapper.findAll('.date-picker__pill')
        // Click the first pill (2026-02-12)
        await pills[0].trigger('click')
        expect(wrapper.emitted('update:modelValue')).toBeTruthy()
        expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-02-12'])
    })

    it('renders nothing when dates is empty', () => {
        const wrapper = mount(DatePicker, {
            props: { dates: [], modelValue: null },
        })
        const pills = wrapper.findAll('.date-picker__pill')
        expect(pills).toHaveLength(0)
    })

    it('handles keyboard ArrowRight navigation', async () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-14' },
            attachTo: document.createElement('div'),
        })
        const container = wrapper.find('.date-picker')
        await container.trigger('keydown', { key: 'ArrowRight' })
        expect(wrapper.emitted('update:modelValue')).toBeTruthy()
        expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-02-15'])
        wrapper.unmount()
    })

    it('handles keyboard ArrowLeft navigation', async () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-14' },
            attachTo: document.createElement('div'),
        })
        const container = wrapper.find('.date-picker')
        await container.trigger('keydown', { key: 'ArrowLeft' })
        expect(wrapper.emitted('update:modelValue')).toBeTruthy()
        expect(wrapper.emitted('update:modelValue')[0]).toEqual(['2026-02-13'])
        wrapper.unmount()
    })

    it('does not go past last date on ArrowRight', async () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-18' },
            attachTo: document.createElement('div'),
        })
        const container = wrapper.find('.date-picker')
        await container.trigger('keydown', { key: 'ArrowRight' })
        // Should not emit since already at the last date
        expect(wrapper.emitted('update:modelValue')).toBeFalsy()
        wrapper.unmount()
    })

    it('does not go before first date on ArrowLeft', async () => {
        const wrapper = mount(DatePicker, {
            props: { dates: sampleDates, modelValue: '2026-02-12' },
            attachTo: document.createElement('div'),
        })
        const container = wrapper.find('.date-picker')
        await container.trigger('keydown', { key: 'ArrowLeft' })
        expect(wrapper.emitted('update:modelValue')).toBeFalsy()
        wrapper.unmount()
    })
})
