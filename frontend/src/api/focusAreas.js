import client from './client'

// Combined "L1 - L2" options for the first Project-editor dropdown.
export async function listFocusAreaOptions() {
  const { data } = await client.get('/focus-areas/l1-l2/')
  return data
}

// A single node, so its level/parent can be resolved (e.g. to preselect the
// first dropdown from a project's already-saved focus_area).
export async function getFocusArea(id) {
  const { data } = await client.get(`/focus-areas/${id}/`)
  return data
}

// Direct children of a selected L1-L2 node, for the second Project-editor
// dropdown. Empty when the node itself is a leaf.
export async function listFocusAreaChildren(parentId) {
  const { data } = await client.get(`/focus-areas/${parentId}/children/`)
  return data
}
