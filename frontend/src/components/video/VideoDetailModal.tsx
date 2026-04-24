"use client";

import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Calendar,
  User,
  Building2,
  Clock,
  Tag,
  Download,
  ExternalLink,
  ChevronRight,
  ImageOff
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Movie, Magnet } from '@/types/jav';

interface VideoDetailModalProps {
  movie: Movie | null;
  isOpen: boolean;
  onClose: () => void;
}

export const VideoDetailModal: React.FC<VideoDetailModalProps> = ({ movie, isOpen, onClose }) => {
  if (!movie) return null;

  const {
    categories = [],
    actresses = [],
    magnets = [],
    title_ja = "Unknown Title",
    content_id,
    release_date = "Unknown",
    jacket_full_url,
    jacket_thumb_url,
    runtime_mins = 0,
    maker,
    label
  } = movie;

  const coverUrl = jacket_full_url || jacket_thumb_url;

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog.Root open={isOpen} onOpenChange={onClose}>
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl"
              />
            </Dialog.Overlay>

            <Dialog.Content asChild>
              <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 20 }}
                transition={{ type: "spring", bounce: 0.2, duration: 0.5 }}
                className="fixed left-1/2 top-1/2 z-50 w-full max-w-5xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl bg-bg-elevated shadow-2xl focus:outline-none"
              >
                <div className="relative flex flex-col md:flex-row" style={{ maxHeight: '90vh' }}>

                  {/* Left: Poster & Actions */}
                  <div className="w-full md:w-80 shrink-0 bg-bg-surface p-8 flex flex-col gap-6">
                    <div className="aspect-[2/3] w-full overflow-hidden rounded-2xl bg-bg-base flex items-center justify-center">
                      {coverUrl ? (
                        <img
                          src={coverUrl}
                          className="h-full w-full object-cover"
                          alt="Poster"
                        />
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-zinc-600">
                          <ImageOff className="h-10 w-10" />
                          <span className="text-xs font-medium uppercase tracking-widest">No Poster</span>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <button className="btn btn-primary w-full">
                        <Download className="h-4 w-4" />
                        Quick Download
                      </button>
                      <button className="btn w-full bg-bg-surface text-zinc-300 hover:bg-bg-hover">
                        <ExternalLink className="h-4 w-4" />
                        View Details
                      </button>
                    </div>

                    <div className="mt-auto space-y-4 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-500">Content ID</span>
                        <span className="font-mono text-zinc-300 uppercase tracking-wider">{content_id}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-500">Release Date</span>
                        <span className="text-zinc-300">{release_date}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Info & Magnets */}
                  <div className="flex-1 overflow-y-auto p-8 custom-scrollbar space-y-8">
                    {/* Header */}
                    <header className="space-y-3">
                      <div className="flex flex-wrap gap-1.5">
                        {categories.map(cat => (
                          <span key={cat.id} className="px-2 py-0.5 rounded-md bg-bg-surface text-[10px] text-zinc-400 font-medium uppercase tracking-wider">
                            {cat.name}
                          </span>
                        ))}
                      </div>
                      <h1 className="text-2xl font-bold leading-tight tracking-tight text-white">
                        {title_ja}
                      </h1>
                    </header>

                    {/* Meta Grid */}
                    <section className="grid grid-cols-2 gap-4 p-5 rounded-2xl bg-bg-surface">
                      <MetaItem icon={User} label="Actors" value={actresses.map(a => a.name).join(', ') || 'N/A'} />
                      <MetaItem icon={Building2} label="Maker" value={maker?.name || 'N/A'} />
                      <MetaItem icon={Clock} label="Runtime" value={`${runtime_mins} mins`} />
                      <MetaItem icon={Tag} label="Label" value={label?.name || 'N/A'} />
                    </section>

                    {/* Magnets */}
                    <section className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h2 className="text-base font-semibold text-white flex items-center gap-2">
                          <Download className="h-4 w-4 text-accent" />
                          Magnets
                        </h2>
                        <span className="text-xs text-zinc-500">{magnets.length} links</span>
                      </div>

                      <div className="space-y-2">
                        {magnets.length > 0 ? (
                          magnets.map((m, idx) => (
                            <MagnetRow key={idx} magnet={m} />
                          ))
                        ) : (
                          <div className="p-6 rounded-2xl bg-bg-surface text-center text-zinc-500 text-sm">
                            No magnets available for this title.
                          </div>
                        )}
                      </div>
                    </section>
                  </div>

                  {/* Close */}
                  <button
                    onClick={onClose}
                    className="absolute top-5 right-5 h-9 w-9 flex items-center justify-center rounded-full bg-bg-surface text-zinc-400 hover:text-white hover:bg-bg-hover transition-smooth"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </AnimatePresence>
  );
};

const MetaItem = ({ icon: Icon, label, value }: { icon: any, label: string, value: string }) => (
  <div className="flex flex-col gap-1">
    <div className="flex items-center gap-1.5 text-zinc-500">
      <Icon className="h-3 w-3" />
      <span className="text-[10px] font-semibold uppercase tracking-widest">{label}</span>
    </div>
    <span className="text-sm text-zinc-200 truncate">{value}</span>
  </div>
);

const MagnetRow = ({ magnet }: { magnet: Magnet }) => (
  <div className="group flex items-center justify-between p-4 rounded-xl bg-bg-surface hover:bg-bg-hover transition-smooth cursor-pointer">
    <div className="flex flex-col gap-1 min-w-0">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-zinc-100 truncate">{magnet.title}</span>
        {magnet.hd && <span className="shrink-0 px-1.5 py-0.5 rounded text-[8px] bg-accent/20 text-accent font-bold">HD</span>}
        {magnet.subtitle && <span className="shrink-0 px-1.5 py-0.5 rounded text-[8px] bg-emerald-500/20 text-emerald-400 font-bold">SUB</span>}
      </div>
      <div className="flex items-center gap-2 text-[10px] text-zinc-500">
        <span>{magnet.size}</span>
        <span className="text-zinc-700">|</span>
        <span>{magnet.quality || 'N/A'}</span>
      </div>
    </div>
    <ChevronRight className="h-4 w-4 text-zinc-600 shrink-0 ml-3 group-hover:text-zinc-300 transition-colors" />
  </div>
);
