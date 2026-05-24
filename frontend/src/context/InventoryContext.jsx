import { createContext, useCallback, useContext, useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getInventorySettings, listProducts } from "../api.js";
import { normalizeInventorySettings, setCurrentInventorySettings } from "../constants/inventory.js";

export const INVENTORY_KEYS = {
  products: ["inventory", "products"],
  settings: ["inventory", "settings"],
};

const InventoryContext = createContext(null);

export function InventoryProvider({ children, onError }) {
  const queryClient = useQueryClient();

  const {
    data: productsData,
    isLoading: loadingProducts,
    error: productsError,
  } = useQuery({
    queryKey: INVENTORY_KEYS.products,
    queryFn: () => listProducts().then((d) => d || []),
  });

  const {
    data: settingsData,
    isLoading: loadingSettings,
    error: settingsError,
  } = useQuery({
    queryKey: INVENTORY_KEYS.settings,
    queryFn: getInventorySettings,
    staleTime: 5 * 60_000,
  });

  const products = productsData ?? [];
  const inventorySettings = useMemo(
    () => normalizeInventorySettings(settingsData),
    [settingsData],
  );

  useEffect(() => {
    setCurrentInventorySettings(inventorySettings);
  }, [inventorySettings]);

  useEffect(() => {
    if (productsError) onError?.(productsError.message || "Error al cargar productos.");
  }, [productsError, onError]);

  useEffect(() => {
    if (settingsError) onError?.(settingsError.message || "Error al cargar configuracion. Usando valores por defecto.");
  }, [settingsError, onError]);

  const updateSettings = useCallback(
    (rawApiResponse) => {
      queryClient.setQueryData(INVENTORY_KEYS.settings, rawApiResponse);
      setCurrentInventorySettings(normalizeInventorySettings(rawApiResponse));
    },
    [queryClient],
  );

  const refreshProducts = useCallback(
    () => queryClient.invalidateQueries({ queryKey: INVENTORY_KEYS.products }),
    [queryClient],
  );

  const refreshSettings = useCallback(
    () => queryClient.invalidateQueries({ queryKey: INVENTORY_KEYS.settings }),
    [queryClient],
  );

  return (
    <InventoryContext.Provider value={{
      products,
      inventorySettings,
      loadingSettings,
      loadingProducts,
      updateSettings,
      refreshProducts,
      refreshSettings,
    }}>
      {children}
    </InventoryContext.Provider>
  );
}

export function useInventoryContext() {
  const ctx = useContext(InventoryContext);
  if (!ctx) throw new Error("useInventoryContext must be used inside InventoryProvider");
  return ctx;
}
