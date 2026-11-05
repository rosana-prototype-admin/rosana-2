import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import client from '../api/client'
import '../styles/authForm.css'
import '../styles/formFeedback.css'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const uid = searchParams.get('uid') || ''
  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setIsSubmitting(true)
    try {
      await client.post('/auth/password-reset/confirm/', {
        uid,
        token,
        new_password: password,
      })
      setSuccess(true)
    } catch (err) {
      const data = err.response?.data
      setError(data?.new_password?.[0] || data?.detail || 'This reset link is invalid or expired.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>Rosana</h1>
        <p className="auth-subtitle">Choose a new password</p>
        {success ? (
          <>
            <p className="form-success">Your password has been reset.</p>
            <p className="auth-switch"><Link to="/login">Go to sign in</Link></p>
          </>
        ) : (
          <>
            {error && <p className="form-error" role="alert">{error}</p>}
            <label className="auth-field">
              <span>New password</span>
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                autoFocus
              />
            </label>
            <label className="auth-field">
              <span>Confirm new password</span>
              <input
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </label>
            <button type="submit" className="auth-submit" disabled={isSubmitting || !uid || !token}>
              {isSubmitting ? 'Saving...' : 'Set new password'}
            </button>
          </>
        )}
      </form>
    </main>
  )
}
