import { useCallback, useState } from "react";
import { api, session, type Me, type Session } from "../api";
import { GoogleButton } from "./GoogleButton";

interface Props {
  onLogin: (me: Me, notice: string | null) => void;
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export function Login({ onLogin }: Props) {
  const [subject, setSubject] = useState("jugador-1");
  const [error, setError] = useState<string | null>(null);

  const finish = useCallback(
    async (start: () => Promise<Session>) => {
      setError(null);
      try {
        const result = await start();
        session.set(result.access_token);
        const me = await api.me();
        onLogin(me, result.onboarding.message);
      } catch (e) {
        session.clear();
        setError(e instanceof Error ? e.message : "No se pudo iniciar sesión");
      }
    },
    [onLogin],
  );

  const withGoogle = useCallback(
    (idToken: string) => finish(() => api.googleLogin(idToken)),
    [finish],
  );

  return (
    <div className="login">
      <h1>PokéArena</h1>
      {GOOGLE_CLIENT_ID ? (
        <>
          <p className="muted">
            Inicia sesión con tu cuenta de Google; no necesitas otra contraseña.
          </p>
          <GoogleButton clientId={GOOGLE_CLIENT_ID} onToken={withGoogle} />
        </>
      ) : (
        <p className="muted">
          Inicio de sesión con Google no configurado (falta <code>VITE_GOOGLE_CLIENT_ID</code>).
        </p>
      )}
      <hr />
      <p className="muted">
        Usuario de prueba (solo existe fuera de producción). El rol de administrador se asigna por
        configuración en <code>ADMIN_SUBJECTS</code>.
      </p>
      <div className="row">
        <input value={subject} onChange={(e) => setSubject(e.target.value)} />
        <button onClick={() => finish(() => api.testToken(subject))}>
          Entrar como usuario de prueba
        </button>
      </div>
      {error && <div className="banner banner--error">{error}</div>}
    </div>
  );
}
