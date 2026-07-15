import client from './client'

export async function listProjects() {
  const { data } = await client.get('/projects/')
  return data
}

export async function getProject(id) {
  const { data } = await client.get(`/projects/${id}/`)
  return data
}

export async function createProject(payload) {
  const { data } = await client.post('/projects/', payload)
  return data
}

export async function updateProject(id, payload) {
  const { data } = await client.patch(`/projects/${id}/`, payload)
  return data
}

export async function deleteProject(id) {
  await client.delete(`/projects/${id}/`)
}

export async function cloneProject(id) {
  const { data } = await client.post(`/projects/${id}/clone/`)
  return data
}
