// NOTICE: This file is protected under RCF-PL
import { render, screen } from '@testing-library/react'
import { StatusBar } from '@/components/shell/StatusBar'

describe('StatusBar', () => {
  it('renders default status items', () => {
    render(<StatusBar />)

    expect(screen.getByText('Orchestrator')).toBeInTheDocument()
    expect(screen.getByText('Postgres')).toBeInTheDocument()
    expect(screen.getByText('Mongo')).toBeInTheDocument()
    expect(screen.getByText('NIM')).toBeInTheDocument()
    expect(screen.getByText('RCF')).toBeInTheDocument()
    expect(screen.getByText('aladdin-ai')).toBeInTheDocument()
  })

  it('displays version from package.json', () => {
    render(<StatusBar />)

    const versionCode = screen.getByText(/v\d+\.\d+\.\d+/)
    expect(versionCode).toBeInTheDocument()
  })

  it('renders custom items when provided', () => {
    const customItems = [
      { id: 'test', label: 'Test Service', code: 'running', dot: 'ok' as const }
    ]

    render(<StatusBar items={customItems} />)

    expect(screen.getByText('Test Service')).toBeInTheDocument()
    expect(screen.getByText('running')).toBeInTheDocument()
  })

  it('separates left and right items', () => {
    const items = [
      { id: 'left', label: 'Left Item', code: 'ok' },
      { id: 'right', label: 'Right Item', code: 'ok', right: true }
    ]

    const { container } = render(<StatusBar items={items} />)

    const spacer = container.querySelector('.sb-spacer')
    expect(spacer).toBeInTheDocument()
  })
})
