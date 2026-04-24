"use client";

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Download, Loader2, Play, Pause, Trash2, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface DownloadTask {
  id: string;
  code: string;
  title: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed' | 'paused';
  progress: number;
  size: string;
  added_at: string;
  error_msg?: string;
}

export default function DownloadsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: async () => {
      const res: any = await api.get('/v1/downloads');
      return res;
    },
    refetchInterval: 3000, // 轮询进度
  });

  const deleteTask = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/downloads/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['downloads'] }),
  });

  const tasks = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* 头部 */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Download className="h-6 w-6 text-indigo-500" />
            下载任务
          </h1>
          <p className="text-sm text-zinc-500 mt-1">共有 {total} 个进行中或已完成的任务。</p>
        </div>
      </div>

      <div className="flex-1 p-8 max-w-5xl mx-auto w-full">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <Download className="h-12 w-12 opacity-30" />
            <p>暂无下载任务。</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <AnimatePresence>
              {tasks.map((task: DownloadTask) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-zinc-900 border border-white/5 rounded-2xl p-5 flex flex-col gap-4 shadow-xl"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-white/10 rounded-md text-[10px] font-bold uppercase tracking-widest text-zinc-300">
                          {task.code}
                        </span>
                        <h3 className="text-sm font-semibold text-zinc-100 line-clamp-1">{task.title}</h3>
                      </div>
                      <p className="text-xs text-zinc-500">大小: {task.size || '未知'}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button 
                        onClick={() => deleteTask.mutate(task.id)}
                        className="p-2 hover:bg-rose-500/10 text-zinc-500 hover:text-rose-500 rounded-xl transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* 进度条区域 */}
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between text-xs font-medium">
                      <div className="flex items-center gap-2">
                        <StatusIcon status={task.status} />
                        <span className="capitalize tracking-wider text-zinc-400">{task.status}</span>
                      </div>
                      <span className="text-zinc-300">{task.progress || 0}%</span>
                    </div>
                    
                    <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${task.progress || 0}%` }}
                        transition={{ duration: 0.5 }}
                        className={cn(
                          "h-full rounded-full",
                          task.status === 'completed' ? "bg-emerald-500" :
                          task.status === 'failed' ? "bg-rose-500" :
                          "bg-indigo-500"
                        )}
                      />
                    </div>
                    {task.error_msg && (
                      <p className="text-[10px] text-rose-400 mt-1">{task.error_msg}</p>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'completed': return <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />;
    case 'failed': return <AlertCircle className="h-3.5 w-3.5 text-rose-500" />;
    case 'downloading': return <Loader2 className="h-3.5 w-3.5 text-indigo-500 animate-spin" />;
    case 'paused': return <Pause className="h-3.5 w-3.5 text-amber-500" />;
    default: return <Play className="h-3.5 w-3.5 text-zinc-500" />;
  }
};
