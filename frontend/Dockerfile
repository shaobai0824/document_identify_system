# 使用 Node.js 20 作為基礎映像
FROM node:20-alpine

# 設定工作目錄
WORKDIR /app

# 複製 package.json 和 package-lock.json
COPY package*.json ./

# 安裝前端依賴
RUN npm cache clean --force
RUN npm install

# 複製所有前端檔案
COPY . .

# 建置前端應用程式
RUN npm run build

# 安裝 serve 以伺服靜態檔案
RUN npm install -g serve

# 暴露應用程式運行的埠
EXPOSE 3000

# 定義啟動命令
CMD ["serve", "-s", "build", "-l", "3000"]
