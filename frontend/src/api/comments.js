import client from './client'

export async function listComments(projectId) {
  const { data } = await client.get(`/projects/${projectId}/comments/`)
  return data
}

export async function createComment(projectId, { body, parent }) {
  const { data } = await client.post(`/projects/${projectId}/comments/`, { body, parent })
  return data
}

export async function updateComment(id, { body }) {
  const { data } = await client.patch(`/comments/${id}/`, { body })
  return data
}

export async function deleteComment(id) {
  await client.delete(`/comments/${id}/`)
}

export async function deleteCommentTree(id) {
  const { data } = await client.post(`/comments/${id}/delete-tree/`)
  return data
}

export async function voteComment(id, value) {
  const { data } = await client.post(`/comments/${id}/vote/`, { value })
  return data
}
