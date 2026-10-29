import client from './client'

export async function listProjects(opportunityId) {
  const { data } = await client.get(`/opportunities/${opportunityId}/projects/`)
  return data
}

export async function getProject(id) {
  const { data } = await client.get(`/projects/${id}/`)
  return data
}

export async function createProject(opportunityId, payload) {
  const { data } = await client.post(`/opportunities/${opportunityId}/projects/`, payload)
  return data
}

export async function updateProject(id, payload) {
  const { data } = await client.patch(`/projects/${id}/`, payload)
  return data
}

export async function deleteProject(id) {
  await client.delete(`/projects/${id}/`)
}

// Manager-only -- see backend ProjectViewSet.comments_enabled.
export async function updateCommentsEnabled(id, enabled) {
  const { data } = await client.patch(`/projects/${id}/comments-enabled/`, {
    comments_enabled: enabled,
  })
  return data
}
