export function entitlementDenialMessage(entitlement, resourceLabel = 'this feature') {
  if (!entitlement || !entitlement.plan_code || entitlement.plan_code === 'none' || entitlement.access_state === 'unlicensed') {
    return `This organization does not have an active subscription for ${resourceLabel}.`
  }
  if (entitlement.access_state === 'expired_grace') {
    return 'This subscription is in its renewal grace period. Existing records can be viewed, but changes are disabled until renewal.'
  }
  if (entitlement.access_state !== 'active') {
    return 'This organization account is locked or restricted pending subscription renewal.'
  }
  if (entitlement.rosana_role === 'technical_user' && !entitlement.has_technical_seat) {
    return 'A Technical User seat is required before you can analyze or modify technical records.'
  }
  return `Your Rosana Role or group permissions do not allow you to modify ${resourceLabel}.`
}
