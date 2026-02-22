import { createGalleryApi } from './useGalleryApiFactory'

export const useAdminGalleryApi = () => {
  return createGalleryApi('/api/admin/galleries', () => ({
    credentials: 'include' as RequestCredentials
  }))
}
