"use client";

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, Loader2, Bell, BellOff, Trash2, Heart } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface Subscription {
  id: number;
  actor_name: string;
  actor_code: string;
  enabled: boolean;
  auto_download: boolean;
  last_check: string;
  last_found: string;
  created_at: string;
}

export default function FavoritesPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const res: any = await api.get('/v1/subscriptions');
      return res;
    },
  });

  const deleteSub = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/subscriptions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
  });

  const subs = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="flex flex-col min-h-screen">
      {/* 头部 */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-8 py-6 bg-zinc-950/80 backdrop-blur-md border-b border-white/5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Heart className="h-6 w-6 text-rose-500" />
            Favorites & Subscriptions
          </h1>
          <p className="text-sm text-zinc-500 mt-1">You are following {total} actresses.</p>
        </div>
      </div>

      <div className="flex-1 p-8 max-w-6xl mx-auto w-full">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-32 bg-zinc-900 animate-pulse rounded-2xl" />
            ))}
          </div>
        ) : subs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500 gap-4 mt-20">
            <Heart className="h-12 w-12 opacity-30" />
            <p>No favorites yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {subs.map((sub: Subscription) => (
                <motion.div
                  key={sub.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-zinc-900 border border-white/5 rounded-2xl p-5 flex flex-col gap-4 shadow-xl hover:border-white/10 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-12 w-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20">
                        {sub.actor_name[0]}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-white group-hover:text-rose-400 transition-colors">
                          {sub.actor_name}
                        </span>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          ID: {sub.actor_code || '未知'}
                        </span>
                      </div>
                    </div>

                    <button 
                      onClick={() => deleteSub.mutate(sub.id)}
                      className="p-2 hover:bg-rose-500/10 text-zinc-500 hover:text-rose-500 rounded-xl transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <div className="flex items-center gap-2 p-2 bg-zinc-950 rounded-lg border border-white/5">
                      {sub.auto_download ? (
                        <Bell className="h-3 w-3 text-emerald-500" />
                      ) : (
                        <BellOff className="h-3 w-3 text-zinc-500" />
                      )}
                      <span className="text-[10px] font-medium text-zinc-400">
                        Auto Download: <span className={sub.auto_download ? "text-emerald-500" : "text-zinc-500"}>{sub.auto_download ? 'ON' : 'OFF'}</span>
                      </span>
                    </div>

                    <div className="flex flex-col justify-center p-2 bg-zinc-950 rounded-lg border border-white/5">
                      <span className="text-[9px] uppercase tracking-widest text-zinc-500 font-bold mb-0.5">Last Check</span>
                      <span className="text-[10px] text-zinc-300 truncate">
                        {sub.last_check ? new Date(sub.last_check).toLocaleDateString() : 'Never'}
                      </span>
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
