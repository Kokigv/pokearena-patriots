import { useCallback, useState } from "react";
import { session, type Me } from "./api";
import { CardForm } from "./components/CardForm";
import { CardSearch } from "./components/CardSearch";
import { LocationForm } from "./components/LocationForm";
import { Login } from "./components/Login";

const ADMIN_TABS = {
  card: "Crear carta",
  location: "Crear ubicación",
  search: "Buscar cartas",
} as const;
type Tab = keyof typeof ADMIN_TABS;

export function App() {
  const [user, setUser] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("card");

  const onLogin = useCallback((me: Me, message: string | null) => {
    setUser(me);
    setNotice(message);
  }, []);

  if (!user) return <Login onLogin={onLogin} />;

  const isAdmin = user.roles.includes("admin");
  const tabs: Record<string, string> = isAdmin ? ADMIN_TABS : {};

  return (
    <div className="app">
      <header>
        <strong>PokéArena</strong>
        <nav>
          {(Object.keys(tabs) as Tab[]).map((t) => (
            <button
              key={t}
              className={t === tab ? "tab tab--active" : "tab"}
              onClick={() => setTab(t)}
            >
              {tabs[t]}
            </button>
          ))}
        </nav>
        <span className="muted">
          {user.player.display_name} · Elo {user.player.elo}
          {isAdmin && " (admin)"}{" "}
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
        {notice && <div className="banner banner--error">{notice}</div>}
        {tab === "card" && isAdmin && <CardForm />}
        {tab === "location" && isAdmin && <LocationForm />}
        {tab === "search" && isAdmin && <CardSearch />}
      </main>
    </div>
  );
}
