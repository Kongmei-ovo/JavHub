import { reactive } from 'vue'

export const modalState = reactive({
  selectedVideo: null,
  visible: false,
  openedOnRoute: null, // 记录弹窗是在哪个页面打开的
  interrupted: false   // 记录是否因为点击 Tag 导航而暂时隐藏
})

export function openVideoModal(video, routePath = null) {
  modalState.selectedVideo = video
  modalState.visible = true
  modalState.interrupted = false
  if (routePath) {
    modalState.openedOnRoute = routePath
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
