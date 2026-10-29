import client from './client'

export async function listSites(projectId) {
  const { data } = await client.get(`/projects/${projectId}/sites/`)
  return data
}

export async function getSite(id) {
  const { data } = await client.get(`/sites/${id}/`)
  return data
}

export async function listAvailableJcodes(siteId) {
  const { data } = await client.get(`/sites/${siteId}/available-jcodes/`)
  return data
}

export async function createSite(projectId, payload) {
  const { data } = await client.post(`/projects/${projectId}/sites/`, payload)
  return data
}

export async function updateSite(id, payload) {
  const { data } = await client.patch(`/sites/${id}/`, payload)
  return data
}

export async function deleteSite(id) {
  await client.delete(`/sites/${id}/`)
}
