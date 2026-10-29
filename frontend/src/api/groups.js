import client from './client'

export async function listGroups() {
  const { data } = await client.get('/groups/')
  return data
}

export async function listMyGroups() {
  const { data } = await client.get('/groups/mine/')
  return data
}

// Shared org-chart catalog. `q` filters by name (case-insensitive substring).
export async function searchGroups(q) {
  const { data } = await client.get('/groups/', { params: q ? { q } : {} })
  return data
}

export async function getGroup(id) {
  const { data } = await client.get(`/groups/${id}/`)
  return data
}

// Direct (non-transitive) memberships, matching the manager-must-be-a-
// lead_agency-member validation the backend enforces on Opportunity.
export async function listGroupMembers(groupId) {
  const { data } = await client.get(`/groups/${groupId}/members/`)
  return data
}

export async function createGroup(payload) {
  const { data } = await client.post('/groups/', payload)
  return data
}

export async function updateGroup(id, payload) {
  const { data } = await client.patch(`/groups/${id}/`, payload)
  return data
}

export async function deleteGroup(id) {
  await client.delete(`/groups/${id}/`)
}

// Sends a pending invitation (Notification) rather than adding the member
// directly -- the invitee must accept it before a Membership is created.
export async function inviteGroupMember(groupId, { userId, roles }) {
  const { data } = await client.post(`/groups/${groupId}/invite/`, { user_id: userId, roles })
  return data
}

// Sends a pending join request (Notification) to the group's admin.
export async function requestToJoinGroup(groupId) {
  const { data } = await client.post(`/groups/${groupId}/request-to-join/`)
  return data
}

export async function changeGroupMemberRoles(groupId, userId, roles) {
  const { data } = await client.patch(`/groups/${groupId}/members/${userId}/`, { roles })
  return data
}

export async function removeGroupMember(groupId, userId) {
  await client.delete(`/groups/${groupId}/members/${userId}/`)
}

export async function setGroupAdmin(groupId, userId) {
  const { data } = await client.post(`/groups/${groupId}/set-admin/`, { user_id: userId })
  return data
}

export async function updateGroupJcodes(groupId, jcodeIds) {
  const { data } = await client.patch(`/groups/${groupId}/jcodes/`, { jcode_ids: jcodeIds })
  return data
}
