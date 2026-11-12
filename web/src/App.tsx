import { useCallback, useEffect, useState } from "react";
import { api, session, type Me } from "./api";
import { CardForm } from "./components/CardForm";
import { CardSearch } from "./components/CardSearch";
import { CatalogExplorer } from "./components/CatalogExplorer";
import { LocationForm } from "./components/LocationForm";
import { Login } from "./components/Login";

const PLAYER_TABS = { catalog: "Catálogo y mi colección" } as const;
const ADMIN_TABS = {
  card: "Crear carta",
  location: "Crear ubicación",
  search: "Buscar cartas",
} as const;
type Tab = keyof typeof PLAYER_TABS | keyof typeof ADMIN_TABS;

export function App() {
  const [user, setUser] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cubes, setCubes] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("catalog");

  const onLogin = useCallback((me: Me, message: string | null) => {
    setUser(me);
    setNotice(message);
    setTab("catalog");
  }, []);

  useEffect(() => {
    if (!user) return;
    api
      .myCollection()
      .then((c) => setCubes(c.cubes))
      .catch(() => setCubes(null));
  }, [user]);

  if (!user) return <Login onLogin={onLogin} />;

  const isAdmin = user.roles.includes("admin");
  const tabs: Record<string, string> = isAdmin ? { ...PLAYER_TABS, ...ADMIN_TABS } : PLAYER_TABS;

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
          {cubes !== null && ` · ${cubes.toLocaleString("es-CR")} cubos`}
          {isAdmin && " (admin)"}{" "}
          <button
            className="link"
            onClick={() => {
              session.clear();
              setUser(null);
              setCubes(null);
            }}
          >
            Salir
          </button>
        </span>
      </header>
      <main>
        {notice && <div className="banner banner--error">{notice}</div>}
        {tab === "catalog" && <CatalogExplorer />}
        {tab === "card" && isAdmin && <CardForm />}
        {tab === "location" && isAdmin && <LocationForm />}
        {tab === "search" && isAdmin && <CardSearch />}
      </main>
    </div>
  );
}
