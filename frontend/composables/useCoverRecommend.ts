/**
 * 智能封面推荐（纯前端评分策略）
 * 根据文件大小、类型、文件名关键词对画集图片评分，返回 top 3 推荐
 */
import type { GalleryImage } from '~/composables/useGalleryApi'

interface ScoredImage {
  image: GalleryImage
  score: number
}

/**
 * 对单张图片评分
 */
function scoreImage(image: GalleryImage): number {
  let score = 50 // 基础分

  // 文件大小评分：200KB-2MB 得分最高
  const size = image.file_size || 0
  if (size > 0) {
    if (size >= 200 * 1024 && size <= 2 * 1024 * 1024) {
      score += 30
    } else if (size >= 100 * 1024 && size <= 5 * 1024 * 1024) {
      score += 15
    } else if (size < 50 * 1024) {
      score -= 20 // 太小，可能是图标
    }
  }

  // MIME 类型评分
  const mime = (image.mime_type || '').toLowerCase()
  const filename = (image.original_filename || '').toLowerCase()
  const ext = filename.split('.').pop() || ''

  if (mime.includes('jpeg') || mime.includes('jpg') || ext === 'jpg' || ext === 'jpeg') {
    score += 15
  } else if (mime.includes('png') || ext === 'png') {
    score += 12
  } else if (mime.includes('webp') || ext === 'webp') {
    score += 5
  } else if (mime.includes('gif') || ext === 'gif') {
    score -= 5
  }

  // 文件名关键词加分
  if (/cover|封面|banner|poster|hero/i.test(filename)) {
    score += 25
  }

  // 文件名关键词减分
  if (/thumb|icon|avatar|logo|favicon/i.test(filename)) {
    score -= 20
  }

  return score
}

/**
 * 返回 top N 推荐封面图片
 */
export function useCoverRecommend() {
  const recommend = (images: GalleryImage[], topN = 3): GalleryImage[] => {
    if (!images || images.length === 0) return []

    const scored: ScoredImage[] = images.map(image => ({
      image,
      score: scoreImage(image)
    }))

    scored.sort((a, b) => b.score - a.score)

    return scored.slice(0, topN).map(s => s.image)
  }

  return { recommend }
}
