import { useState } from 'react'
import { createComment, deleteComment, deleteCommentTree, updateComment, voteComment } from '../api/comments'
import { formatDate } from '../utils/formatDate'
import './CommentNode.css'

// Mirrors backend discussions.models.Comment.MAX_DEPTH -- cosmetic only
// (hides the Reply affordance past the cap), the server re-validates.
const MAX_DEPTH = 3

export default function CommentNode({
  comment,
  childrenByParent,
  currentUserId,
  isModerator,
  commentsEnabled,
  onChanged,
  onVoted,
}) {
  const [isReplying, setIsReplying] = useState(false)
  const [replyBody, setReplyBody] = useState('')
  const [isPostingReply, setIsPostingReply] = useState(false)
  const [replyError, setReplyError] = useState('')

  const [isEditing, setIsEditing] = useState(false)
  const [editBody, setEditBody] = useState(comment.body || '')
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editError, setEditError] = useState('')

  const [isVoting, setIsVoting] = useState(false)
  const [actionError, setActionError] = useState('')

  const isDeleted = Boolean(comment.deleted_at)
  const isAuthor = !isDeleted && comment.author?.id === currentUserId
  const canDelete = !isDeleted && (isAuthor || isModerator)
  const canDeleteTree = !isDeleted && isModerator
  const replies = childrenByParent.get(comment.id) || []

  async function handleReply(event) {
    event.preventDefault()
    setReplyError('')
    if (!replyBody.trim()) {
      setReplyError('Reply cannot be empty.')
      return
    }
    setIsPostingReply(true)
    try {
      await createComment(comment.project, { body: replyBody.trim(), parent: comment.id })
      setReplyBody('')
      setIsReplying(false)
      await onChanged()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setReplyError(firstError || 'Unable to post reply. Please try again.')
      } else {
        setReplyError('Unable to post reply. Please try again.')
      }
    } finally {
      setIsPostingReply(false)
    }
  }

  async function handleSaveEdit(event) {
    event.preventDefault()
    setEditError('')
    if (!editBody.trim()) {
      setEditError('Comment cannot be empty.')
      return
    }
    setIsSavingEdit(true)
    try {
      await updateComment(comment.id, { body: editBody.trim() })
      setIsEditing(false)
      await onChanged()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setEditError(firstError || 'Unable to save changes. Please try again.')
      } else {
        setEditError('Unable to save changes. Please try again.')
      }
    } finally {
      setIsSavingEdit(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm('Delete this comment?')) return
    setActionError('')
    try {
      await deleteComment(comment.id)
      await onChanged()
    } catch {
      setActionError('Unable to delete the comment. Please try again.')
    }
  }

  async function handleDeleteTree() {
    if (!window.confirm('Delete this comment and all of its replies?')) return
    setActionError('')
    try {
      await deleteCommentTree(comment.id)
      await onChanged()
    } catch {
      setActionError('Unable to delete the comment thread. Please try again.')
    }
  }

  async function handleVote(value) {
    setActionError('')
    setIsVoting(true)
    try {
      const updated = await voteComment(comment.id, value)
      onVoted(updated)
    } catch {
      setActionError('Unable to register your vote. Please try again.')
    } finally {
      setIsVoting(false)
    }
  }

  return (
    <li className="comment-node">
      {isDeleted ? (
        <p className="comment-tombstone">{comment.body || '[Commend deleted]'}</p>
      ) : isEditing ? (
        <form className="comment-edit-form" onSubmit={handleSaveEdit}>
          <textarea
            rows={3}
            value={editBody}
            onChange={(event) => setEditBody(event.target.value)}
            maxLength={2000}
          />
          {editError && (
            <p className="form-error" role="alert">
              {editError}
            </p>
          )}
          <div className="comment-actions">
            <button type="submit" disabled={isSavingEdit}>
              {isSavingEdit ? 'Saving…' : 'Save'}
            </button>
            <button type="button" onClick={() => setIsEditing(false)} disabled={isSavingEdit}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="comment-meta">
            <span className="comment-author">
              {`${comment.author.first_name} ${comment.author.last_name}`.trim() || comment.author.username}
            </span>
            <span className="comment-date">{formatDate(comment.created_at)}</span>
          </div>
          <p className="comment-body">{comment.body}</p>
        </>
      )}

      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}

      {!isDeleted && !isEditing && (
        <div className="comment-actions">
          <button
            type="button"
            className={`comment-vote${comment.my_vote === 1 ? ' comment-vote-active' : ''}`}
            onClick={() => handleVote(1)}
            disabled={isVoting}
          >
            ▲ {comment.up_count}
          </button>
          <button
            type="button"
            className={`comment-vote${comment.my_vote === -1 ? ' comment-vote-active' : ''}`}
            onClick={() => handleVote(-1)}
            disabled={isVoting}
          >
            ▼ {comment.down_count}
          </button>
          {commentsEnabled && comment.depth < MAX_DEPTH && (
            <button type="button" onClick={() => setIsReplying((prev) => !prev)}>
              Reply
            </button>
          )}
          {isAuthor && (
            <button type="button" onClick={() => setIsEditing(true)}>
              Edit
            </button>
          )}
          {canDelete && (
            <button type="button" onClick={handleDelete}>
              Delete
            </button>
          )}
          {canDeleteTree && (
            <button type="button" onClick={handleDeleteTree}>
              Delete Comment Tree
            </button>
          )}
        </div>
      )}

      {isReplying && (
        <form className="comment-reply-form" onSubmit={handleReply}>
          <textarea
            rows={2}
            value={replyBody}
            onChange={(event) => setReplyBody(event.target.value)}
            placeholder="Write a reply…"
            maxLength={2000}
            autoFocus
          />
          {replyError && (
            <p className="form-error" role="alert">
              {replyError}
            </p>
          )}
          <div className="comment-actions">
            <button type="submit" disabled={isPostingReply}>
              {isPostingReply ? 'Posting…' : 'Post reply'}
            </button>
            <button type="button" onClick={() => setIsReplying(false)} disabled={isPostingReply}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {replies.length > 0 && (
        <ul className="comment-list comment-replies">
          {replies.map((reply) => (
            <CommentNode
              key={reply.id}
              comment={reply}
              childrenByParent={childrenByParent}
              currentUserId={currentUserId}
              isModerator={isModerator}
              commentsEnabled={commentsEnabled}
              onChanged={onChanged}
              onVoted={onVoted}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
