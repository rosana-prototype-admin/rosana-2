import client from './client'

// All focus areas, for use by forms that need a single flat list of choices.
export async function listFocusAreas() {
  const { data } = await client.get('/focus-areas/')
  return data
}

// Combined "L1 - L2" options for the first Opportunity-editor dropdown.
export async function listFocusAreaOptions() {
  const { data } = await client.get('/focus-areas/l1-l2/')
  return data
}

// A single node, so its level/parent can be resolved (e.g. to preselect the
// first dropdown from an opportunity's already-saved focus_area).
export async function getFocusArea(id) {
  const { data } = await client.get(`/focus-areas/${id}/`)
  return data
}

// Direct children of a selected L1-L2 node, for the second Opportunity-editor
// dropdown. Empty when the node itself is a leaf.
export async function listFocusAreaChildren(parentId) {
  const { data } = await client.get(`/focus-areas/${parentId}/children/`)
  return data
}
