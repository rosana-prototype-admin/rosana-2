const FRACTION_FORMATTERS = {
  0: new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
    useGrouping: true,
  }),
  1: new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
    useGrouping: true,
  }),
  2: new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
    useGrouping: true,
  }),
}

const THREE_SIGNIFICANT_DIGIT_FORMATTER = new Intl.NumberFormat('en-US', {
  maximumSignificantDigits: 3,
  useGrouping: true,
})

/**
 * Format an annual outcome using the display rules from the outcome spec.
 * Calculations should pass the unrounded value to this function.
 */
export function formatAnnualOutcome(value, outcome) {
  if (value === '' || value === null || value === undefined) return ''

  const number = Number(value)
  if (!Number.isFinite(number) || number < 0) return ''
  if (number === 0) return '0'
  if (number < 0.01) return '<0.01'
  if (number < 10) return FRACTION_FORMATTERS[2].format(number)
  if (number < 100) return FRACTION_FORMATTERS[1].format(number)

  // Fatalities retain whole-person precision at every magnitude. Other
  // outcomes use three significant digits once they reach four digits.
  if (outcome === 'fatalities' || number < 1000) {
    return FRACTION_FORMATTERS[0].format(number)
  }

  return THREE_SIGNIFICANT_DIGIT_FORMATTER.format(number)
}

