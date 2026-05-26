import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

// 루트의 images/ 폴더를 dev 서버에서 /images/* 로 서빙
// (publicDir 밖에 있어 vite 빌드 산출물에는 포함되지 않음 - .ait 사이즈 최소화)
const serveLocalImages = () => ({
  name: "serve-local-images",
  configureServer(server: any) {
    server.middlewares.use("/images", (req: any, res: any, next: any) => {
      const url = req.url?.split("?")[0] || "";
      const filePath = path.join(process.cwd(), "images", url);
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const ext = path.extname(filePath).toLowerCase();
        const mime: Record<string, string> = {
          ".jpg": "image/jpeg",
          ".jpeg": "image/jpeg",
          ".png": "image/png",
          ".webp": "image/webp",
        };
        res.setHeader("Content-Type", mime[ext] || "application/octet-stream");
        res.setHeader("Cache-Control", "public, max-age=3600");
        fs.createReadStream(filePath).pipe(res);
      } else {
        next();
      }
    });
  },
});

export default defineConfig({
  plugins: [react(), serveLocalImages()],
  server: {
    host: true,
    port: 5175,
    strictPort: true,
  },
});
