import client from './client'

export async function updateCurrentUser(payload) {
  const { data } = await client.patch('/auth/me/', payload)
  return data
}

export async function changeCurrentPassword(payload) {
  const { data } = await client.post('/auth/change-password/', payload)
  return data
}

export async function revokeAllSessions() {
  const { data } = await client.post('/auth/sessions/revoke-all/')
  return data
}

export async function deactivateCurrentAccount(payload) {
  const { data } = await client.post('/auth/deactivate/', payload)
  return data
}

// Directory search for finding users to invite. `q` and/or `jcode` may be
// omitted, but at least one is required for the backend to return results.
export async function searchUsers({ q, jcode } = {}) {
  const params = {}
  if (q) params.q = q
  if (jcode) params.jcode = jcode
  const { data } = await client.get('/auth/users/', { params })
  return data
}
