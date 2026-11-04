import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import client from '../api/client'
import '../styles/authForm.css'
import '../styles/formFeedback.css'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const [state, setState] = useState(() => (
    searchParams.has('uid') && searchParams.has('token') ? 'verifying' : 'sent'
  ))
  const [error, setError] = useState('')

  useEffect(() => {
    const uid = searchParams.get('uid')
    const token = searchParams.get('token')
    if (!uid || !token) return

    let isCurrent = true
    client.post('/auth/verify-email/', { uid, token })
      .then(() => {
        if (isCurrent) setState('verified')
      })
      .catch((err) => {
        if (!isCurrent) return
        setError(err.response?.data?.detail || 'This verification link is invalid or expired.')
        setState('error')
      })

    return () => {
      isCurrent = false
    }
  }, [searchParams])

  return (
    <main className="auth-page">
      <section className="auth-card" aria-live="polite">
        <h1>Rosana</h1>
        {state === 'sent' && (
          <>
            <p className="auth-subtitle">Check your email</p>
            <p>We sent you a verification link. Follow it to activate your account.</p>
          </>
        )}
        {state === 'verifying' && <p className="auth-subtitle">Verifying your email...</p>}
        {state === 'verified' && (
          <>
            <p className="auth-subtitle">Email verified</p>
            <p className="form-success">Your account is active. You can now sign in.</p>
            <Link className="auth-submit" to="/login">Go to sign in</Link>
          </>
        )}
        {state === 'error' && (
          <>
            <p className="form-error" role="alert">{error}</p>
            <p>Request a new verification email or contact support if the problem continues.</p>
            <Link to="/login">Go to sign in</Link>
          </>
        )}
      </section>
    </main>
  )
}
