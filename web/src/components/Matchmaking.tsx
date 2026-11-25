import { useEffect, useState } from "react";
import { api, gameplay, type Deck, type MatchSearch } from "../api";

export function Matchmaking() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState<MatchSearch | null>(null);
  const [message, setMessage] = useState("");
  const searchId = search?.search_id;
  const searchStatus = search?.status;

  // Cargar los decks disponibles del jugador
  useEffect(() => {
    api
      .decks()
      .then(setDecks)
      .catch((e: Error) => setMessage(e.message));
  }, []);

  // Consultar el estado de búsqueda cada 3 segundos
  useEffect(() => {
    if (!searchId || searchStatus !== "WAITING") return;

    let running = true;

    let timer: number;
    const poll = async () => {
      try {
        const state = await gameplay.status(searchId);

        if (running) {
          setSearch((current) =>
            current?.search_id === searchId && current.status === "WAITING" ? state : current,
          );
        }
      } catch (e) {
        if (running) {
          setMessage((e as Error).message);
        }
      } finally {
        if (running) timer = window.setTimeout(poll, 3000);
      }
    };

    timer = window.setTimeout(poll, 3000);

    return () => {
      running = false;
      window.clearTimeout(timer);
    };
  }, [searchId, searchStatus]);
  const begin = async () => {
    try {
      setSearch(await gameplay.startSearch(selected));
      setMessage("");
    } catch (e) {
      setMessage((e as Error).message);
    }
  };
  const cancel = async () => {
    if (!search) return;
    try {
      setSearch(await gameplay.cancel(search.search_id));
    } catch (e) {
      setMessage((e as Error).message);
    }
  };
  const bot = async () => {
    if (!search) return;
    try {
      setSearch(await gameplay.acceptBot(search.search_id));
    } catch (e) {
      setMessage((e as Error).message);
    }
  };
  return (
    <section>
      <h2>Buscar partida clasificatoria</h2>
      <label>
        Elegí un deck:{" "}
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Seleccionar deck</option>
          {decks.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <button disabled={!selected || search?.status === "WAITING"} onClick={begin}>
        Buscar rival
      </button>
      {search && (
        <div role="status">
          <p>Estado: {search.status}</p>
          {search.match_id && <p>Partida: {search.match_id}</p>}
          {search.status === "WAITING" && <button onClick={cancel}>Cancelar búsqueda</button>}
          {search.bot_available && search.status === "WAITING" && (
            <button onClick={bot}>Jugar contra bot</button>
          )}
        </div>
      )}
      {message && <p role="alert">{message}</p>}
    </section>
  );
}
