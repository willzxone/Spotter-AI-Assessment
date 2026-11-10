/** The backend rejects shorter queries (`SearchInput.query` min_length). */
export const MIN_QUERY_LENGTH = 2

/** Matches the backend's `SearchInput.query` max_length. */
export const MAX_QUERY_LENGTH = 120

export const RESULT_LIMIT = 6

/** Wait this long after the last keystroke before searching; search is rate limited. */
export const DEBOUNCE_MS = 300
