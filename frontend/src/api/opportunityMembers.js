import client from './client'

export async function listMembers(opportunityId) {
  const { data } = await client.get(`/opportunities/${opportunityId}/members/`)
  return data
}

export async function inviteMember(opportunityId, { identifier, role }) {
  const { data } = await client.post(`/opportunities/${opportunityId}/members/`, { identifier, role })
  return data
}

// Adds every member of a Group as a stakeholder (read-only viewer) in one call.
export async function inviteGroup(opportunityId, groupId) {
  const { data } = await client.post(`/opportunities/${opportunityId}/invite-group/`, { group_id: groupId })
  return data
}

export async function changeMemberRole(opportunityId, userId, role) {
  const { data } = await client.patch(`/opportunities/${opportunityId}/members/${userId}/`, { role })
  return data
}

export async function removeMember(opportunityId, userId) {
  await client.delete(`/opportunities/${opportunityId}/members/${userId}/`)
}
