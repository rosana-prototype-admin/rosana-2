import client from './client'

// Strategy rows are auto-provisioned server-side (one per InterventionType
// compatible with the Site's Opportunity's focus area) -- listing is what
// triggers that sync. There is no create/delete: only `selected` (the
// checkbox) and `details` are ever written, via updateStrategy.
export async function listStrategies(siteId) {
  const { data } = await client.get(`/sites/${siteId}/strategies/`)
  return data
}

export async function updateStrategy(id, payload) {
  const { data } = await client.patch(`/strategies/${id}/`, payload)
  return data
}
