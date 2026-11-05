import { useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'
import '../styles/authForm.css'
import '../styles/formFeedback.css'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await client.post('/auth/password-reset/', { email: email.trim() })
      setSubmitted(true)
    } catch (err) {
      setError(err.response?.data?.email?.[0] || 'Enter a valid email address.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Rosana</h1>
        <p className="auth-subtitle">Reset your password</p>
        {submitted ? (
          <>
            <p>If an account exists for that email, we sent a password reset link.</p>
            <p className="auth-switch"><Link to="/login">Return to sign in</Link></p>
          </>
        ) : (
          <>
            {error && <p className="form-error" role="alert">{error}</p>}
            <label className="auth-field">
              <span>Email</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoFocus
              />
            </label>
            <button type="submit" className="auth-submit" disabled={isSubmitting}>
              {isSubmitting ? 'Sending...' : 'Send reset link'}
            </button>
            <p className="auth-switch"><Link to="/login">Return to sign in</Link></p>
          </>
        )}
      </form>
    </main>
  )
}
