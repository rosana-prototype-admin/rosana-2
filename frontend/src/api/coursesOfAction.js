import client from './client'

export async function listCoursesOfAction(projectId) {
  const { data } = await client.get(`/projects/${projectId}/courses-of-action/`)
  return data
}

export async function getCourseOfAction(id) {
  const { data } = await client.get(`/courses-of-action/${id}/`)
  return data
}

export async function createCourseOfAction(projectId, payload) {
  const { data } = await client.post(`/projects/${projectId}/courses-of-action/`, payload)
  return data
}

export async function updateCourseOfAction(id, payload) {
  const { data } = await client.patch(`/courses-of-action/${id}/`, payload)
  return data
}

export async function deleteCourseOfAction(id) {
  await client.delete(`/courses-of-action/${id}/`)
}

export async function cloneCourseOfAction(id) {
  const { data } = await client.post(`/courses-of-action/${id}/clone/`)
  return data
}
