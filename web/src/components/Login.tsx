import { useState } from "react";
import { api, session } from "../api";

interface Props {
  onLogin: (subject: string, roles: string[]) => void;
}

export function Login({ onLogin }: Props) {
  const [subject, setSubject] = useState("admin-1");
  const [error, setError] = useState<string | null>(null);

  async function enter() {
    setError(null);
    try {
      const { access_token } = await api.testToken(subject);
      session.set(access_token);
      const me = await api.me();
      onLogin(me.subject, me.roles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión");
    }
  }

  return (
    <div className="login">
      <h1>PokéArena · Administración</h1>
      <p className="muted">
        Sesión de usuario de prueba (solo existe fuera de producción). El rol de administrador se
        asigna por configuración en <code>ADMIN_SUBJECTS</code>.
      </p>
      <div className="row">
        <input value={subject} onChange={(e) => setSubject(e.target.value)} />
        <button onClick={enter}>Entrar como usuario de prueba</button>
      </div>
      {error && <div className="banner banner--error">{error}</div>}
    </div>
  );
}
