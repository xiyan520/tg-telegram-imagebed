/**
 * API 文档数据结构定义
 * 用于渲染 API 文档页面的数据驱动配置
 */

// ===================== 类型定义 =====================

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'HEAD'
export type ParamLocation = 'path' | 'query' | 'header' | 'body' | 'formData'
export type CodeLanguage = 'bash' | 'javascript' | 'python' | 'php' | 'json'

/** API 参数定义 */
export interface ApiParam {
  name: string
  in: ParamLocation
  required?: boolean
  description?: string
  type?: string
  example?: string
}

/** 代码示例 */
export interface CodeExample {
  id: string
  label: string
  language: CodeLanguage
  code: string
}

/** 响应示例 */
export interface ResponseExample {
  status: number
  description: string
  example?: string
}

/** API 端点定义 */
export interface ApiEndpoint {
  id: string
  title: string
  summary?: string
  description?: string
  method: HttpMethod
  path: string
  deprecated?: boolean
  auth?: 'none' | 'bearer'
  authDescription?: string
  params?: ApiParam[]
  responses: ResponseExample[]
  codeExamples?: CodeExample[]
  notes?: string[]
}

/** API 分组定义 */
export interface ApiSection {
  id: string
  title: string
  description?: string
  icon?: string
  endpoints: ApiEndpoint[]
}

/** 模板变量定义 */
export const TEMPLATE_VARS = {
  baseUrl: { description: 'API 基础地址', example: 'http://localhost:18793' },
  token: { description: 'Bearer Token', example: 'guest_xxxxx' },
  encryptedId: { description: '图片加密 ID', example: 'abc123xyz' },
  filePath: { description: '本地文件路径', example: './image.jpg' },
} as const

/** 模板变量默认示例值（用于代码示例渲染） */
export const DEFAULT_TEMPLATE_VALUES: Record<string, string> = {
  baseUrl: '',  // 运行时由组件提供
  token: 'guest_xxxxx',
  encryptedId: 'abc123xyz',
  filePath: './image.jpg',
}

// ===================== API 文档数据 =====================

export const apiSections: ApiSection[] = [
  // -------------------- 上传 --------------------
  {
    id: 'upload',
    title: '上传',
    description: '图片上传相关接口',
    icon: 'heroicons:cloud-arrow-up',
    endpoints: [
      {
        id: 'upload-anonymous',
        title: '匿名上传图片',
        summary: '使用 multipart/form-data 上传单张图片',
        description: '当系统允许匿名上传时可用，否则返回 403。',
        method: 'POST',
        path: '/api/upload',
        auth: 'none',
        authDescription: '无需认证（受系统策略限制）',
        params: [
          {
            name: 'file',
            in: 'formData',
            required: true,
            description: '要上传的图片文件',
            type: 'File',
          },
        ],
        responses: [
          {
            status: 200,
            description: '上传成功',
            example: `{
  "success": true,
  "data": {
    "url": "{{baseUrl}}/image/{{encryptedId}}",
    "filename": "image.jpg",
    "size": "1.2 MB",
    "upload_time": "2025-01-01 12:00:00"
  }
}`,
          },
          { status: 400, description: '请求参数错误（未提供 file）' },
          { status: 403, description: '匿名上传被禁用' },
          { status: 413, description: '文件过大' },
          { status: 429, description: '触发每日上传限制' },
          { status: 500, description: '服务器错误' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl -X POST "{{baseUrl}}/api/upload" \\
  -F "file=@{{filePath}}"`,
          },
          {
            id: 'javascript',
            label: 'JavaScript',
            language: 'javascript',
            code: `const formData = new FormData()
formData.append('file', fileInput.files[0])

const res = await fetch('{{baseUrl}}/api/upload', {
  method: 'POST',
  body: formData
})
const data = await res.json()
console.log(data)`,
          },
          {
            id: 'python',
            label: 'Python',
            language: 'python',
            code: `import requests

with open("{{filePath}}", "rb") as f:
    files = {"file": f}
    r = requests.post("{{baseUrl}}/api/upload", files=files)
    print(r.json())`,
          },
          {
            id: 'php',
            label: 'PHP',
            language: 'php',
            code: `<?php
$ch = curl_init();
$file = new CURLFile("{{filePath}}");

curl_setopt_array($ch, [
  CURLOPT_URL => "{{baseUrl}}/api/upload",
  CURLOPT_POST => true,
  CURLOPT_POSTFIELDS => ["file" => $file],
  CURLOPT_RETURNTRANSFER => true,
]);

$resp = curl_exec($ch);
curl_close($ch);
echo $resp;`,
          },
        ],
        notes: ['支持格式：JPG、PNG、GIF、WebP、AVIF、SVG', '单文件最大 20MB'],
      },
    ],
  },

  // -------------------- Token --------------------
  {
    id: 'token',
    title: 'Token',
    description: '游客 Token 创建、验证与使用',
    icon: 'heroicons:key',
    endpoints: [
      {
        id: 'token-generate',
        title: '创建 Token',
        summary: '生成一个可用于上传的游客 Token',
        method: 'POST',
        path: '/api/auth/token/generate',
        auth: 'none',
        params: [
          {
            name: 'upload_limit',
            in: 'body',
            required: false,
            description: '允许上传次数（受系统上限约束）',
            type: 'number',
            example: '100',
          },
          {
            name: 'expires_days',
            in: 'body',
            required: false,
            description: '有效天数（受系统上限约束）',
            type: 'number',
            example: '30',
          },
          {
            name: 'description',
            in: 'body',
            required: false,
            description: '备注/描述',
            type: 'string',
            example: 'my client',
          },
        ],
        responses: [
          {
            status: 200,
            description: '创建成功',
            example: `{
  "success": true,
  "data": {
    "token": "{{token}}",
    "upload_limit": 100,
    "expires_days": 30,
    "expires_at": "2025-02-01T00:00:00Z",
    "message": "Token已生成，可上传100张图片，有效期30天"
  }
}`,
          },
          { status: 400, description: '参数不合法' },
          { status: 403, description: 'Token 生成被禁用' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl -X POST "{{baseUrl}}/api/auth/token/generate" \\
  -H "Content-Type: application/json" \\
  -d '{"upload_limit": 100, "expires_days": 30}'`,
          },
          {
            id: 'javascript',
            label: 'JavaScript',
            language: 'javascript',
            code: `const res = await fetch('{{baseUrl}}/api/auth/token/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ upload_limit: 100, expires_days: 30 })
})
console.log(await res.json())`,
          },
        ],
      },
      {
        id: 'token-verify',
        title: '验证 Token',
        summary: '检查 Token 是否有效',
        method: 'POST',
        path: '/api/auth/token/verify',
        auth: 'bearer',
        authDescription: '推荐使用 Authorization: Bearer <token>',
        params: [
          {
            name: 'Authorization',
            in: 'header',
            required: false,
            description: 'Bearer Token',
            type: 'string',
            example: 'Bearer {{token}}',
          },
          {
            name: 'token',
            in: 'body',
            required: false,
            description: '当未设置 Authorization 时可用',
            type: 'string',
          },
        ],
        responses: [
          {
            status: 200,
            description: '验证结果',
            example: `{
  "success": true,
  "valid": true,
  "data": {
    "upload_count": 3,
    "upload_limit": 100,
    "remaining_uploads": 97,
    "expires_at": "2025-02-01T00:00:00Z"
  }
}`,
          },
          { status: 400, description: '未提供 Token' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl -X POST "{{baseUrl}}/api/auth/token/verify" \\
  -H "Authorization: Bearer {{token}}"`,
          },
        ],
      },
      {
        id: 'token-upload',
        title: '使用 Token 上传',
        summary: '通过 Bearer Token 上传图片',
        method: 'POST',
        path: '/api/auth/upload',
        auth: 'bearer',
        authDescription: '必须提供 Authorization: Bearer <token>',
        params: [
          {
            name: 'Authorization',
            in: 'header',
            required: true,
            description: 'Bearer Token',
            type: 'string',
            example: 'Bearer {{token}}',
          },
          {
            name: 'file',
            in: 'formData',
            required: true,
            description: '要上传的图片文件',
            type: 'File',
          },
        ],
        responses: [
          {
            status: 200,
            description: '上传成功',
            example: `{
  "success": true,
  "data": {
    "url": "{{baseUrl}}/image/{{encryptedId}}",
    "filename": "image.jpg",
    "size": "1.2 MB",
    "remaining_uploads": 97
  }
}`,
          },
          { status: 401, description: 'Token 缺失或无效' },
          { status: 403, description: 'Token 上传被禁用' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl -X POST "{{baseUrl}}/api/auth/upload" \\
  -H "Authorization: Bearer {{token}}" \\
  -F "file=@{{filePath}}"`,
          },
          {
            id: 'javascript',
            label: 'JavaScript',
            language: 'javascript',
            code: `const formData = new FormData()
formData.append('file', fileInput.files[0])

const res = await fetch('{{baseUrl}}/api/auth/upload', {
  method: 'POST',
  headers: { Authorization: 'Bearer {{token}}' },
  body: formData
})
console.log(await res.json())`,
          },
        ],
      },
      {
        id: 'token-uploads',
        title: '获取上传记录',
        summary: '分页获取当前 Token 上传过的图片列表',
        method: 'GET',
        path: '/api/auth/uploads',
        auth: 'bearer',
        authDescription: '推荐 Authorization；也支持 ?token=...',
        params: [
          {
            name: 'Authorization',
            in: 'header',
            required: false,
            description: 'Bearer Token',
            type: 'string',
          },
          {
            name: 'page',
            in: 'query',
            required: false,
            description: '页码（从 1 开始）',
            type: 'number',
            example: '1',
          },
          {
            name: 'limit',
            in: 'query',
            required: false,
            description: '每页数量',
            type: 'number',
            example: '50',
          },
        ],
        responses: [
          {
            status: 200,
            description: '上传记录列表',
            example: `{
  "success": true,
  "data": {
    "uploads": [
      {
        "encrypted_id": "{{encryptedId}}",
        "filename": "image.jpg",
        "created_at": "2025-01-01 12:00:00",
        "image_url": "{{baseUrl}}/image/{{encryptedId}}"
      }
    ],
    "total_uploads": 3,
    "remaining_uploads": 97,
    "has_more": false
  }
}`,
          },
          { status: 401, description: 'Token 缺失或无效' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/auth/uploads?page=1&limit=50" \\
  -H "Authorization: Bearer {{token}}"`,
          },
        ],
      },
    ],
  },

  // -------------------- 图片访问 --------------------
  {
    id: 'image',
    title: '图片访问',
    description: '通过加密 ID 访问图片资源',
    icon: 'heroicons:photo',
    endpoints: [
      {
        id: 'serve-image',
        title: '访问图片',
        summary: '获取图片二进制内容（可能重定向到 CDN）',
        description: '支持 GET/HEAD，设置缓存响应头；启用 CDN 时可能返回 302 跳转。',
        method: 'GET',
        path: '/image/:encryptedId',
        auth: 'none',
        params: [
          {
            name: 'encryptedId',
            in: 'path',
            required: true,
            description: '图片加密 ID',
            type: 'string',
          },
        ],
        responses: [
          { status: 200, description: '图片内容' },
          { status: 302, description: '重定向到 CDN' },
          { status: 404, description: '图片不存在' },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl -L "{{baseUrl}}/image/{{encryptedId}}" -o image.jpg`,
          },
        ],
      },
    ],
  },

  // -------------------- 统计与列表 --------------------
  {
    id: 'stats',
    title: '统计与列表',
    description: '站点统计信息与最近上传列表',
    icon: 'heroicons:chart-bar',
    endpoints: [
      {
        id: 'get-stats',
        title: '获取统计信息',
        summary: '返回总文件数、总容量、今日上传量、运行时长',
        method: 'GET',
        path: '/api/stats',
        auth: 'none',
        responses: [
          {
            status: 200,
            description: '统计数据',
            example: `{
  "success": true,
  "data": {
    "totalFiles": "1234",
    "totalSize": "5.6 GB",
    "todayUploads": "56",
    "uptime": "3天"
  }
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/stats"`,
          },
        ],
      },
      {
        id: 'get-recent',
        title: '获取最近上传',
        summary: '分页获取最近上传文件列表',
        method: 'GET',
        path: '/api/recent',
        auth: 'none',
        params: [
          {
            name: 'limit',
            in: 'query',
            required: false,
            description: '每页数量（默认 12）',
            type: 'number',
          },
          {
            name: 'page',
            in: 'query',
            required: false,
            description: '页码（默认 1）',
            type: 'number',
          },
        ],
        responses: [
          {
            status: 200,
            description: '最近上传列表',
            example: `{
  "success": true,
  "files": [
    {
      "encrypted_id": "{{encryptedId}}",
      "original_filename": "image.jpg",
      "created_at": "2025-01-01 12:00:00",
      "image_url": "{{baseUrl}}/image/{{encryptedId}}"
    }
  ],
  "has_more": false
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/recent?page=1&limit=12"`,
          },
        ],
      },
    ],
  },

  // -------------------- 服务信息 --------------------
  {
    id: 'info',
    title: '服务信息',
    description: '服务端配置与健康状态',
    icon: 'heroicons:information-circle',
    endpoints: [
      {
        id: 'get-info',
        title: '获取服务信息',
        summary: '返回服务端信息、CDN/群组上传配置等',
        description: '注意：该接口返回的是"裸对象"，不使用 { success, data } 包装。',
        method: 'GET',
        path: '/api/info',
        auth: 'none',
        responses: [
          {
            status: 200,
            description: '服务信息（裸对象）',
            example: `{
  "domain": "{{baseUrl}}",
  "cdn_enabled": true,
  "total_files": 1234,
  "max_file_size": 20971520
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/info"`,
          },
        ],
      },
      {
        id: 'health-check',
        title: '健康检查',
        summary: '用于探活',
        method: 'GET',
        path: '/api/health',
        auth: 'none',
        responses: [
          {
            status: 200,
            description: '健康状态',
            example: `{
  "status": "healthy",
  "timestamp": 1735689600,
  "cdn_enabled": true
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/health"`,
          },
        ],
      },
    ],
  },

  // -------------------- 公告 --------------------
  {
    id: 'announcement',
    title: '公告',
    description: '获取当前系统公告',
    icon: 'heroicons:megaphone',
    endpoints: [
      {
        id: 'get-announcement',
        title: '获取公告',
        summary: '返回当前公告内容与启用状态',
        method: 'GET',
        path: '/api/announcement',
        auth: 'none',
        responses: [
          {
            status: 200,
            description: '公告信息',
            example: `{
  "success": true,
  "data": {
    "id": 1,
    "enabled": true,
    "content": "系统公告内容",
    "created_at": "2025-01-01 12:00:00",
    "updated_at": "2025-01-02 12:00:00"
  }
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/announcement"`,
          },
        ],
      },
    ],
  },

  // -------------------- 公开设置 --------------------
  {
    id: 'settings',
    title: '公开设置',
    description: '前端可读取的系统设置',
    icon: 'heroicons:cog-6-tooth',
    endpoints: [
      {
        id: 'get-public-settings',
        title: '获取公开设置',
        summary: '返回匿名上传策略、文件大小限制等',
        method: 'GET',
        path: '/api/public/settings',
        auth: 'none',
        responses: [
          {
            status: 200,
            description: '公开设置',
            example: `{
  "success": true,
  "data": {
    "guest_upload_policy": "open",
    "guest_token_generation_enabled": true,
    "max_file_size_mb": 20,
    "daily_upload_limit": 0,
    "guest_token_max_upload_limit": 1000,
    "guest_token_max_expires_days": 365
  }
}`,
          },
        ],
        codeExamples: [
          {
            id: 'curl',
            label: 'cURL',
            language: 'bash',
            code: `curl "{{baseUrl}}/api/public/settings"`,
          },
        ],
        notes: ['guest_upload_policy 可能为：open | token_only | admin_only'],
      },
    ],
  },
]

// ===================== 工具函数 =====================

/**
 * 替换模板变量
 * @param template 模板字符串
 * @param vars 变量值映射
 */
export function replaceTemplateVars(
  template: string,
  vars: Record<string, string>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => vars[key] ?? `{{${key}}}`)
}

/**
 * 获取 HTTP 方法对应的颜色
 */
export function getMethodColor(method: HttpMethod): string {
  const colors: Record<HttpMethod, string> = {
    GET: 'blue',
    POST: 'green',
    PUT: 'amber',
    DELETE: 'red',
    HEAD: 'gray',
  }
  return colors[method] || 'gray'
}

export default apiSections
