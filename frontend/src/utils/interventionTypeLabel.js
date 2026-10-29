export function interventionTypeLabel(interventionType) {
  return interventionType.category ? `${interventionType.category} — ${interventionType.name}` : interventionType.name
}
