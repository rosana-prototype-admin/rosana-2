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

export async function listAdminGroups(params = {}) {
  const { data } = await client.get('/auth/admin/groups/', { params })
  return data
}

export async function getAdminGroupSubscription(groupId) {
  const { data } = await client.get(`/auth/admin/groups/${groupId}/subscription/`)
  return data
}

export async function updateAdminGroupSubscription(groupId, payload) {
  const { data } = await client.patch(`/auth/admin/groups/${groupId}/subscription/`, payload)
  return data
}

export async function listAdminGroupContracts(groupId) {
  const { data } = await client.get(`/auth/admin/groups/${groupId}/contracts/`)
  return data
}

export async function createAdminGroupContract(groupId, payload) {
  const { data } = await client.post(`/auth/admin/groups/${groupId}/contracts/`, payload)
  return data
}

export async function listAdminGroupSeats(groupId) {
  const { data } = await client.get(`/auth/admin/groups/${groupId}/seats/`)
  return data
}

export async function assignAdminGroupSeat(groupId, userId) {
  const { data } = await client.post(`/auth/admin/groups/${groupId}/seats/`, { user_id: userId })
  return data
}

export async function listAdminAuditEvents(params = {}) {
  const { data } = await client.get('/auth/admin/audit/', { params })
  return data
}
