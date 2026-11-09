import client from './client'

export async function listAdminUsers(params = {}) {
  const { data } = await client.get('/auth/admin/users/', { params })
  return data
}

export async function updateAdminUser(id, payload) {
  const { data } = await client.patch(`/auth/admin/users/${id}/`, payload)
  return data
}
