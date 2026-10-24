import { useCallback, useRef } from "react";

/** Una llave por intento de creación: se mantiene en los reintentos y cambia cuando el
 * formulario cambia o la creación termina bien (RNF-INT-01). */
export function useIdempotencyKey() {
  const key = useRef(crypto.randomUUID());
  const renew = useCallback(() => {
    key.current = crypto.randomUUID();
  }, []);
  return { current: () => key.current, renew };
}
