FROM nginx:alpine
RUN apk add --no-cache bash
COPY nginx.conf    /etc/nginx/conf.d/default.conf
COPY index.html    /var/www/html/index.html
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]