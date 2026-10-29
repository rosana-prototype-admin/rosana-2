import client from './client'

export async function listNotifications() {
  const { data } = await client.get('/notifications/')
  return data
}

export async function acceptNotification(id) {
  const { data } = await client.post(`/notifications/${id}/accept/`)
  return data
}

export async function declineNotification(id) {
  const { data } = await client.post(`/notifications/${id}/decline/`)
  return data
}
