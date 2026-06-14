/// <reference types="vite/client" />
import axios from 'axios'

const TOKEN_KEY = 'auth_token'

// Create a single Axios instance for the whole app.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL as string,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach the Bearer token to every request when one is stored.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401 responses, clear the saved auth data so the user is sent to login.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only clear storage — do not navigate here to avoid redirect loops.
      // The router guard will handle the redirect.
      localStorage.removeItem(TOKEN_KEY)
    }
    return Promise.reject(error)
  },
)

export { TOKEN_KEY }
export default apiClient
