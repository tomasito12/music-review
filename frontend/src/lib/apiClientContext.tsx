import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactElement,
  type ReactNode,
} from "react";

import { ApiClient } from "./apiClient";

interface ApiClientContextValue {
  createClient: () => ApiClient;
}

const ApiClientContext = createContext<ApiClientContextValue | null>(null);

interface ApiClientProviderProps {
  children: ReactNode;
  token?: string;
}

/** Provides a shared ApiClient factory for hooks and child components. */
export function ApiClientProvider({
  children,
  token,
}: ApiClientProviderProps): ReactElement {
  const value = useMemo(
    () => ({
      createClient: () => new ApiClient({ token }),
    }),
    [token],
  );

  return (
    <ApiClientContext.Provider value={value}>{children}</ApiClientContext.Provider>
  );
}

/** Return a factory that builds ApiClient instances with the app-wide base URL. */
export function useApiClient(): () => ApiClient {
  const context = useContext(ApiClientContext);

  return useCallback(() => {
    if (context !== null) {
      return context.createClient();
    }
    return new ApiClient();
  }, [context]);
}
