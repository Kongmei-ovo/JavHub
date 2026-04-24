export interface Actor {
  id?: number | string;
  name: string;
  image_url?: string;
  count?: number;
}

export interface Category {
  id: string | number;
  name: string;
}

export interface Magnet {
  title: string;
  magnet: string;
  size: string;
  quality?: string;
  resolution?: string;
  hd: boolean;
  subtitle: boolean;
}

export interface Movie {
  content_id: string;
  dvd_id?: string;
  title_ja?: string;
  release_date?: string;
  runtime_mins?: number;
  jacket_thumb_url?: string;
  jacket_full_url?: string;
  categories?: Category[];
  actresses?: Actor[];
  magnets?: Magnet[];
}
