import { reactive } from 'vue'

const defaultState = {
  open: false,
  title: '确认操作',
  message: '',
  details: '',
  confirmText: '确认',
  cancelText: '取消',
  tone: 'default'
}

let pendingResolve = null

export const confirmDialogState = reactive({ ...defaultState })

export function requestConfirm(options = {}) {
  if (pendingResolve) {
    pendingResolve(false)
  }

  Object.assign(confirmDialogState, defaultState, options, { open: true })

  return new Promise(resolve => {
    pendingResolve = resolve
  })
}

export function resolveConfirm(confirmed) {
  if (!confirmDialogState.open) return

  const resolve = pendingResolve
  pendingResolve = null
  confirmDialogState.open = false

  if (resolve) {
    resolve(Boolean(confirmed))
  }
}
