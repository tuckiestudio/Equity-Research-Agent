import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, FileText, Calendar, Trash2, Sparkles } from 'lucide-react'
import { getNotes, createNote, deleteNote, extractNoteEntities, type Note } from '@/services/news'
import { formatDate } from '@/utils/format'

interface NotesTabProps {
  ticker: string
}

export default function NotesTab({ ticker }: NotesTabProps) {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  const { data: notes, isLoading } = useQuery({
    queryKey: ['notes', ticker],
    queryFn: () => getNotes(ticker).then((res) => res.data),
  })

  const createMutation = useMutation({
    mutationFn: () => createNote(ticker, { title, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', ticker] })
      setIsModalOpen(false)
      setTitle('')
      setContent('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (noteId: string) => deleteNote(noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', ticker] })
    },
  })

  const extractMutation = useMutation({
    mutationFn: (noteId: string) => extractNoteEntities(noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', ticker] })
    },
  })

  const handleSave = () => {
    if (title.trim() && content.trim()) {
      createMutation.mutate()
    }
  }



  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">Research Notes</h2>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-3 py-1.5 rounded text-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Note
        </button>
      </div>

      {/* Notes Grid */}
      {isLoading ? (
        <div className="text-center py-8 text-text-secondary">Loading notes...</div>
      ) : notes && notes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              onDelete={() => deleteMutation.mutate(note.id)}
              onExtract={() => extractMutation.mutate(note.id)}
              isProcessing={extractMutation.isPending && extractMutation.variables === note.id}
            />
          ))}
        </div>
      ) : (
        <div className="bg-surface-card rounded-lg p-8 text-center border border-border">
          <FileText className="w-12 h-12 text-text-muted mx-auto mb-3" />
          <p className="text-text-secondary mb-1">No notes yet</p>
          <p className="text-text-muted text-sm mb-4">
            Add notes to track your research and insights
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-accent hover:underline"
          >
            Create your first note
          </button>
        </div>
      )}

      {/* Add Note Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-card rounded-lg w-full max-w-lg border border-border animate-slide-up">
            <div className="p-4 border-b border-border">
              <h3 className="text-lg font-semibold text-text-primary">Add Note</h3>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="text-sm text-text-secondary mb-1 block">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Note title..."
                  className="w-full bg-surface border border-border rounded px-3 py-2 text-text-primary focus:border-accent outline-none"
                />
              </div>
              <div>
                <label className="text-sm text-text-secondary mb-1 block">Content</label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Write your research notes..."
                  rows={6}
                  className="w-full bg-surface border border-border rounded px-3 py-2 text-text-primary focus:border-accent outline-none resize-none"
                />
              </div>
            </div>
            <div className="p-4 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsModalOpen(false)
                  setTitle('')
                  setContent('')
                }}
                className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={createMutation.isPending || !title.trim() || !content.trim()}
                className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                {createMutation.isPending ? 'Saving...' : 'Save Note'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface NoteCardProps {
  note: Note
  onDelete: () => void
  onExtract: () => void
  isProcessing: boolean
}

function NoteCard({ note, onDelete, onExtract, isProcessing }: NoteCardProps) {
  const [expanded, setExpanded] = useState(false)
  const maxPreviewLength = 120

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'text-success bg-success/10 border-success/20'
      case 'negative':
        return 'text-danger bg-danger/10 border-danger/20'
      default:
        return 'text-text-muted bg-surface-elevated border-border'
    }
  }

  return (
    <div className="bg-surface-card rounded-lg border border-border hover:border-border-hover transition-all">
      <div
        className="p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-text-primary font-medium line-clamp-1">{note.title}</h3>
          {note.extracted_sentiment && (
            <span
              className={`text-xs px-2 py-0.5 rounded border ${getSentimentColor(
                note.extracted_sentiment
              )}`}
            >
              {note.extracted_sentiment}
            </span>
          )}
        </div>
        <p className="text-sm text-text-secondary line-clamp-2">
          {note.content.length > maxPreviewLength && !expanded
            ? `${note.content.slice(0, maxPreviewLength)}...`
            : note.content}
        </p>
        <div className="flex items-center gap-2 mt-3 text-xs text-text-muted">
          <Calendar className="w-3 h-3" />
          {formatDate(note.created_at)}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-border/50 animate-fade-in">
          <div className="flex gap-2 mt-3">
            {!note.is_ai_processed && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onExtract()
                }}
                disabled={isProcessing}
                className="flex items-center gap-1.5 text-xs bg-accent/10 hover:bg-accent/20 text-accent px-2 py-1 rounded transition-colors"
              >
                <Sparkles className="w-3 h-3" />
                {isProcessing ? 'Processing...' : 'AI Extract'}
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="flex items-center gap-1.5 text-xs text-danger hover:text-danger/80 px-2 py-1 transition-colors ml-auto"
            >
              <Trash2 className="w-3 h-3" />
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
