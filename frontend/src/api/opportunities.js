import client from './client'

export async function listOpportunities() {
  const { data } = await client.get('/opportunities/')
  return data
}

export async function getOpportunity(id) {
  const { data } = await client.get(`/opportunities/${id}/`)
  return data
}

export async function createOpportunity(payload) {
  const { data } = await client.post('/opportunities/', payload)
  return data
}

export async function updateOpportunity(id, payload) {
  const { data } = await client.patch(`/opportunities/${id}/`, payload)
  return data
}

export async function deleteOpportunity(id) {
  await client.delete(`/opportunities/${id}/`)
}

export async function cloneOpportunity(id) {
  const { data } = await client.post(`/opportunities/${id}/clone/`)
  return data
}
