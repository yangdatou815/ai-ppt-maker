import { describe, expect, it } from 'vitest'
import { parseTableInput } from '../src/api/client'

describe('parseTableInput', () => {
  it('returns null for empty / whitespace-only input', () => {
    expect(parseTableInput('')).toBeNull()
    expect(parseTableInput('   \n\n  \n')).toBeNull()
  })

  it('parses TSV with first row as headers', () => {
    const t = parseTableInput('a\tb\n1\t2\n3\t4')
    expect(t).not.toBeNull()
    expect(t!.headers).toEqual(['a', 'b'])
    expect(t!.rows).toEqual([
      ['1', '2'],
      ['3', '4'],
    ])
    expect(t!.caption).toBeNull()
  })

  it('falls back to comma when no tabs in header line', () => {
    const t = parseTableInput('q,rev\nQ1,10', 'cap')
    expect(t!.headers).toEqual(['q', 'rev'])
    expect(t!.rows).toEqual([['Q1', '10']])
    expect(t!.caption).toBe('cap')
  })

  it('trims whitespace and skips blank lines', () => {
    const t = parseTableInput('  a\tb  \n\n 1 \t 2 \n')
    expect(t!.headers).toEqual(['a', 'b'])
    expect(t!.rows).toEqual([['1', '2']])
  })

  it('headers-only input yields zero rows', () => {
    const t = parseTableInput('only\theader')
    expect(t!.headers).toEqual(['only', 'header'])
    expect(t!.rows).toEqual([])
  })
})
