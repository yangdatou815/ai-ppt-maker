import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TemplatePicker from '../src/components/TemplatePicker.vue'
import type { TemplateInfo } from '../src/api/client'

const fakes: TemplateInfo[] = [
  {
    name: 'executive-dark',
    display_name: 'Executive Dark',
    description: 'Premium dark template',
    tags: ['business'],
    theme: { primary: '#0B1F3A', accent: '#C9A24E' },
    fonts: { heading: 'Source Han Serif CN' },
    has_master: false,
    thumbnail_url: '/api/templates/executive-dark/thumbnail.png',
  },
  {
    name: 'minimal-light',
    display_name: 'Minimal Light',
    description: 'Minimal pitch template',
    tags: ['minimal'],
    theme: { primary: '#FAFAF7', accent: '#E2532E' },
    fonts: { heading: 'Inter' },
    has_master: false,
    thumbnail_url: null,
  },
]

describe('TemplatePicker', () => {
  it('renders one card per template', () => {
    const w = mount(TemplatePicker, { props: { templates: fakes, selected: null } })
    expect(w.findAll('.tcard')).toHaveLength(2)
    expect(w.text()).toContain('Executive Dark')
    expect(w.text()).toContain('Minimal Light')
  })

  it('emits select on click', async () => {
    const w = mount(TemplatePicker, { props: { templates: fakes, selected: null } })
    await w.findAll('.tcard')[1].trigger('click')
    expect(w.emitted('select')?.[0]).toEqual(['minimal-light'])
  })

  it('marks selected card', () => {
    const w = mount(TemplatePicker, {
      props: { templates: fakes, selected: 'executive-dark' },
    })
    expect(w.findAll('.tcard')[0].classes()).toContain('selected')
    expect(w.findAll('.tcard')[1].classes()).not.toContain('selected')
  })

  it('renders thumbnail <img> only when thumbnail_url is set', () => {
    const w = mount(TemplatePicker, { props: { templates: fakes, selected: null } })
    const imgs = w.findAll('img.thumbnail')
    expect(imgs).toHaveLength(1)
    expect(imgs[0].attributes('src')).toBe('/api/templates/executive-dark/thumbnail.png')
    expect(imgs[0].attributes('alt')).toContain('Executive Dark')
  })
})
