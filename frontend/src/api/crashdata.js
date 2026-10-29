import client from './client'

export async function listCrashConversionTables() {
  const { data } = await client.get('/crash-conversion-tables/')
  return data
}
