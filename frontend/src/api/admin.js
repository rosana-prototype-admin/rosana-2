import client from './client'

export async function listAdminUsers(params = {}) {
  const { data } = await client.get('/auth/admin/users/', { params })
  return data
}

export async function updateAdminUser(id, payload) {
  const { data } = await client.patch(`/auth/admin/users/${id}/`, payload)
  return data
}

export async function resendAdminVerification(id) {
  const { data } = await client.post(`/auth/admin/users/${id}/resend-verification/`)
  return data
}

export async function sendAdminPasswordReset(id) {
  const { data } = await client.post(`/auth/admin/users/${id}/send-password-reset/`)
  return data
}

export async function getAdminSubscription(id) {
  const { data } = await client.get(`/auth/admin/users/${id}/subscription/`)
  return data
}

export async function updateAdminSubscription(id, payload) {
  const { data } = await client.patch(`/auth/admin/users/${id}/subscription/`, payload)
  return data
}

export async function listAdminContracts(id) {
  const { data } = await client.get(`/auth/admin/users/${id}/contracts/`)
  return data
}

export async function createAdminContract(id, payload) {
  const { data } = await client.post(`/auth/admin/users/${id}/contracts/`, payload)
  return data
}
