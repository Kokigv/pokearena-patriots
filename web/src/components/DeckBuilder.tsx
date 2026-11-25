import { useEffect, useState } from "react";
import { api, type CatalogCard, type Deck } from "../api";

export function DeckBuilder() {
  const [cards, setCards] = useState<CatalogCard[]>([]);
  const [decks, setDecks] = useState<Deck[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  const refresh = async () => {
    const collection = await api.myCollection();
    const all: CatalogCard[] = [];
    let cursor: string | null = null;
    do {
      const params = new URLSearchParams({ owned: "true", limit: "100" });
      if (cursor) params.set("cursor", cursor);
      const page = await api.catalog(params);
      all.push(...page.items);
      cursor = page.next_cursor;
    } while (cursor);
    setCards(all.filter((c) => collection.cards.some((owned) => owned.card_code === c.code)));
    setDecks(await api.decks());
  };

  useEffect(() => { refresh().catch((e: Error) => setMessage(e.message)); }, []);

  const toggle = (code: string) => {
    setChosen((prev) => prev.includes(code) ? prev.filter((c) => c !== code) : prev.length < 12 ? [...prev, code] : prev);
  };
  const save = async () => {
    try {
      await api.createDeck({ name: name.trim(), card_codes: chosen });
      setChosen([]);
      setName("");
      setMessage("Deck guardado correctamente");
      await refresh();
    } catch (e) { setMessage((e as Error).message); }
  };

  return <section>
    <h2>Mis decks</h2>
    {decks.length === 0 ? <p>Aún no tenés decks.</p> : <ul>{decks.map((d) => <li key={d.id}>{d.name} · {d.card_codes.length} cartas</li>)}</ul>}
    <h3>Crear Deck ({chosen.length}/12 cartas distintas)</h3>
    <label>Nombre del deck <input value={name} maxLength={60} onChange={(e) => setName(e.target.value)} /></label>
    <div className="deck-grid">{cards.map((c) => <button key={c.code} type="button"
      aria-pressed={chosen.includes(c.code)}
      className={chosen.includes(c.code) ? "deck-card deck-card--chosen" : "deck-card"}
      onClick={() => toggle(c.code)}>{c.name} ({c.code})</button>)}</div>
    <button type="button" disabled={chosen.length !== 12 || !name.trim()} onClick={save}>Guardar deck</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
