import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import '../styles/authForm.css'
import '../styles/formFeedback.css'
import './RegisterPage.css'

const INITIAL_FORM = {
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  firstName: '',
  lastName: '',
  company: '',
  secondaryEmail: '',
}

function parseFieldErrors(data) {
  if (!data || typeof data !== 'object') return {}
  const errors = {}
  for (const [key, value] of Object.entries(data)) {
    errors[key] = Array.isArray(value) ? value[0] : String(value)
  }
  return errors
}

export default function RegisterPage() {
  const { register, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(INITIAL_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [generalError, setGeneralError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  function handleChange(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  function validate() {
    const errors = {}
    if (!form.username.trim()) errors.username = 'Username is required.'
    if (!form.email.trim()) errors.email = 'Email is required.'
    if (!form.password) errors.password = 'Password is required.'
    if (form.password && form.password !== form.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.'
    }
    return errors
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setGeneralError('')

    const clientErrors = validate()
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors)
      return
    }
    setFieldErrors({})

    setIsSubmitting(true)
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        company: form.company.trim(),
        secondary_email: form.secondaryEmail.trim(),
      })
      navigate('/', { replace: true })
    } catch (err) {
      if (err.response?.status === 400) {
        setFieldErrors(parseFieldErrors(err.response.data))
      } else {
        setGeneralError('Unable to create an account right now. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card auth-card-wide" onSubmit={handleSubmit} noValidate>
        <h1>Rosana</h1>
        <p className="auth-subtitle">Create an account</p>

        {generalError && (
          <p className="form-error" role="alert">
            {generalError}
          </p>
        )}

        <label className="auth-field">
          <span>Username</span>
          <input
            type="text"
            autoComplete="username"
            value={form.username}
            onChange={handleChange('username')}
            autoFocus
          />
          {fieldErrors.username && <p className="auth-field-error">{fieldErrors.username}</p>}
        </label>

        <label className="auth-field">
          <span>Email</span>
          <input type="email" autoComplete="email" value={form.email} onChange={handleChange('email')} />
          {fieldErrors.email && <p className="auth-field-error">{fieldErrors.email}</p>}
        </label>

        <div className="auth-field-row">
          <label className="auth-field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={handleChange('password')}
            />
            {fieldErrors.password && <p className="auth-field-error">{fieldErrors.password}</p>}
          </label>

          <label className="auth-field">
            <span>Confirm password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={handleChange('confirmPassword')}
            />
            {fieldErrors.confirmPassword && <p className="auth-field-error">{fieldErrors.confirmPassword}</p>}
          </label>
        </div>

        <div className="auth-field-row">
          <label className="auth-field">
            <span>First name</span>
            <input type="text" autoComplete="given-name" value={form.firstName} onChange={handleChange('firstName')} />
          </label>

          <label className="auth-field">
            <span>Last name</span>
            <input type="text" autoComplete="family-name" value={form.lastName} onChange={handleChange('lastName')} />
          </label>
        </div>

        <label className="auth-field">
          <span>Company</span>
          <input type="text" autoComplete="organization" value={form.company} onChange={handleChange('company')} />
          {fieldErrors.company && <p className="auth-field-error">{fieldErrors.company}</p>}
        </label>

        <label className="auth-field">
          <span>Secondary email (optional)</span>
          <input type="email" value={form.secondaryEmail} onChange={handleChange('secondaryEmail')} />
          {fieldErrors.secondary_email && <p className="auth-field-error">{fieldErrors.secondary_email}</p>}
        </label>

        <button type="submit" className="auth-submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </main>
  )
}
