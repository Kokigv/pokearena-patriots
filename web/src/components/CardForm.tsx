import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, CARD_TYPES, label, RARITIES, type Ability, type Card } from "../api";
import { CardView } from "./CardView";
import { ErrorBanner, Field } from "./Field";
import { useIdempotencyKey } from "./useIdempotencyKey";

const EMPTY = {
  name: "",
  cost: "1",
  power: "1",
  type: "FUEGO",
  rarity: "COMUN",
  ability: "HAB-000",
};

export function CardForm() {
  const [values, setValues] = useState(EMPTY);
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [abilities, setAbilities] = useState<Ability[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [created, setCreated] = useState<Card | null>(null);
  const [busy, setBusy] = useState(false);
  const [fileKey, setFileKey] = useState(0);
  const idem = useIdempotencyKey();

  useEffect(() => {
    api.abilities().then(setAbilities).catch(setError);
  }, []);

  function update(field: keyof typeof EMPTY, value: string) {
    setValues((v) => ({ ...v, [field]: value }));
    idem.renew();
  }

  function pickImage(file: File | null) {
    setImage(file);
    setPreview(file ? URL.createObjectURL(file) : null);
    idem.renew();
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.set("name", values.name);
    form.set("cost", values.cost);
    form.set("power", values.power);
    form.set("type", values.type);
    form.set("rarity", values.rarity);
    if (values.ability) form.set("ability_code", values.ability);
    if (image) form.set("image", image);
    try {
      const card = await api.createCard(form, idem.current());
      setCreated(card);
      setValues(EMPTY);
      pickImage(null);
      setFileKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "network", String(err)));
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    if (created) setCreated(await api.retryCardImage(created.code));
  }

  const ability = abilities.find((a) => a.code === values.ability);

  return (
    <div className="layout">
      <form className="panel" onSubmit={submit}>
        <h2>Crear carta</h2>
        <ErrorBanner message={error && !error.errors.length ? error.message : null} />
        <Field label="Nombre" error={error?.fieldError("name")}>
          <input value={values.name} onChange={(e) => update("name", e.target.value)} />
        </Field>
        <div className="row">
          <Field label="Costo (0 a 10)" error={error?.fieldError("cost")}>
            <input
              type="number"
              value={values.cost}
              onChange={(e) => update("cost", e.target.value)}
            />
          </Field>
          <Field label="Poder (-20 a 20)" error={error?.fieldError("power")}>
            <input
              type="number"
              value={values.power}
              onChange={(e) => update("power", e.target.value)}
            />
          </Field>
        </div>
        <div className="row">
          <Field label="Tipo" error={error?.fieldError("type")}>
            <select value={values.type} onChange={(e) => update("type", e.target.value)}>
              {CARD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {label(t)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Rareza" error={error?.fieldError("rarity")}>
            <select value={values.rarity} onChange={(e) => update("rarity", e.target.value)}>
              {RARITIES.map((r) => (
                <option key={r} value={r}>
                  {label(r)}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field
          label="Habilidad"
          error={error?.fieldError("ability_code")}
          hint={
            ability?.affected_type
              ? `Afecta a cartas de tipo ${label(ability.affected_type)}`
              : undefined
          }
        >
          <select value={values.ability} onChange={(e) => update("ability", e.target.value)}>
            <option value="">— Elegir —</option>
            {abilities.map((a) => (
              <option key={a.code} value={a.code}>
                {a.code} · {a.name}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Imagen"
          error={error?.fieldError("image")}
          hint="PNG, JPG o WebP · máximo 5 MB · proporción 5:7 · mínimo 600 × 840"
        >
          <input
            key={fileKey}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => pickImage(e.target.files?.[0] ?? null)}
          />
        </Field>
        {preview && <img className="preview" src={preview} alt="Vista previa" />}
        <button disabled={busy}>{busy ? "Creando…" : "Crear carta"}</button>
      </form>
      <section className="panel">
        <h2>Ficha</h2>
        {created ? (
          <CardView card={created} onRetry={retry} />
        ) : (
          <p className="muted">Aún no hay carta creada.</p>
        )}
      </section>
    </div>
  );
}
