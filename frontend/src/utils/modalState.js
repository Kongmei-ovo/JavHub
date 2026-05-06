import { reactive } from 'vue'
import defaultApi from '../api/index.js'
import { normalizeVideo, videoCodeOf } from './videoNormalize.js'

let modalRequestId = 0

export const modalState = reactive({
  selectedVideo: null,
  visible: false,
  openedOnRoute: null, // 记录弹窗是在哪个页面打开的
  interrupted: false   // 记录是否因为点击 Tag 导航而暂时隐藏
})

function withLoadingState(video, contentId, api) {
  const normalized = normalizeVideo(video)
  return {
    ...normalized,
    _loading: {
      javinfo: Boolean(contentId && api?.getVideo),
      metatube: Boolean(contentId && api?.getVideoMetadata),
      cover: true,
      gallery: false,
      ...(video._loading || {})
    },
    _errors: {
      javinfo: null,
      metatube: null,
      cover: null,
      gallery: null,
      stream: null,
      ...(video._errors || {})
    }
  }
}

function isCurrentRequest(requestId, contentId) {
  return modalRequestId === requestId && videoCodeOf(modalState.selectedVideo) === contentId
}

function errorMessage(error) {
  return error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || '网络错误'
}

export function openVideoModal(video, routePath = null, api = defaultApi) {
  const requestId = ++modalRequestId
  const contentId = videoCodeOf(video)
  modalState.selectedVideo = withLoadingState(video, contentId, api)
  modalState.visible = true
  modalState.interrupted = false
  if (routePath) {
    modalState.openedOnRoute = routePath
  }

  if (contentId && api?.getVideo) {
    api.getVideo(contentId)
      .then(response => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo = {
            ...modalState.selectedVideo,
            ...(response?.data || {}),
            _loading: {
              ...modalState.selectedVideo._loading,
              javinfo: false,
            },
          }
        }
      })
      .catch(error => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo._loading.javinfo = false
          modalState.selectedVideo._errors.javinfo = errorMessage(error)
        }
      })
  }

  if (contentId && api?.getVideoMetadata) {
    api.getVideoMetadata(contentId)
      .then(response => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo = {
            ...modalState.selectedVideo,
            ...(response?.data || {}),
            _loading: {
              ...modalState.selectedVideo._loading,
              metatube: false,
            },
          }
        }
      })
      .catch(error => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo._loading.metatube = false
          modalState.selectedVideo._errors.metatube = errorMessage(error)
        }
      })
  }
}

export function closeVideoModal() {
  modalState.visible = false
  modalState.interrupted = false
  // 延迟清除数据，给动画留时间
  setTimeout(() => {
    if (!modalState.visible && !modalState.interrupted) {
      modalState.selectedVideo = null
      modalState.openedOnRoute = null
    }
  }, 300)
}

// 暂时隐藏弹窗（用于跳转到 Tag 页面）
export function interruptModal() {
  if (modalState.visible) {
    modalState.visible = false
    modalState.interrupted = true
  }
}

// 恢复弹窗（从 Tag 页面返回时）
export function resumeModal() {
  if (modalState.interrupted && modalState.selectedVideo) {
    modalState.visible = true
    modalState.interrupted = false
  }
}

export function resetModal() {
  modalRequestId += 1
  modalState.selectedVideo = null
  modalState.visible = false
  modalState.openedOnRoute = null
  modalState.interrupted = false
}
