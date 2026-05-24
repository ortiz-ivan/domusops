import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { InventoryProvider, useInventoryContext } from './InventoryContext.jsx'

vi.mock('../api.js', () => ({
  getInventorySettings: vi.fn(),
  listProducts: vi.fn(),
}))

import { getInventorySettings, listProducts } from '../api.js'

const MOCK_PRODUCTS = [
  { id: 1, name: 'Arroz', category: 'food', stock: 5 },
  { id: 2, name: 'Detergente', category: 'cleaning', stock: 2 },
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0, gcTime: 0 } },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

function ProductList() {
  const { products, loadingProducts, loadingSettings } = useInventoryContext()
  if (loadingSettings || loadingProducts) return <span>loading</span>
  if (products.length === 0) return <span>empty</span>
  return (
    <ul>
      {products.map((p) => (
        <li key={p.id}>{p.name}</li>
      ))}
    </ul>
  )
}

function SettingsDisplay() {
  const { inventorySettings, loadingSettings } = useInventoryContext()
  if (loadingSettings) return <span>loading</span>
  return <span data-testid="currency">{inventorySettings.currency.code}</span>
}

describe('InventoryProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getInventorySettings.mockResolvedValue({})
    listProducts.mockResolvedValue(MOCK_PRODUCTS)
  })

  it('renders children without crashing', async () => {
    render(
      <InventoryProvider>
        <span>ok</span>
      </InventoryProvider>,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText('ok')).toBeInTheDocument()
  })

  it('loads and exposes products from the API', async () => {
    render(
      <InventoryProvider>
        <ProductList />
      </InventoryProvider>,
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument())
    expect(screen.getByText('Arroz')).toBeInTheDocument()
    expect(screen.getByText('Detergente')).toBeInTheDocument()
    expect(listProducts).toHaveBeenCalledOnce()
  })

  it('exposes normalized settings with currency defaults', async () => {
    render(
      <InventoryProvider>
        <SettingsDisplay />
      </InventoryProvider>,
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument())
    expect(screen.getByTestId('currency').textContent).toBe('PYG')
  })

  it('returns empty products array when API fails', async () => {
    listProducts.mockRejectedValue(new Error('Network error'))
    const onError = vi.fn()
    render(
      <InventoryProvider onError={onError}>
        <ProductList />
      </InventoryProvider>,
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument())
    expect(screen.getByText('empty')).toBeInTheDocument()
    expect(onError).toHaveBeenCalledWith('Network error')
  })

  it('uses default settings when settings API fails', async () => {
    getInventorySettings.mockRejectedValue(new Error('Server error'))
    const onError = vi.fn()
    render(
      <InventoryProvider onError={onError}>
        <SettingsDisplay />
      </InventoryProvider>,
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument())
    // Falls back to DEFAULT_INVENTORY_SETTINGS (currency PYG)
    expect(screen.getByTestId('currency').textContent).toBe('PYG')
    expect(onError).toHaveBeenCalled()
  })
})

describe('useInventoryContext', () => {
  it('throws a descriptive error when used outside provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    function BadConsumer() {
      useInventoryContext()
      return null
    }
    expect(() => render(<BadConsumer />)).toThrow(
      'useInventoryContext must be used inside InventoryProvider'
    )
    spy.mockRestore()
  })
})
