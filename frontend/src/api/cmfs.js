import client from './client'

export async function listCmfs() {
  const { data } = await client.get('/cmfs/')
  return data
}

export async function getCmf(id) {
  const { data } = await client.get(`/cmfs/${id}/`)
  return data
}

export async function getCmfConfig() {
  const { data } = await client.get('/cmfs/config/')
  return data
}

export async function resolveCmf(code) {
  const { data } = await client.get('/cmfs/resolve/', { params: { code } })
  return data
}

export async function createCmf(payload) {
  const { data } = await client.post('/cmfs/', payload)
  return data
}

export async function updateCmf(id, payload) {
  const { data } = await client.patch(`/cmfs/${id}/`, payload)
  return data
}

export async function deleteCmf(id) {
  await client.delete(`/cmfs/${id}/`)
}
