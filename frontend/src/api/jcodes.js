import client from './client'

export async function listJcodes(params = {}) {
  const { data } = await client.get('/jcodes/', { params })
  return data
}
