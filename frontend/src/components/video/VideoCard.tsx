"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, User, ImageOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Movie } from '@/types/jav';

interface VideoCardProps {
  movie: Movie;
  className?: string;
  onClick?: (movie: Movie) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({ movie, className, onClick }) => {
  const [imageError, setImageError] = useState(false);
  const { content_id, title_ja, release_date, actresses = [], jacket_full_url, jacket_thumb_url } = movie;

  const coverUrl = jacket_full_url || jacket_thumb_url;
  const actressNames = actresses.slice(0, 2).map(a => a.name).join(', ') + (actresses.length > 2 ? '...' : '');

  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      whileHover={{ y: -4 }}
      onClick={() => onClick?.(movie)}
      className={cn(
        "group relative flex flex-col bg-bg-elevated cursor-pointer",
        "rounded-2xl overflow-hidden transition-smooth",
        className
      )}
    >
      {/* Cover */}
      <div className="relative aspect-[2/3] w-full overflow-hidden bg-bg-surface">
        {coverUrl && !imageError ? (
          <img
            src={coverUrl}
            alt={content_id}
            onError={() => setImageError(true)}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-zinc-700">
            <ImageOff className="h-8 w-8" strokeWidth={1.5} />
            <span className="text-[10px] font-medium tracking-widest uppercase">No Poster</span>
          </div>
        )}

        {/* ID Badge */}
        <div className="absolute bottom-3 left-3">
          <span className="rounded-md bg-black/50 backdrop-blur-sm px-2 py-0.5 text-[10px] font-bold tracking-widest text-white/80 uppercase backdrop-blur-sm">
            {content_id}
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="p-4 space-y-1.5">
        <h3 className="line-clamp-1 text-sm font-medium tracking-tight text-zinc-200 group-hover:text-white transition-colors">
          {title_ja || content_id}
        </h3>

        <div className="flex items-center justify-between text-[11px] text-zinc-500">
          {actresses.length > 0 ? (
            <div className="flex items-center gap-1.5 truncate">
              <User className="h-3 w-3 shrink-0" />
              <span className="truncate">{actressNames}</span>
            </div>
          ) : <div className="flex-1" />}
          {release_date && (
            <div className="flex items-center gap-1.5 shrink-0 ml-2">
              <Calendar className="h-3 w-3" />
              <span>{release_date.split('-')[0]}</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
