import { useState, type FormEvent } from "react";
import { api, ApiError, CARD_TYPES, EFFECTS, label, RARITIES, TRIGGERS, type Card } from "../api";
import { CardView } from "./CardView";
import { ErrorBanner, Field } from "./Field";

const FILTERS = {
  code: "",
  name: "",
  cost_min: "",
  cost_max: "",
  power_min: "",
  power_max: "",
  type: "",
  rarity: "",
  ability_code: "",
  trigger: "",
  effect: "",
};
type Filters = typeof FILTERS;

function toParams(filters: Filters, cursor: string | null): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters))
    if (value.trim()) params.set(key, value.trim());
  if (cursor) params.set("cursor", cursor);
  return params;
}

export function CardSearch() {
  const [filters, setFilters] = useState(FILTERS);
  const [applied, setApplied] = useState<Filters | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(f: Filters, from: string | null) {
    setBusy(true);
    setError(null);
    try {
      const page = await api.searchCards(toParams(f, from));
      setCards((prev) => (from ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setApplied(f);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "network", String(err)));
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    load(filters, null);
  }

  const set = (field: keyof Filters) => (e: { target: { value: string } }) =>
    setFilters((f) => ({ ...f, [field]: e.target.value }));

  const select = (field: keyof Filters, options: readonly string[]) => (
    <select value={filters[field]} onChange={set(field)}>
      <option value="">Todos</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {label(o)}
        </option>
      ))}
    </select>
  );

  return (
    <div className="search">
      <form className="panel filters" onSubmit={submit}>
        <h2>Buscar cartas</h2>
        <ErrorBanner message={error && !error.errors.length ? error.message : null} />
        {error?.errors.map((e) => (
          <div key={e.field} className="banner banner--error">
            {e.field}: {e.reason}
          </div>
        ))}
        <div className="grid">
          <Field label="Código">
            <input placeholder="PKA-FUE" value={filters.code} onChange={set("code")} />
          </Field>
          <Field label="Nombre">
            <input
              placeholder="sin tildes ni mayúsculas"
              value={filters.name}
              onChange={set("name")}
            />
          </Field>
          <Field label="Costo mín.">
            <input type="number" value={filters.cost_min} onChange={set("cost_min")} />
          </Field>
          <Field label="Costo máx.">
            <input type="number" value={filters.cost_max} onChange={set("cost_max")} />
          </Field>
          <Field label="Poder mín.">
            <input type="number" value={filters.power_min} onChange={set("power_min")} />
          </Field>
          <Field label="Poder máx.">
            <input type="number" value={filters.power_max} onChange={set("power_max")} />
          </Field>
          <Field label="Tipo">{select("type", CARD_TYPES)}</Field>
          <Field label="Rareza">{select("rarity", RARITIES)}</Field>
          <Field label="Habilidad (código)">
            <input
              placeholder="HAB-000"
              value={filters.ability_code}
              onChange={set("ability_code")}
            />
          </Field>
          <Field label="Disparador">{select("trigger", TRIGGERS)}</Field>
          <Field label="Efecto">{select("effect", EFFECTS)}</Field>
        </div>
        <div className="row">
          <button disabled={busy}>Buscar</button>
          <button type="button" className="secondary" onClick={() => setFilters(FILTERS)}>
            Limpiar
          </button>
        </div>
      </form>
      {applied && (
        <p className="muted">
          {cards.length} {cards.length === 1 ? "carta" : "cartas"}
          {cursor ? " (hay más)" : ""}
        </p>
      )}
      <div className="results">
        {cards.map((c) => (
          <CardView key={c.code} card={c} />
        ))}
      </div>
      {applied && cards.length === 0 && (
        <p className="muted">Ninguna carta cumple los criterios.</p>
      )}
      {cursor && applied && (
        <button className="more" disabled={busy} onClick={() => load(applied, cursor)}>
          Cargar más
        </button>
      )}
    </div>
  );
}
