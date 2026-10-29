import { useCallback, useEffect, useMemo, useState } from 'react'
import { createComment, listComments } from '../api/comments'
import { updateCommentsEnabled } from '../api/projects'
import CommentNode from './CommentNode'
import { useAuth } from '../hooks/useAuth'
import './CommentThread.css'

export default function CommentThread({ projectId, isOwner, commentsEnabled: initialCommentsEnabled }) {
  const { user } = useAuth()
  const [comments, setComments] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [commentsEnabled, setCommentsEnabled] = useState(initialCommentsEnabled)
  const [isTogglingEnabled, setIsTogglingEnabled] = useState(false)
  const [toggleError, setToggleError] = useState('')

  const [body, setBody] = useState('')
  const [isPosting, setIsPosting] = useState(false)
  const [postError, setPostError] = useState('')

  const loadComments = useCallback(async () => {
    try {
      const data = await listComments(projectId)
      setComments(data)
      setLoadError('')
    } catch {
      setLoadError('Unable to load comments. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadComments()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadComments])

  const childrenByParent = useMemo(() => {
    const map = new Map()
    for (const comment of comments) {
      const key = comment.parent
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(comment)
    }
    return map
  }, [comments])

  async function handlePost(event) {
    event.preventDefault()
    setPostError('')
    if (!body.trim()) {
      setPostError('Comment cannot be empty.')
      return
    }
    setIsPosting(true)
    try {
      await createComment(projectId, { body: body.trim(), parent: null })
      setBody('')
      await loadComments()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setPostError(firstError || 'Unable to post comment. Please try again.')
      } else {
        setPostError('Unable to post comment. Please try again.')
      }
    } finally {
      setIsPosting(false)
    }
  }

  function handleVoted(updatedComment) {
    setComments((prev) => prev.map((item) => (item.id === updatedComment.id ? updatedComment : item)))
  }

  async function handleToggleCommentsEnabled() {
    setToggleError('')
    setIsTogglingEnabled(true)
    try {
      const updated = await updateCommentsEnabled(projectId, !commentsEnabled)
      setCommentsEnabled(updated.comments_enabled)
    } catch {
      setToggleError('Unable to update comment settings. Please try again.')
    } finally {
      setIsTogglingEnabled(false)
    }
  }

  const rootComments = childrenByParent.get(null) || []

  return (
    <div className="comment-thread">
      {isOwner && (
        <div className="comment-moderation-toggle">
          <button type="button" onClick={handleToggleCommentsEnabled} disabled={isTogglingEnabled}>
            {commentsEnabled ? 'Disable comments' : 'Enable comments'}
          </button>
          {toggleError && (
            <p className="form-error" role="alert">
              {toggleError}
            </p>
          )}
        </div>
      )}

      {commentsEnabled ? (
        <form className="comment-composer" onSubmit={handlePost}>
          <textarea
            rows={3}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Add a comment…"
            maxLength={2000}
          />
          {postError && (
            <p className="form-error" role="alert">
              {postError}
            </p>
          )}
          <button type="submit" disabled={isPosting}>
            {isPosting ? 'Posting…' : 'Post comment'}
          </button>
        </form>
      ) : (
        <p className="text-sm">Comments are disabled for this project.</p>
      )}

      {loadError && (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm">Loading comments…</p>
      ) : rootComments.length === 0 ? (
        <p className="text-sm">No comments yet.</p>
      ) : (
        <ul className="comment-list">
          {rootComments.map((comment) => (
            <CommentNode
              key={comment.id}
              comment={comment}
              childrenByParent={childrenByParent}
              currentUserId={user.id}
              isModerator={isOwner}
              commentsEnabled={commentsEnabled}
              onChanged={loadComments}
              onVoted={handleVoted}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
