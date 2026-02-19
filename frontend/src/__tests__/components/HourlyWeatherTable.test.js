import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HourlyWeatherTable from '@/components/forecast/HourlyWeatherTable.vue'

describe('HourlyWeatherTable', () => {
    const mockHourly = [
        { hour: 6, time: '06:00', weather: { temperature: -3.2, cloud_cover: 10, weather_icon: 'clear' } },
        { hour: 7, time: '07:00', weather: { temperature: -1.0, cloud_cover: 15, weather_icon: 'clear' } },
        { hour: 8, time: '08:00', weather: { temperature: 2.5, cloud_cover: 30, weather_icon: 'partly_cloudy' } },
        { hour: 12, time: '12:00', weather: { temperature: 8.0, cloud_cover: 70, weather_icon: 'cloudy' } },
        { hour: 15, time: '15:00', weather: { temperature: 5.5, cloud_cover: 90, weather_icon: 'rain' } },
        { hour: 20, time: '20:00', weather: { temperature: -1.0, cloud_cover: 5, weather_icon: 'snow' } },
    ]

    const mockHourlyWithEmpty = [
        { hour: 6, time: '06:00', weather: { temperature: -3.2, cloud_cover: 10, weather_icon: 'clear' } },
        { hour: 7, time: '07:00', weather: {} },
        { hour: 8, time: '08:00', weather: { temperature: 2.5, cloud_cover: 30, weather_icon: 'partly_cloudy' } },
    ]

    it('renders collapsed by default (no .weather-rows)', () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        expect(wrapper.find('.weather-rows').exists()).toBe(false)
    })

    it('renders .collapse-header', () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        expect(wrapper.find('.collapse-header').exists()).toBe(true)
    })

    it('expands on .collapse-header click', async () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        await wrapper.find('.collapse-header').trigger('click')
        expect(wrapper.find('.weather-rows').exists()).toBe(true)
    })

    it('renders correct number of rows when expanded (filters empty weather)', async () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourlyWithEmpty } })
        await wrapper.find('.collapse-header').trigger('click')
        const rows = wrapper.findAll('.weather-row')
        // Only 2 rows: hour 6 and hour 8 (hour 7 has empty weather)
        expect(rows).toHaveLength(2)
    })

    it('displays temperature value', async () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        await wrapper.find('.collapse-header').trigger('click')
        const firstRow = wrapper.findAll('.weather-row')[0]
        expect(firstRow.text()).toContain('-3.2')
    })

    it('displays cloud cover percentage', async () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        await wrapper.find('.collapse-header').trigger('click')
        const firstRow = wrapper.findAll('.weather-row')[0]
        expect(firstRow.text()).toContain('10%')
    })

    it('maps weather_icon to correct emoji', async () => {
        const wrapper = mount(HourlyWeatherTable, { props: { hourly: mockHourly } })
        await wrapper.find('.collapse-header').trigger('click')
        const rows = wrapper.findAll('.weather-row')
        // clear → ☀️
        expect(rows[0].text()).toContain('☀️')
        // partly_cloudy → ⛅
        expect(rows[2].text()).toContain('⛅')
        // cloudy → ☁️
        expect(rows[3].text()).toContain('☁️')
        // rain → 🌧️
        expect(rows[4].text()).toContain('🌧️')
        // snow → ❄️
        expect(rows[5].text()).toContain('❄️')
    })
})
