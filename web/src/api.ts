// Cliente de la API. Todas las llamadas pasan por aquí (estándar V6).

export const CARD_TYPES = ["FUEGO", "AGUA", "PLANTA", "ELECTRICO", "PSIQUICO", "LUCHA"] as const;
export const RARITIES = ["COMUN", "POCO_COMUN", "RARA", "LEGENDARIA"] as const;
export const TRIGGERS = ["AL_REVELARSE", "CONTINUO", "NINGUNO"] as const;
export const EFFECTS = [
  "SIN_EFECTO",
  "MODIFICAR_PODER",
  "MODIFICAR_COSTO",
  "GANAR_ENERGIA",
  "MOVER",
  "DESTRUIR",
  "DESCARTAR",
  "EVOLUCIONAR",
] as const;

export const LABELS: Record<string, string> = {
  FUEGO: "Fuego",
  AGUA: "Agua",
  PLANTA: "Planta",
  ELECTRICO: "Eléctrico",
  PSIQUICO: "Psíquico",
  LUCHA: "Lucha",
  COMUN: "Común",
  POCO_COMUN: "Poco común",
  RARA: "Rara",
  LEGENDARIA: "Legendaria",
  AL_REVELARSE: "Al revelarse",
  CONTINUO: "Continuo",
  NINGUNO: "Ninguno",
  READY: "Lista",
  FAILED: "Falló",
  PENDING: "Pendiente",
};

export const label = (value: string | null | undefined) => (value ? (LABELS[value] ?? value) : "—");

export interface Ability {
  code: string;
  name: string;
  trigger: string;
  effect: string;
  affected_type: string | null;
  params: Record<string, unknown>;
}

export interface ImageInfo {
  status: string;
  url: string;
  small_url: string | null;
}

export interface Card {
  code: string;
  name: string;
  cost: number;
  power: number;
  type: string;
  rarity: string;
  ability: Ability | null;
  image: ImageInfo;
  available_to_players: boolean;
}

export interface Location {
  id: string;
  name: string;
  description: string;
  card_limit: number;
  extra_energy: { mode: string; amount: number };
  effect: { type: string; params: Record<string, unknown> };
  image: ImageInfo;
  assignable_to_matches: boolean;
}

export interface CardPage {
  items: Card[];
  next_cursor: string | null;
}

export interface FieldError {
  field: string;
  reason: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public type: string,
    message: string,
    public errors: FieldError[] = [],
  ) {
    super(message);
  }

  fieldError(field: string): string | undefined {
    return this.errors.find((e) => e.field === field || e.field.startsWith(`${field}.`))?.reason;
  }
}

const TOKEN_KEY = "pokearena.token";

export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = session.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const resp = await fetch(path, { ...init, headers });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const type =
      String(body.type ?? "")
        .split("/")
        .pop() ?? "";
    throw new ApiError(resp.status, type, body.detail ?? resp.statusText, body.errors ?? []);
  }
  return body as T;
}

export const api = {
  testToken: (subject: string) =>
    request<{ access_token: string }>("/v1/dev/tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject }),
    }),
  me: () => request<{ subject: string; roles: string[] }>("/v1/me"),
  abilities: () => request<Ability[]>("/v1/abilities"),
  createCard: (form: FormData, idempotencyKey: string) =>
    request<Card>("/v1/cards", {
      method: "POST",
      body: form,
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  retryCardImage: (code: string) =>
    request<Card>(`/v1/cards/${code}/image/retry`, { method: "POST" }),
  searchCards: (params: URLSearchParams) => request<CardPage>(`/v1/cards?${params}`),
  createLocation: (form: FormData, idempotencyKey: string) =>
    request<Location>("/v1/locations", {
      method: "POST",
      body: form,
      headers: { "Idempotency-Key": idempotencyKey },
    }),
};
