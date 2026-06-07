# V-Legal Bot Frontend

Giao diện người dùng cho V-Legal Bot - Trợ lý Pháp luật Việt Nam.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Markdown**: React Markdown

## Cài đặt

### 1. Cài đặt dependencies

```bash
cd frontend
npm install
```

### 2. Cấu hình

Tạo file `.env.local` (optional):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Chạy development server

```bash
npm run dev
```

Frontend sẽ chạy tại: http://localhost:3000

## Cấu trúc

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Home (Chat)
│   │   ├── admin/           # Admin panel
│   │   ├── search/          # Search page
│   │   └── stats/           # Statistics
│   ├── components/          # React components
│   │   ├── ChatInterface.tsx
│   │   ├── AdminPanel.tsx
│   │   └── Sidebar.tsx
│   ├── services/            # API services
│   │   └── api.ts
│   └── styles/              # Global styles
│       └── globals.css
├── package.json
├── tailwind.config.js
├── next.config.js
└── tsconfig.json
```

## Các trang

| Trang | Đường dẫn | Mô tả |
|-------|-----------|-------|
| Chat | `/` | Giao diện chat chính |
| Tìm kiếm | `/search` | Tìm kiếm văn bản pháp luật |
| Quản lý | `/admin` | Upload và quản lý văn bản |
| Thống kê | `/stats` | Xem thống kê hệ thống |

## Tính năng

- 💬 **Chat Interface**: Hỏi đáp pháp luật với gợi ý câu hỏi
- 🔍 **Tìm kiếm**: Tìm kiếm semantic trong kho văn bản
- 📁 **Quản lý**: Upload/xóa văn bản, xem chunks
- 📊 **Thống kê**: Dashboard với biểu đồ phân tích

## Yêu cầu

- Node.js 18+
- Backend API đang chạy tại `http://localhost:8000`

## Build Production

```bash
npm run build
npm start
```
