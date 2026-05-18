import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getInventorySettings, listProducts } from "../api.js";
import { normalizeInventorySettings, setCurrentInventorySettings } from "../constants/inventory.js";

const InventoryContext = createContext(null);

export function InventoryProvider({ children, onError }) {
  const [products, setProducts] = useState([]);
  const [inventorySettings, setInventorySettings] = useState(() => normalizeInventorySettings());
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [loadingProducts, setLoadingProducts] = useState(false);

  const updateSettings = useCallback((next) => {
    setInventorySettings(next);
    setCurrentInventorySettings(next);
  }, []);

  const refreshSettings = useCallback(async () => {
    setLoadingSettings(true);
    try {
      const data = await getInventorySettings();
      updateSettings(normalizeInventorySettings(data));
    } catch (err) {
      updateSettings(normalizeInventorySettings());
      onError?.(err.message || "Error al cargar configuracion. Usando valores por defecto.");
    } finally {
      setLoadingSettings(false);
    }
  }, [onError, updateSettings]);

  const refreshProducts = useCallback(async () => {
    setLoadingProducts(true);
    try {
      const data = await listProducts();
      setProducts(data || []);
    } catch (err) {
      setProducts([]);
      onError?.(err.message || "Error al cargar productos.");
    } finally {
      setLoadingProducts(false);
    }
  }, [onError]);

  useEffect(() => {
    refreshSettings();
    refreshProducts();
  }, [refreshSettings, refreshProducts]);

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
