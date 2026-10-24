import { label, type Card } from "../api";

export function CardView({ card, onRetry }: { card: Card; onRetry?: () => void }) {
  const ability = card.ability;
  return (
    <article className="card">
      {card.image.small_url ? (
        <img src={card.image.small_url} alt={card.name} width={200} height={280} />
      ) : (
        <div className="card__placeholder">Imagen: {label(card.image.status)}</div>
      )}
      <div className="card__body">
        <strong>{card.name}</strong>
        <code>{card.code}</code>
        <span>
          {label(card.type)} · {label(card.rarity)}
        </span>
        <span>
          Costo {card.cost} · Poder {card.power}
        </span>
        <span title={ability ? JSON.stringify(ability.params) : ""}>
          {ability ? `${ability.code} ${ability.name}` : "—"}
          {ability?.affected_type && ` (afecta a ${label(ability.affected_type)})`}
        </span>
        <span className={card.available_to_players ? "ok" : "warn"}>
          Imagen: {label(card.image.status)}
        </span>
        {!card.available_to_players && onRetry && (
          <button className="secondary" onClick={onRetry}>
            Reintentar imagen
          </button>
        )}
      </div>
    </article>
  );
}
