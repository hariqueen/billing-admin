# 프론트엔드 Dockerfile (빌드용)
FROM node:18-alpine as build

WORKDIR /app

# package.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 소스 코드 복사
COPY . .

# React 앱 빌드
RUN npm run build

# 프로덕션용 nginx 이미지
FROM nginx:alpine

# 빌드된 파일을 nginx로 복사
COPY --from=build /app/build /usr/share/nginx/html

# nginx 설정 파일 복사 (선택사항)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# 포트 노출
EXPOSE 80

# nginx 실행
CMD ["nginx", "-g", "daemon off;"]

