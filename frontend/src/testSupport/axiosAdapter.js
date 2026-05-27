import axios from 'axios'

export function installAxiosAdapter(t, adapter) {
  const originalAdapter = axios.defaults.adapter
  axios.defaults.adapter = adapter
  t.after(() => {
    axios.defaults.adapter = originalAdapter
  })
}
