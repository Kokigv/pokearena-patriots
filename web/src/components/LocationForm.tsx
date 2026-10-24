import { useState, type FormEvent } from "react";
import { api, ApiError, CARD_TYPES, label, type Location } from "../api";
import { ErrorBanner, Field } from "./Field";
import { useIdempotencyKey } from "./useIdempotencyKey";

const EFFECTS: Record<string, string> = {
  NINGUNO: "Sin efecto",
  BONIFICACION_POR_TIPO: "Bonificación por tipo",
  MODIFICADOR_DE_COSTO: "Modificador de costo",
  RESTRICCION_POR_TURNO: "Restricción por turno",
};

const EMPTY = {
  name: "",
  description: "",
  card_limit: "4",
  extra_energy_mode: "FIJA",
  extra_energy_amount: "0",
  effect_type: "NINGUNO",
  card_type: "AGUA",
  amount: "1",
  turns: [] as number[],
};

function effectParams(v: typeof EMPTY): Record<string, unknown> {
  switch (v.effect_type) {
    case "BONIFICACION_POR_TIPO":
      return { card_type: v.card_type, amount: Number(v.amount) };
    case "MODIFICADOR_DE_COSTO":
      return v.card_type
        ? { amount: Number(v.amount), card_type: v.card_type }
        : { amount: Number(v.amount) };
    case "RESTRICCION_POR_TURNO":
      return { turns: v.turns };
    default:
      return {};
  }
}

export function LocationForm() {
  const [values, setValues] = useState(EMPTY);
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [created, setCreated] = useState<Location | null>(null);
  const [busy, setBusy] = useState(false);
  const [fileKey, setFileKey] = useState(0);
  const idem = useIdempotencyKey();

  function update<K extends keyof typeof EMPTY>(field: K, value: (typeof EMPTY)[K]) {
    setValues((v) => ({ ...v, [field]: value }));
    idem.renew();
  }

  function toggleTurn(turn: number) {
    update(
      "turns",
      values.turns.includes(turn)
        ? values.turns.filter((t) => t !== turn)
        : [...values.turns, turn].sort(),
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData();
    for (const key of [
      "name",
      "description",
      "card_limit",
      "extra_energy_mode",
      "extra_energy_amount",
      "effect_type",
    ] as const) {
      form.set(key, values[key]);
    }
    form.set("effect_params", JSON.stringify(effectParams(values)));
    if (image) form.set("image", image);
    try {
      setCreated(await api.createLocation(form, idem.current()));
      setValues(EMPTY);
      setImage(null);
      setFileKey((k) => k + 1);
      idem.renew();
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "network", String(err)));
    } finally {
      setBusy(false);
    }
  }

  const energyRange =
    values.extra_energy_mode === "FIJA" ? "0 a 3 por turno" : "0 a 2 por cada carta propia";

  return (
    <div className="layout">
      <form className="panel" onSubmit={submit}>
        <h2>Crear ubicación</h2>
        <ErrorBanner message={error && !error.errors.length ? error.message : null} />
        <Field label="Nombre" error={error?.fieldError("name")}>
          <input value={values.name} onChange={(e) => update("name", e.target.value)} />
        </Field>
        <Field label="Descripción" error={error?.fieldError("description")}>
          <textarea
            value={values.description}
            onChange={(e) => update("description", e.target.value)}
          />
        </Field>
        <div className="row">
          <Field
            label="Límite de cartas por jugador (0 a 5)"
            error={error?.fieldError("card_limit")}
          >
            <input
              type="number"
              value={values.card_limit}
              onChange={(e) => update("card_limit", e.target.value)}
            />
          </Field>
          <Field label="Energía extra" error={error?.fieldError("extra_energy_mode")}>
            <select
              value={values.extra_energy_mode}
              onChange={(e) => update("extra_energy_mode", e.target.value)}
            >
              <option value="FIJA">Fija</option>
              <option value="POR_CARTA">Por carta</option>
            </select>
          </Field>
          <Field label="Monto" error={error?.fieldError("extra_energy_amount")} hint={energyRange}>
            <input
              type="number"
              value={values.extra_energy_amount}
              onChange={(e) => update("extra_energy_amount", e.target.value)}
            />
          </Field>
        </div>
        <Field label="Efecto" error={error?.fieldError("effect_type")}>
          <select
            value={values.effect_type}
            onChange={(e) => update("effect_type", e.target.value)}
          >
            {Object.entries(EFFECTS).map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        </Field>
        {(values.effect_type === "BONIFICACION_POR_TIPO" ||
          values.effect_type === "MODIFICADOR_DE_COSTO") && (
          <div className="row">
            <Field label="Tipo de carta" error={error?.fieldError("effect_params.card_type")}>
              <select
                value={values.card_type}
                onChange={(e) => update("card_type", e.target.value)}
              >
                {values.effect_type === "MODIFICADOR_DE_COSTO" && <option value="">Todos</option>}
                {CARD_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {label(t)}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label={
                values.effect_type === "BONIFICACION_POR_TIPO" ? "Poder (-5 a 5)" : "Costo (-5 a 5)"
              }
              error={error?.fieldError("effect_params.amount")}
            >
              <input
                type="number"
                value={values.amount}
                onChange={(e) => update("amount", e.target.value)}
              />
            </Field>
          </div>
        )}
        {values.effect_type === "RESTRICCION_POR_TURNO" && (
          <Field
            label="Turnos sin poder jugar cartas"
            error={error?.fieldError("effect_params.turns")}
          >
            <div className="row">
              {[1, 2, 3, 4, 5, 6].map((t) => (
                <label key={t} className="check">
                  <input
                    type="checkbox"
                    checked={values.turns.includes(t)}
                    onChange={() => toggleTurn(t)}
                  />{" "}
                  {t}
                </label>
              ))}
            </div>
          </Field>
        )}
        <Field
          label="Imagen"
          error={error?.fieldError("image")}
          hint="PNG, JPG o WebP · máximo 5 MB · proporción 4:3 · mínimo 800 × 600"
        >
          <input
            key={fileKey}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => {
              setImage(e.target.files?.[0] ?? null);
              idem.renew();
            }}
          />
        </Field>
        <button disabled={busy}>{busy ? "Creando…" : "Crear ubicación"}</button>
      </form>
      <section className="panel">
        <h2>Ubicación creada</h2>
        {created ? (
          <article className="location">
            {created.image.small_url && (
              <img src={created.image.small_url} alt={created.name} width={320} height={240} />
            )}
            <strong>{created.name}</strong>
            <span>{created.description}</span>
            <span>Límite: {created.card_limit} cartas por jugador</span>
            <span>
              Energía extra: {created.extra_energy.mode === "FIJA" ? "fija" : "por carta"}{" "}
              {created.extra_energy.amount}
            </span>
            <span>
              Efecto: {EFFECTS[created.effect.type]} {JSON.stringify(created.effect.params)}
            </span>
            <span className={created.assignable_to_matches ? "ok" : "warn"}>
              Imagen: {label(created.image.status)}
            </span>
          </article>
        ) : (
          <p className="muted">Aún no hay ubicación creada.</p>
        )}
      </section>
    </div>
  );
}
