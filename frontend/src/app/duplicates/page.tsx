"use client";

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Loader2, Trash2, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

export default function DuplicatesPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['duplicates'],
    queryFn: async () => {
      const res: any = await api.get('/v1/duplicates');
      return res;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.post(`/v1/duplicates/${id}/delete`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['duplicates'] }),
  });

  const ignoreMutation = useMutation({
    mutationFn: (id: string) => api.post(`/v1/duplicates/${id}/ignore`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['duplicates'] }),
  });

  const duplicates = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="flex flex-col min-h-screen">
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-amber-500" />
            Duplicate Files
          </h1>
          <p className="text-sm text-zinc-500 mt-1">You have {total} duplicate videos in your Emby library.</p>
        </div>
      </div>

      <div className="flex-1 p-8 max-w-5xl mx-auto w-full">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
          </div>
        ) : duplicates.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <AlertCircle className="h-12 w-12 opacity-30" />
            <p>Your library is perfectly clean. No duplicates found.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <AnimatePresence>
              {duplicates.map((item: any, i: number) => (
                <motion.div
                  key={item.id || i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-zinc-900 border border-white/5 rounded-2xl p-5 shadow-xl hover:border-white/10 transition-colors"
                >
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-zinc-100 flex items-center gap-2">
                        <span className="bg-amber-500/10 text-amber-500 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest border border-amber-500/20">
                          {item.code || 'ID'}
                        </span>
                        {item.title || item.name}
                      </h3>
                      
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={() => ignoreMutation.mutate(item.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg text-xs font-medium text-zinc-300 transition-colors"
                        >
                          <EyeOff className="h-3.5 w-3.5" />
                          Ignore
                        </button>
                        <button 
                          onClick={() => deleteMutation.mutate(item.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-lg text-xs font-medium text-rose-400 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete File
                        </button>
                      </div>
                    </div>
                    
                    <div className="flex flex-col gap-1.5 p-3 bg-zinc-950 rounded-xl border border-white/5 font-mono text-[11px] text-zinc-400 overflow-x-auto">
                      <p><span className="text-zinc-600">路径:</span> {item.path}</p>
                      {item.size && <p><span className="text-zinc-600">大小:</span> {item.size}</p>}
                    </div>
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
