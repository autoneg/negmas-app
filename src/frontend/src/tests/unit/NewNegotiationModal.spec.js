/**
 * Component tests for NewNegotiationModal
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import NewNegotiationModal from '@/components/NewNegotiationModal.vue'
import { useNegotiationsStore } from '@/stores/negotiations'

// Mock fetch
global.fetch = vi.fn()

describe('NewNegotiationModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    global.fetch.mockReset()
  })

  describe('Visibility', () => {
    it('should render when show prop is true', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      expect(wrapper.find('.modal-overlay').exists()).toBe(true)
      expect(wrapper.find('.modal-title').text()).toBe('Start New Negotiation')
    })

    it('should not render when show prop is false', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: false,
        },
      })

      expect(wrapper.find('.modal-overlay').exists()).toBe(false)
    })
  })

  describe('Header Actions', () => {
    it('should have Recent, Load, and Save buttons', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const buttons = wrapper.findAll('.modal-header-actions button')
      expect(buttons.length).toBeGreaterThanOrEqual(3)

      const buttonTexts = buttons.map((b) => b.text())
      expect(buttonTexts).toContain('Recent')
      expect(buttonTexts).toContain('Load')
      expect(buttonTexts).toContain('Save')
    })

    it('should have Save button disabled when no scenario is selected', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const saveButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Save')
      expect(saveButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('Recent Sessions Dropdown', () => {
    it('should open recent sessions dropdown on button click', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ presets: [] }),
      })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const recentButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Recent')
      await recentButton.trigger('click')

      expect(wrapper.find('.dropdown-menu').exists()).toBe(true)
    })

    it('should show "No recent sessions" when list is empty', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ presets: [] }),
      })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const store = useNegotiationsStore()
      store.recentSessions = []

      const recentButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Recent')
      await recentButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('No recent sessions')
    })

    it('should display recent sessions from store', async () => {
      const mockRecentSessions = [
        {
          name: 'Recent Session 1',
          scenario_name: 'Test Scenario',
          negotiators: [{ name: 'Agent1' }, { name: 'Agent2' }],
          last_used_at: '2024-01-01T00:00:00Z',
        },
      ]

      // Mock both the scenarios/negotiators load AND the recent sessions load
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ scenarios: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ negotiators: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ presets: mockRecentSessions }),
        })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      // Wait for component mount
      await wrapper.vm.$nextTick()

      const recentButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Recent')
      await recentButton.trigger('click')

      // Wait for the dropdown to open and data to load
      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(wrapper.text()).toContain('Test Scenario')
      expect(wrapper.text()).toContain('Agent1 vs Agent2')
    })
  })

  describe('Saved Sessions Dropdown', () => {
    it('should open saved sessions dropdown on button click', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ presets: [] }),
      })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const loadButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Load')
      await loadButton.trigger('click')

      await wrapper.vm.$nextTick()

      expect(wrapper.findAll('.dropdown-menu').length).toBeGreaterThan(0)
    })

    it('should show "No saved sessions" when list is empty', async () => {
      // Mock the fetch calls that happen on mount
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ scenarios: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ negotiators: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ presets: [] }),
        })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const store = useNegotiationsStore()
      store.sessionPresets = []

      const loadButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Load')
      await loadButton.trigger('click')

      // Wait for async operations to complete
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()

      expect(wrapper.text()).toContain('No saved sessions')
    })

    it('should display saved presets from store', async () => {
      const mockPresets = [
        {
          name: 'Saved Preset 1',
          scenario_name: 'Test Scenario',
          scenario_path: '/path/to/scenario',
        },
      ]

      // Mock scenarios, negotiators, and session presets load
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ scenarios: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ negotiators: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ presets: mockPresets }),
        })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      // Wait for component mount
      await wrapper.vm.$nextTick()

      const loadButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Load')
      await loadButton.trigger('click')

      // Wait for the dropdown to open and data to load
      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 10))

      expect(wrapper.text()).toContain('Saved Preset 1')
      expect(wrapper.text()).toContain('Test Scenario')
    })

    it('should have delete button for each preset', async () => {
      const mockPresets = [
        {
          name: 'Preset 1',
          scenario_name: 'Test Scenario 1',
          scenario_path: '/path/1',
        },
        {
          name: 'Preset 2',
          scenario_name: 'Test Scenario 2',
          scenario_path: '/path/2',
        },
      ]

      // Mock scenarios, negotiators, and session presets load
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ scenarios: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ negotiators: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ presets: mockPresets }),
        })

      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      // Wait for component mount
      await wrapper.vm.$nextTick()

      const loadButton = wrapper.findAll('.modal-header-actions button').find((b) => b.text() === 'Load')
      await loadButton.trigger('click')

      // Wait for the dropdown to open and data to load
      await wrapper.vm.$nextTick()
      await new Promise((resolve) => setTimeout(resolve, 10))

      const deleteButtons = wrapper.findAll('.btn-icon-sm')
      expect(deleteButtons.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('Close Functionality', () => {
    it('should emit close event when close button is clicked', async () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      await wrapper.find('.modal-close').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
      expect(wrapper.emitted('close').length).toBe(1)
    })

    it('should emit close event when clicking modal overlay', async () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      await wrapper.find('.modal-overlay').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })
  })

  describe('Wizard Tabs', () => {
    it('should render all wizard tabs', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      expect(wrapper.text()).toContain('Scenario')
      expect(wrapper.text()).toContain('Negotiators')
      expect(wrapper.text()).toContain('Settings')
    })

    it('should start with scenario tab active', () => {
      const wrapper = mount(NewNegotiationModal, {
        props: {
          show: true,
        },
      })

      const activeTab = wrapper.find('.wizard-tab.active')
      expect(activeTab.text()).toContain('Scenario')
    })
  })
})
