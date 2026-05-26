import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "korean-history-quiz", // 콘솔 등록 시 변경 가능
  brand: {
    displayName: "2026 한국사 기출집", // 콘솔의 한국어 앱 이름과 동일하게
    primaryColor: "#1E40AF",
    icon: "https://static.toss.im/appsintoss/44501/2c901fc3-2bb6-482e-98dd-c70d480328f2.png", // 임시, 콘솔에서 등록 후 교체
  },
  web: {
    host: "localhost",
    port: 5175,
    commands: {
      dev: "vite dev",
      build: "vite build",
    },
  },
  permissions: [],
  outdir: "dist",
});
