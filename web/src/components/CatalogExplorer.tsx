import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, CARD_TYPES, label, type CatalogCard } from "../api";
import { ErrorBanner, Field } from "./Field";

const FILTERS = { type: "", cost_min: "", cost_max: "", owned: false };
type Filters = typeof FILTERS;

function toParams(f: Filters, cursor: string | null): URLSearchParams {
  const params = new URLSearchParams({ limit: "24" });
  if (f.type) params.set("type", f.type);
  if (f.cost_min.trim()) params.set("cost_min", f.cost_min.trim());
  if (f.cost_max.trim()) params.set("cost_max", f.cost_max.trim());
  if (f.owned) params.set("owned", "true");
  if (cursor) params.set("cursor", cursor);
  return params;
}

function CatalogCardView({ card }: { card: CatalogCard }) {
  return (
    <article className={card.owned ? "card card--owned" : "card card--missing"}>
      {/* Versión grande de la imagen (criterio de la US 124). */}
      <img src={card.image_url} alt={card.name} width={200} height={280} loading="lazy" />
      <div className="card__body">
        <strong>{card.name}</strong>
        <code>{card.code}</code>
        <span>
          {label(card.type)} · {label(card.rarity)}
        </span>
        <span>
          Costo {card.cost} · Poder {card.power}
        </span>
        <span>{card.ability ? card.ability.name : "Sin habilidad"}</span>
        <span className={card.owned ? "ok" : "muted"}>
          {card.owned
            ? `La tienes · ${card.copies} ${card.copies === 1 ? "copia" : "copias"}`
            : "No la tienes"}
        </span>
      </div>
    </article>
  );
}

export function CatalogExplorer() {
  const [filters, setFilters] = useState(FILTERS);
  const [applied, setApplied] = useState<Filters>(FILTERS);
  const [cards, setCards] = useState<CatalogCard[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (f: Filters, from: string | null) => {
    setBusy(true);
    setError(null);
    try {
      const page = await api.catalog(toParams(f, from));
      setCards((prev) => (from ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setApplied(f);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "network", String(err)));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load(FILTERS, null);
  }, [load]);

  function submit(e: FormEvent) {
    e.preventDefault();
    load(filters, null);
  }

  return (
    <div className="search">
      <form className="panel filters" onSubmit={submit}>
        <h2>Catálogo y mi colección</h2>
        <ErrorBanner message={error && !error.errors.length ? error.message : null} />
        {error?.errors.map((e) => (
          <div key={e.field} className="banner banner--error">
            {e.field}: {e.reason}
          </div>
        ))}
        <div className="grid">
          <Field label="Tipo">
            <select
              value={filters.type}
              onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))}
            >
              <option value="">Todos</option>
              {CARD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {label(t)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Costo mín.">
            <input
              type="number"
              value={filters.cost_min}
              onChange={(e) => setFilters((f) => ({ ...f, cost_min: e.target.value }))}
            />
          </Field>
          <Field label="Costo máx.">
            <input
              type="number"
              value={filters.cost_max}
              onChange={(e) => setFilters((f) => ({ ...f, cost_max: e.target.value }))}
            />
          </Field>
          <label className="check">
            <input
              type="checkbox"
              checked={filters.owned}
              onChange={(e) => setFilters((f) => ({ ...f, owned: e.target.checked }))}
            />
            Solo mis cartas
          </label>
        </div>
        <div className="row">
          <button disabled={busy}>Filtrar</button>
          <button type="button" className="secondary" onClick={() => setFilters(FILTERS)}>
            Limpiar
          </button>
        </div>
      </form>
      <div className="results">
        {cards.map((c) => (
          <CatalogCardView key={c.code} card={c} />
        ))}
      </div>
      {!busy && cards.length === 0 && (
        <p className="muted">
          {applied.owned
            ? "No tienes cartas con esos filtros."
            : "Ninguna carta cumple los filtros."}
        </p>
      )}
      {cursor && (
        <button className="more" disabled={busy} onClick={() => load(applied, cursor)}>
          Cargar más
        </button>
      )}
    </div>
  );
}
