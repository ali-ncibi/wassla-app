export interface ArticleCardItem {
  id: number
  title: string
  summary: string | null
  category: string | null
  source_name: string
  url: string
  published_at: string | null
  scraped_at: string
}

export interface ArticlesResponse {
  total: number
  items: ArticleCardItem[]
}

export interface ArticleDetail {
  id: number
  title: string
  body: string
  summary: string | null
  category: string | null
  lang: string
  source_language: string
  source_name: string
  url: string
  published_at: string | null
  scraped_at: string
  eval_score: number | null
  eval_verdict: string | null
  available_langs: string[]
}

export interface CategoryCount {
  name: string
  count: number
}

export interface SearchHit {
  article_id: number
  title: string
  summary: string | null
  category: string | null
  source_name: string
  url: string
  published_at: string | null
  score: number
}

export interface SearchResponse {
  query: string
  lang: string
  answer: string | null
  hits: SearchHit[]
}

export interface StatsResponse {
  total_articles: number
  needs_review: number
  avg_eval_score: number | null
  last_scraped_at: string | null
  by_category: CategoryCount[]
  by_language: CategoryCount[]
  per_day_target: number
}
