import { useState } from "react";
import { session } from "./api";
import { CardForm } from "./components/CardForm";
import { LocationForm } from "./components/LocationForm";
import { Login } from "./components/Login";

const TABS = { card: "Crear carta", location: "Crear ubicación" } as const;
type Tab = keyof typeof TABS;

export function App() {
  const [user, setUser] = useState<{ subject: string; roles: string[] } | null>(null);
  const [tab, setTab] = useState<Tab>("card");

  if (!user) return <Login onLogin={(subject, roles) => setUser({ subject, roles })} />;

  return (
    <div className="app">
      <header>
        <strong>PokéArena · Administración</strong>
        <nav>
          {(Object.keys(TABS) as Tab[]).map((t) => (
            <button
              key={t}
              className={t === tab ? "tab tab--active" : "tab"}
              onClick={() => setTab(t)}
            >
              {TABS[t]}
            </button>
          ))}
        </nav>
        <span className="muted">
          {user.subject} {user.roles.includes("admin") ? "(admin)" : "(sin rol admin)"}{" "}
          <button
            className="link"
            onClick={() => {
              session.clear();
              setUser(null);
            }}
          >
            Salir
          </button>
        </span>
      </header>
      <main>
        {tab === "card" && <CardForm />}
        {tab === "location" && <LocationForm />}
      </main>
    </div>
  );
}
