import client from './client'

export async function getOrganizationSubscription(groupId) {
  const { data } = await client.get(`/auth/organizations/${groupId}/subscription/`)
  return data
}

export async function updateOrganizationSubscription(groupId, payload) {
  const { data } = await client.patch(`/auth/organizations/${groupId}/subscription/`, payload)
  return data
}

export async function listOrganizationSubscriptionUsers(groupId) {
  const { data } = await client.get(`/auth/organizations/${groupId}/subscription/users/`)
  return data
}

export async function assignOrganizationSeat(groupId, userId) {
  const { data } = await client.post(`/auth/organizations/${groupId}/subscription/seats/`, { user_id: userId })
  return data
}

export async function releaseOrganizationSeat(groupId, seatId) {
  await client.delete(`/auth/organizations/${groupId}/subscription/seats/${seatId}/`)
}
